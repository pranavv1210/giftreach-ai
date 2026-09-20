from datetime import datetime,timedelta
from fastapi import APIRouter,Depends,HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select,func
from sqlalchemy.orm import Session,aliased
from .db import get_db
from .security import current_user,require_csrf
from .schemas import DiscoveryCampaignIn,BulkDraftAction,BulkSendAction
from .models import DiscoveryCampaign,CampaignProspect,Job,Company,Contact,ContactSource,Draft,AgentSettings,GmailConnection,Activity
from .worker import enqueue,process_one
from .services import validate_email,send_mock,ensure_send_eligible
from .gmail import authorization_url,exchange_code,send_gmail,revoke

router=APIRouter(prefix="/api")
def campaign_out(c):return {"id":c.id,"name":c.name,"cities":c.cities,"districts":c.districts,"company_sizes":c.company_sizes,"industries":c.industries,"contact_roles":c.contact_roles,"score_threshold":c.score_threshold,"max_companies":c.max_companies,"max_contacts_per_company":c.max_contacts_per_company,"provider":c.provider,"generate_drafts":c.generate_drafts,"status":c.status,"discovered_count":c.discovered_count,"qualified_count":c.qualified_count,"error_message":c.error_message,"created_at":c.created_at}
@router.get("/discovery-campaigns")
def list_campaigns(db:Session=Depends(get_db),user=Depends(current_user)):return [campaign_out(c) for c in db.scalars(select(DiscoveryCampaign).order_by(DiscoveryCampaign.created_at.desc())).all()]
@router.post("/discovery-campaigns",status_code=201)
def create_campaign(data:DiscoveryCampaignIn,db:Session=Depends(get_db),user=Depends(require_csrf)):
    if data.provider not in ("brave","overpass"):raise HTTPException(422,"Supported providers are overpass and brave")
    c=DiscoveryCampaign(**data.model_dump());db.add(c);db.flush();db.add(Activity(event="campaign.created",message=f"Created discovery campaign {c.name}",entity_type="campaign",entity_id=c.id));db.commit();db.refresh(c);return campaign_out(c)
@router.post("/discovery-campaigns/{campaign_id}/start")
def start(campaign_id:int,db:Session=Depends(get_db),user=Depends(require_csrf)):
    c=db.get(DiscoveryCampaign,campaign_id);settings=db.get(AgentSettings,1)
    if not c:raise HTTPException(404,"Campaign not found")
    if settings.kill_switch:raise HTTPException(409,"Emergency stop is active")
    if settings.mode=="OFF":raise HTTPException(409,"Select RESEARCH or DRAFT mode before starting discovery")
    c.status="QUEUED";c.error_message=None;enqueue(db,"DISCOVER",c.id,suffix=datetime.utcnow().strftime("%Y%m%d%H%M%S"));db.commit();return campaign_out(c)
@router.post("/discovery-campaigns/{campaign_id}/pause")
def pause(campaign_id:int,db:Session=Depends(get_db),user=Depends(require_csrf)):
    c=db.get(DiscoveryCampaign,campaign_id)
    if not c:raise HTTPException(404,"Campaign not found")
    c.status="PAUSED";db.commit();return campaign_out(c)
@router.post("/discovery-campaigns/{campaign_id}/cancel")
def cancel(campaign_id:int,db:Session=Depends(get_db),user=Depends(require_csrf)):
    c=db.get(DiscoveryCampaign,campaign_id)
    if not c:raise HTTPException(404,"Campaign not found")
    c.status="CANCELLED"
    for j in db.scalars(select(Job).where(Job.campaign_id==c.id,Job.status.in_(["PENDING","RUNNING"]))).all():j.cancelled=True;j.status="CANCELLED"
    db.commit();return campaign_out(c)
@router.get("/jobs")
def jobs(campaign_id:int|None=None,db:Session=Depends(get_db),user=Depends(current_user)):
    q=select(Job).order_by(Job.created_at.desc()).limit(100)
    if campaign_id:q=q.where(Job.campaign_id==campaign_id)
    return db.scalars(q).all()
@router.post("/jobs/run-one")
def run_one(user=Depends(require_csrf)):return {"processed":process_one()}
@router.get("/review")
def review(campaign_id:int|None=None,status:str|None=None,db:Session=Depends(get_db),user=Depends(current_user)):
    q=select(CampaignProspect,DiscoveryCampaign,Company,Contact,Draft).join(DiscoveryCampaign,DiscoveryCampaign.id==CampaignProspect.campaign_id).join(Company,Company.id==CampaignProspect.company_id).join(Contact,Contact.id==CampaignProspect.contact_id).outerjoin(Draft,Draft.id==CampaignProspect.draft_id).order_by(CampaignProspect.created_at.desc())
    if campaign_id:q=q.where(CampaignProspect.campaign_id==campaign_id)
    if status:q=q.where(Draft.status==status)
    rows=[]
    for link,camp,company,contact,draft in db.execute(q).all():
        source=db.scalar(select(ContactSource).where(ContactSource.contact_id==contact.id).order_by(ContactSource.created_at.desc()))
        eligible=bool(draft and not draft.validation_errors and not contact.suppressed and contact.verification_status in ("MX_VALID","PROVIDER_VERIFIED","MANUALLY_VERIFIED"))
        reasons=[]
        if contact.suppressed:reasons.append("Contact suppressed")
        if contact.verification_status not in ("MX_VALID","PROVIDER_VERIFIED","MANUALLY_VERIFIED"):reasons.append("Email is not independently verified")
        if not draft:reasons.append("Draft not generated")
        elif draft.validation_errors:reasons.extend(draft.validation_errors)
        rows.append({"prospect_id":link.id,"campaign_id":camp.id,"campaign":camp.name,"campaign_status":camp.status,"company":company.name,"industry":company.industry,"size":company.size,"city":company.city,"score":company.score,"contact_id":contact.id,"contact":contact.name,"title":contact.title,"email":contact.email,"verification_status":contact.verification_status,"confidence":contact.confidence,"source_type":source.source_type if source else None,"source_url":source.source_url if source else None,"source_description":source.description if source else None,"draft_id":draft.id if draft else None,"subject":draft.subject if draft else None,"body":draft.body if draft else None,"draft_status":draft.status if draft else "MISSING","eligible":eligible,"exclusion_reasons":reasons})
    return rows
