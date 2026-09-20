from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from . import __version__
from .config import get_settings, APPROVED_CATEGORIES
from .db import Base, engine, get_db
from .models import Company, Contact, ContactSource, Campaign, Draft, Activity, AgentSettings
from .schemas import *
from .security import current_user, require_csrf, create_session, set_session
from .services import score_company, generate_draft, validate_email, send_mock

@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    with next(get_db()) as db:
        if not db.get(AgentSettings,1): db.add(AgentSettings(id=1,approved_categories=list(APPROVED_CATEGORIES))); db.commit()
    yield

app=FastAPI(title="GiftReach AI",version=__version__,lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=[get_settings().frontend_origin],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

def audit(db,event,message,entity_type=None,entity_id=None): db.add(Activity(event=event,message=message,entity_type=entity_type,entity_id=entity_id))
def company_out(c): return {"id":c.id,"name":c.name,"domain":c.domain,"industry":c.industry,"size":c.size,"city":c.city,"district":c.district,"evidence":c.evidence,"source_url":c.source_url,"score":c.score,"score_breakdown":c.score_breakdown,"suppressed":c.suppressed,"contact_count":len(c.contacts)}
def contact_out(c): return {"id":c.id,"company_id":c.company_id,"company":c.company.name,"name":c.name,"email":c.email,"title":c.title,"department":c.department,"verification_status":c.verification_status,"confidence":c.confidence,"suppressed":c.suppressed,"sources":[{"id":s.id,"source_type":s.source_type,"source_url":s.source_url,"description":s.description,"provider":s.provider} for s in c.sources]}

@app.get("/health")
def health(): return {"status":"ok"}
@app.get("/ready")
def ready(db:Session=Depends(get_db)): db.execute(select(1)); return {"status":"ready"}
@app.get("/version")
def version(): return {"version":__version__}
@app.post("/api/auth/login")
def login(data:LoginIn,response:Response):
    s=get_settings()
    if data.email.lower()!=s.owner_email.lower() or data.password!=s.owner_password: raise HTTPException(401,"Invalid credentials")
    token,csrf=create_session(data.email); set_session(response,token); return {"email":data.email,"csrf_token":csrf}
@app.post("/api/auth/logout")
def logout(response:Response,user=Depends(require_csrf)): response.delete_cookie("session"); return {"ok":True}
@app.get("/api/auth/me")
def me(user=Depends(current_user)): return {"email":user["sub"],"csrf_token":user["csrf"]}

@app.get("/api/overview")
def overview(db:Session=Depends(get_db),user=Depends(current_user)):
    count=lambda model: db.scalar(select(func.count()).select_from(model)) or 0
    verified=db.scalar(select(func.count(Contact.id)).where(Contact.verification_status.in_(["MX_VALID","PROVIDER_VERIFIED","MANUALLY_VERIFIED"]))) or 0
    return {"companies":count(Company),"contacts":count(Contact),"verified":verified,"drafts":db.scalar(select(func.count(Draft.id)).where(Draft.status.in_(["DRAFT","APPROVED"]))) or 0,"sent":db.scalar(select(func.count(Draft.id)).where(Draft.status=="SENT")) or 0,"replies":0,"bounces":db.scalar(select(func.count(Contact.id)).where(Contact.verification_status=="BOUNCED")) or 0,"interested":0,"agent":settings_out(db.get(AgentSettings,1))}
@app.get("/api/companies")
def companies(q:str|None=None,db:Session=Depends(get_db),user=Depends(current_user)):
    stmt=select(Company).options(selectinload(Company.contacts)).order_by(Company.score.desc())
    if q: stmt=stmt.where(Company.name.ilike(f"%{q}%"))
    return [company_out(x) for x in db.scalars(stmt).all()]
@app.post("/api/companies",status_code=201)
def create_company(data:CompanyIn,db:Session=Depends(get_db),user=Depends(require_csrf)):
    c=Company(**data.model_dump()); db.add(c)
    try: db.flush(); score_company(c); audit(db,"company.created",f"Created {c.name}","company",c.id); db.commit(); db.refresh(c); c.contacts=[]; return company_out(c)
    except IntegrityError: db.rollback(); raise HTTPException(409,"Company already exists")
@app.get("/api/contacts")
def contacts(q:str|None=None,db:Session=Depends(get_db),user=Depends(current_user)):
    stmt=select(Contact).options(selectinload(Contact.sources),selectinload(Contact.company)).order_by(Contact.created_at.desc())
    if q: stmt=stmt.where((Contact.email.ilike(f"%{q}%"))|(Contact.name.ilike(f"%{q}%")))
    return [contact_out(x) for x in db.scalars(stmt).all()]
@app.post("/api/contacts",status_code=201)
def create_contact(data:ContactIn,db:Session=Depends(get_db),user=Depends(require_csrf)):
    if not db.get(Company,data.company_id): raise HTTPException(404,"Company not found")
    fields=data.model_dump(exclude={"source_type","source_url","source_description"}); c=Contact(**fields,verification_status="SYNTAX_VALID",confidence=.25); db.add(c)
    try:
        db.flush(); db.add(ContactSource(contact_id=c.id,source_type=data.source_type,source_url=data.source_url,description=data.source_description)); audit(db,"contact.created",f"Created contact {c.email}","contact",c.id); db.commit()
        c=db.scalar(select(Contact).options(selectinload(Contact.sources),selectinload(Contact.company)).where(Contact.id==c.id)); return contact_out(c)
    except IntegrityError: db.rollback(); raise HTTPException(409,"Email already exists")
@app.post("/api/contacts/{contact_id}/suppress")
def suppress(contact_id:int,db:Session=Depends(get_db),user=Depends(require_csrf)):
    c=db.get(Contact,contact_id)
    if not c: raise HTTPException(404,"Contact not found")
    c.suppressed=True;c.verification_status="SUPPRESSED";audit(db,"contact.suppressed",f"Suppressed {c.email}","contact",c.id);db.commit();return {"ok":True}
@app.post("/api/contacts/{contact_id}/verify-manually")
def verify(contact_id:int,db:Session=Depends(get_db),user=Depends(require_csrf)):
    c=db.get(Contact,contact_id)
    if not c: raise HTTPException(404,"Contact not found")
    c.verification_status="MANUALLY_VERIFIED";c.manually_verified=True;c.confidence=1;audit(db,"contact.verified",f"Manually verified {c.email}","contact",c.id);db.commit();return {"ok":True}
@app.get("/api/campaigns")
def campaigns(db:Session=Depends(get_db),user=Depends(current_user)): return db.scalars(select(Campaign).order_by(Campaign.created_at.desc())).all()
@app.post("/api/campaigns",status_code=201)
def create_campaign(data:CampaignIn,db:Session=Depends(get_db),user=Depends(require_csrf)): c=Campaign(**data.model_dump());db.add(c);db.commit();db.refresh(c);return c
@app.get("/api/drafts")
def drafts(db:Session=Depends(get_db),user=Depends(current_user)): return db.scalars(select(Draft).order_by(Draft.created_at.desc())).all()
@app.post("/api/drafts",status_code=201)
def create_draft(data:DraftIn,db:Session=Depends(get_db),user=Depends(require_csrf)):
    c=db.scalar(select(Contact).options(selectinload(Contact.company)).where(Contact.id==data.contact_id))
    if not c: raise HTTPException(404,"Contact not found")
    subject,body,key=generate_draft(c); existing=db.scalar(select(Draft).where(Draft.idempotency_key==key))
    if existing:return existing
    d=Draft(contact_id=c.id,campaign_id=data.campaign_id,subject=subject,body=body,idempotency_key=key);d.validation_errors=validate_email(subject,body);db.add(d);audit(db,"draft.created",f"Drafted email for {c.email}","contact",c.id);db.commit();db.refresh(d);return d
@app.patch("/api/drafts/{draft_id}")
def edit_draft(draft_id:int,data:DraftEdit,db:Session=Depends(get_db),user=Depends(require_csrf)):
    d=db.get(Draft,draft_id)
    if not d:raise HTTPException(404,"Draft not found")
    d.subject=data.subject;d.body=data.body;d.validation_errors=validate_email(d.subject,d.body);d.status="DRAFT";db.commit();db.refresh(d);return d
@app.post("/api/drafts/{draft_id}/approve")
def approve(draft_id:int,db:Session=Depends(get_db),user=Depends(require_csrf)):
    d=db.get(Draft,draft_id)
    if not d:raise HTTPException(404,"Draft not found")
    d.validation_errors=validate_email(d.subject,d.body)
    if d.validation_errors:raise HTTPException(422,{"validation_errors":d.validation_errors})
    d.status="APPROVED";audit(db,"draft.approved",f"Approved draft {d.id}","draft",d.id);db.commit();return {"ok":True}
@app.post("/api/drafts/{draft_id}/send")
def send(draft_id:int,db:Session=Depends(get_db),user=Depends(require_csrf)):
    d=db.get(Draft,draft_id)
    if not d or d.status not in ("APPROVED","SENT"):raise HTTPException(409,"Draft is not approved")
    try: message_id=send_mock(db,d);db.commit();return {"message_id":message_id,"provider":"mock"}
    except ValueError as e: db.rollback();raise HTTPException(409,str(e))
def settings_out(s): return {"mode":s.mode,"paused":s.paused,"kill_switch":s.kill_switch,"sending_paused":s.sending_paused,"discovery_paused":s.discovery_paused,"daily_limit":s.daily_limit,"hourly_limit":s.hourly_limit,"approved_categories":s.approved_categories}
@app.get("/api/agent")
def agent(db:Session=Depends(get_db),user=Depends(current_user)): return settings_out(db.get(AgentSettings,1))
@app.patch("/api/agent")
def patch_agent(data:AgentPatch,db:Session=Depends(get_db),user=Depends(require_csrf)):
    s=db.get(AgentSettings,1)
    for k,v in data.model_dump(exclude_none=True).items():
        if k=="mode" and v not in ("OFF","RESEARCH","DRAFT","CONTROLLED_AUTOPILOT"):raise HTTPException(422,"Invalid mode")
        setattr(s,k,v)
    audit(db,"agent.updated",f"Agent set to {s.mode}","agent",1);db.commit();return settings_out(s)
@app.post("/api/agent/emergency-stop")
def emergency(db:Session=Depends(get_db),user=Depends(require_csrf)):
    s=db.get(AgentSettings,1);s.kill_switch=True;s.paused=True;s.sending_paused=True;s.mode="OFF";audit(db,"agent.emergency_stop","Emergency stop activated","agent",1);db.commit();return settings_out(s)
@app.get("/api/activity")
def activity(limit:int=50,db:Session=Depends(get_db),user=Depends(current_user)): return db.scalars(select(Activity).order_by(Activity.created_at.desc()).limit(min(limit,100))).all()
@app.get("/api/integrations")
def integrations(user=Depends(current_user)):
    s=get_settings();return {"gmail":{"status":"connected" if s.gmail_client_id and s.gmail_client_secret else "missing_configuration"},"database":{"status":"connected"},"ai":{"status":"connected" if s.openai_api_key else "mock"},"search":{"status":"connected" if s.search_api_key else "missing_configuration"},"verification":{"status":"connected" if s.email_verification_api_key else "missing_configuration"}}
