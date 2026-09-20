import hashlib, re, uuid
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from .config import APPROVED_CATEGORIES
from .models import Contact, Company, Draft, Activity, AgentSettings

FORBIDDEN = ("chocolate", "sweets", "dry fruits", "electronics", "apparel", "discount", "guaranteed delivery", "previous conversation")
SIGNATURE = "Pranav V.\nCorporate Gifting"

def score_company(company: Company):
    factors={"geography":25 if company.city.lower()=="bengaluru" else 15 if "karnataka" in company.district.lower() else 0,
             "industry":20 if company.industry else 0,"company_profile":15 if company.size else 0,
             "source_evidence":20 if company.evidence else 0,"contact_readiness":min(len(company.contacts)*10,20)}
    company.score=float(sum(factors.values())); company.score_breakdown={"factors":factors,"missing":[k for k,v in factors.items() if not v],"confidence":"HIGH" if company.score>=70 else "MEDIUM" if company.score>=40 else "LOW"}

def generate_draft(contact: Contact):
    greeting=f"Hello {contact.name}," if contact.name else "Hello,"; company=contact.company.name
    body=(f"{greeting}\n\nI’m Pranav V., and I help businesses source thoughtful corporate gifts and custom art for employee, client, and event requirements. "
          f"I wanted to ask whether {company} is currently exploring options in corporate gifts, Tanjore art, wooden art, brass idols, antiques, or return gifts.\n\n"
          "If useful, I can share a concise selection and pricing based on your requirement and budget. If this is not relevant, please let me know and I will not contact you again.\n\n"+SIGNATURE)
    key=hashlib.sha256(f"initial:{contact.id}:{company}".encode()).hexdigest()
    return f"Corporate Gifting Options for {company}", body, key

def validate_email(subject: str, body: str):
    errors=[]; low=(subject+" "+body).lower()
    if not subject.strip(): errors.append("Subject is required")
    if SIGNATURE not in body: errors.append("Required signature is missing")
    if len(body)>2500: errors.append("Email is not concise")
    if any(term in low for term in FORBIDDEN): errors.append("Contains an unapproved or unsupported claim/category")
    if "unsubscribe" not in low and "not contact you again" not in low and "decline" not in low: errors.append("A polite opt-out is required")
    if re.search(r'\+?\d[\d\s-]{8,}',body): errors.append("Phone numbers are not allowed")
    return errors

def send_mock(db: Session, draft: Draft):
    settings,contact=ensure_send_eligible(db,draft)
    company=contact.company
    prior=db.scalar(select(Draft).where(Draft.idempotency_key==draft.idempotency_key,Draft.sent_at.is_not(None)))
    if prior: return prior.provider_message_id
    draft.sent_at=datetime.utcnow(); draft.status="SENT"; draft.provider_message_id=f"mock-{uuid.uuid4()}"
    db.add(Activity(event="email.sent",message=f"Mock email sent to {contact.email}",entity_type="draft",entity_id=draft.id))
    return draft.provider_message_id

def ensure_send_eligible(db: Session, draft: Draft):
    settings=db.get(AgentSettings,1);contact=db.get(Contact,draft.contact_id);company=contact.company
    if not settings or settings.kill_switch or settings.paused or settings.sending_paused: raise ValueError("Sending is paused by agent safety controls")
    if settings.mode!="CONTROLLED_AUTOPILOT": raise ValueError("Controlled autopilot is not enabled")
    if draft.status not in ("APPROVED","SENT"): raise ValueError("Draft is not approved")
    if contact.suppressed or company.suppressed: raise ValueError("Recipient or company is suppressed")
    if contact.verification_status not in ("MX_VALID","PROVIDER_VERIFIED","MANUALLY_VERIFIED"): raise ValueError("Recipient email is not send-eligible")
    if draft.validation_errors: raise ValueError("Draft failed policy validation")
    now=datetime.utcnow(); daily=db.scalar(select(func.count(Draft.id)).where(Draft.sent_at>=now-timedelta(days=1))) or 0
    hourly=db.scalar(select(func.count(Draft.id)).where(Draft.sent_at>=now-timedelta(hours=1))) or 0
    if daily>=settings.daily_limit or hourly>=settings.hourly_limit: raise ValueError("Global sending limit reached")
    company_daily=db.scalar(select(func.count(Draft.id)).join(Contact,Contact.id==Draft.contact_id).where(Contact.company_id==company.id,Draft.sent_at>=now-timedelta(days=1))) or 0
    company_weekly=db.scalar(select(func.count(Draft.id)).join(Contact,Contact.id==Draft.contact_id).where(Contact.company_id==company.id,Draft.sent_at>=now-timedelta(days=7))) or 0
    if company_daily>=settings.company_daily_limit or company_weekly>=settings.company_weekly_limit:raise ValueError("Company sending limit reached")
    return settings,contact
