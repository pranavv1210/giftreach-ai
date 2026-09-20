import threading,uuid
from datetime import datetime,timedelta
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from .db import SessionLocal
from .models import DiscoveryCampaign,CampaignProspect,Job,Company,Contact,ContactSource,Draft,AgentSettings,Activity
from .providers import BraveDiscoveryProvider,OverpassDiscoveryProvider,OfficialWebsiteContactProvider,campaign_queries,ProviderUnavailable
from .services import score_company,generate_draft,validate_email

WORKER_ID=f"worker-{uuid.uuid4().hex[:8]}";_stop=threading.Event();_thread=None
def enqueue(db,job_type,campaign_id,entity_id=None,payload=None,suffix=""):
    key=f"{job_type}:{campaign_id}:{entity_id or 0}:{suffix}";existing=db.scalar(select(Job).where(Job.dedupe_key==key))
    if existing:return existing
    job=Job(job_type=job_type,campaign_id=campaign_id,entity_id=entity_id,payload=payload or {},dedupe_key=key);db.add(job);return job
def claim(db):
    now=datetime.utcnow();stale=now-timedelta(minutes=10)
    job=db.scalar(select(Job).where(Job.cancelled.is_(False),Job.available_at<=now,((Job.status=="PENDING")|((Job.status=="RUNNING")&(Job.locked_at<stale)))).order_by(Job.created_at).limit(1))
    if not job:return None
    job.status="RUNNING";job.locked_at=now;job.locked_by=WORKER_ID;job.attempts+=1;db.commit();db.refresh(job);return job
def process_one():
    with SessionLocal() as db:
        settings=db.get(AgentSettings,1)
        if not settings or settings.paused or settings.kill_switch or settings.mode=="OFF" or settings.discovery_paused:return False
        job=claim(db)
        if not job:return False
        campaign=db.get(DiscoveryCampaign,job.campaign_id) if job.campaign_id else None
        if not campaign or campaign.status in ("PAUSED","CANCELLED"):job.status="CANCELLED";db.commit();return True
        try:
            if job.job_type=="DISCOVER":_discover(db,campaign,job)
            elif job.job_type=="RESEARCH_COMPANY":_research(db,campaign,job)
            elif job.job_type=="GENERATE_DRAFT":_draft(db,campaign,job)
            job.status="COMPLETED";job.progress=100;job.error_message=None
            db.flush()
            remaining=db.scalar(select(Job.id).where(Job.campaign_id==campaign.id,Job.id!=job.id,Job.status.in_(["PENDING","RUNNING"])).limit(1))
            if not remaining:campaign.status="COMPLETED"
        except Exception as exc:
            job.error_message=str(exc)[:1000]
            if job.attempts<job.max_attempts:job.status="PENDING";job.available_at=datetime.utcnow()+timedelta(seconds=2**job.attempts)
            else:job.status="FAILED";campaign.status="FAILED";campaign.error_message=job.error_message
            db.add(Activity(event="job.failed",message=f"{job.job_type} failed: {job.error_message}",entity_type="job",entity_id=job.id))
        db.commit();return True
def _discover(db,campaign,job):
    if campaign.provider=="brave":findings=BraveDiscoveryProvider().discover_companies(campaign_queries(campaign),campaign.max_companies)
    elif campaign.provider=="overpass":findings=OverpassDiscoveryProvider().discover_companies(campaign,campaign.max_companies)
    else:raise ProviderUnavailable(f"Provider '{campaign.provider}' is not available for live discovery")
    for index,f in enumerate(findings):
        company=db.scalar(select(Company).where((Company.domain==f.domain)|(Company.name==f.name)))
        if not company:
            company=Company(name=f.name,domain=f.domain,city=(campaign.cities or ["Bengaluru"])[0],district=(campaign.districts or ["Karnataka"])[0],industry=None,source_url=f.website,evidence=f"{f.evidence} Source: {f.source_url}");db.add(company);db.flush()
        elif company.source_url and "openstreetmap.org" in company.source_url:
            company.source_url=f.website
            company.evidence=f"{f.evidence} Source: {f.source_url}"
            company.industry=None
        score_company(company)
        if not db.scalar(select(CampaignProspect).where(CampaignProspect.campaign_id==campaign.id,CampaignProspect.company_id==company.id,CampaignProspect.contact_id.is_(None))):db.add(CampaignProspect(campaign_id=campaign.id,company_id=company.id,source_query=f.query))
        enqueue(db,"RESEARCH_COMPANY",campaign.id,company.id,suffix=str(job.id));job.progress=int((index+1)/max(len(findings),1)*100)
    campaign.discovered_count=len(findings);campaign.status="RUNNING";db.add(Activity(event="discovery.completed",message=f"Discovered {len(findings)} company websites for {campaign.name}",entity_type="campaign",entity_id=campaign.id))
def _research(db,campaign,job):
    company=db.scalar(select(Company).options(selectinload(Company.contacts)).where(Company.id==job.entity_id))
    if not company:return
    findings=OfficialWebsiteContactProvider().discover(company.source_url or f"https://{company.domain}",campaign.max_contacts_per_company)
    for f in findings:
        contact=db.scalar(select(Contact).where(Contact.email==f.email))
        if not contact:contact=Contact(company_id=company.id,email=f.email,verification_status="SYNTAX_VALID",confidence=f.confidence);db.add(contact);db.flush()
        if not db.scalar(select(ContactSource).where(ContactSource.contact_id==contact.id,ContactSource.source_url==f.source_url)):db.add(ContactSource(contact_id=contact.id,source_type=f.source_type,source_url=f.source_url,description=f.description,provider="official_website"))
        link=db.scalar(select(CampaignProspect).where(CampaignProspect.campaign_id==campaign.id,CampaignProspect.company_id==company.id,CampaignProspect.contact_id==contact.id))
        if not link:link=CampaignProspect(campaign_id=campaign.id,company_id=company.id,contact_id=contact.id,status="QUALIFIED");db.add(link)
        if company.score<campaign.score_threshold:link.status="BELOW_THRESHOLD"
        elif campaign.generate_drafts and db.get(AgentSettings,1).mode in ("DRAFT","CONTROLLED_AUTOPILOT"):enqueue(db,"GENERATE_DRAFT",campaign.id,contact.id)
    score_company(company);campaign.qualified_count+=len(findings)
def _draft(db,campaign,job):
    contact=db.scalar(select(Contact).options(selectinload(Contact.company)).where(Contact.id==job.entity_id))
    if not contact or contact.suppressed:return
    subject,body,key=generate_draft(contact);draft=db.scalar(select(Draft).where(Draft.idempotency_key==key))
    if not draft:draft=Draft(contact_id=contact.id,subject=subject,body=body,idempotency_key=key,validation_errors=validate_email(subject,body));db.add(draft);db.flush()
    link=db.scalar(select(CampaignProspect).where(CampaignProspect.campaign_id==campaign.id,CampaignProspect.contact_id==contact.id))
    if link:link.draft_id=draft.id;link.status="DRAFTED"
def loop():
    from .config import get_settings
    while not _stop.is_set():worked=process_one();_stop.wait(.25 if worked else get_settings().worker_poll_seconds)
def start_worker():
    global _thread
    if _thread and _thread.is_alive():return
    _stop.clear();_thread=threading.Thread(target=loop,daemon=True,name="giftreach-worker");_thread.start()
def stop_worker():_stop.set()