def _drafts(db,ids):return db.scalars(select(Draft).where(Draft.id.in_(ids))).all()
@router.post("/review/bulk/approve")
def bulk_approve(data:BulkDraftAction,db:Session=Depends(get_db),user=Depends(require_csrf)):
    approved=[];excluded=[]
    for d in _drafts(db,data.draft_ids):
        d.validation_errors=validate_email(d.subject,d.body);contact=db.get(Contact,d.contact_id)
        if d.validation_errors or contact.suppressed:excluded.append({"id":d.id,"reasons":d.validation_errors+(["Contact suppressed"] if contact.suppressed else [])})
        else:d.status="APPROVED";approved.append(d.id)
    db.add(Activity(event="drafts.bulk_approved",message=f"Approved {len(approved)} drafts",details={"draft_ids":approved}));db.commit();return {"approved":approved,"excluded":excluded}
@router.post("/review/bulk/reject")
def bulk_reject(data:BulkDraftAction,db:Session=Depends(get_db),user=Depends(require_csrf)):
    drafts=_drafts(db,data.draft_ids)
    for d in drafts:d.status="REJECTED"
    db.commit();return {"rejected":[d.id for d in drafts]}
@router.post("/review/bulk/preview-send")
def preview_send(data:BulkDraftAction,db:Session=Depends(get_db),user=Depends(current_user)):
    settings=db.get(AgentSettings,1);eligible=[];excluded=[]
    for d in _drafts(db,data.draft_ids):
        c=db.get(Contact,d.contact_id);reasons=[]
        if d.status!="APPROVED":reasons.append("Draft not approved")
        if c.suppressed:reasons.append("Contact suppressed")
        if c.verification_status not in ("MX_VALID","PROVIDER_VERIFIED","MANUALLY_VERIFIED"):reasons.append("Email is not verified")
        if reasons:excluded.append({"id":d.id,"email":c.email,"reasons":reasons})
        else:eligible.append(d.id)
    conn=db.get(GmailConnection,1)
    return {"selected":len(data.draft_ids),"eligible":eligible,"excluded":excluded,"limits":{"daily":settings.daily_limit,"hourly":settings.hourly_limit},"gmail":{"status":conn.status if conn else "NOT_CONNECTED","email":conn.email if conn else None}}
@router.post("/review/bulk/send")
def bulk_send(data:BulkSendAction,db:Session=Depends(get_db),user=Depends(require_csrf)):
    if not data.confirm:raise HTTPException(422,"Explicit confirmation is required")
    sent=[];excluded=[]
    for d in _drafts(db,data.draft_ids):
        try:
            if data.provider=="gmail":
                c=db.get(Contact,d.contact_id)
                ensure_send_eligible(db,d)
                result=send_gmail(db,c.email,d.subject,d.body);d.status="SENT";d.sent_at=datetime.utcnow();d.provider_message_id=result.get("id");sent.append(d.id)
                db.add(Activity(event="email.sent",message=f"Gmail sent to {c.email}",entity_type="draft",entity_id=d.id,details={"provider":"gmail","message_id":d.provider_message_id}))
            elif data.provider=="mock":send_mock(db,d);sent.append(d.id)
            else:raise ValueError("Unknown send provider")
        except Exception as exc:excluded.append({"id":d.id,"reason":str(exc)})
    db.commit();return {"sent":sent,"excluded":excluded,"provider":data.provider}
@router.get("/gmail/status")
def gmail_status(db:Session=Depends(get_db),user=Depends(current_user)):
    c=db.get(GmailConnection,1);return {"status":c.status if c else "NOT_CONNECTED","email":c.email if c else None}
@router.post("/gmail/connect")
def gmail_connect(db:Session=Depends(get_db),user=Depends(require_csrf)):
    try:return {"authorization_url":authorization_url(db)}
    except ValueError as e:raise HTTPException(409,str(e))
@router.get("/integrations/gmail/callback")
def gmail_callback(code:str,state:str,db:Session=Depends(get_db)):
    from .config import get_settings
    try:exchange_code(db,code,state);return RedirectResponse(get_settings().frontend_origin+"/integrations?gmail=connected")
    except Exception as e:raise HTTPException(400,"Gmail authorization failed")
@router.post("/gmail/disconnect")
def gmail_disconnect(db:Session=Depends(get_db),user=Depends(require_csrf)):revoke(db);return {"ok":True}
