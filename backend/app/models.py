import enum
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, Float, ForeignKey, Text, DateTime, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base, TimestampMixin

class VerificationStatus(str, enum.Enum):
    UNVERIFIED="UNVERIFIED"; SYNTAX_VALID="SYNTAX_VALID"; DOMAIN_VALID="DOMAIN_VALID"; MX_VALID="MX_VALID"
    PROVIDER_VERIFIED="PROVIDER_VERIFIED"; MANUALLY_VERIFIED="MANUALLY_VERIFIED"; INVALID="INVALID"; BOUNCED="BOUNCED"; SUPPRESSED="SUPPRESSED"

class Company(Base, TimestampMixin):
    __tablename__="companies"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    domain: Mapped[str|None] = mapped_column(String(255), index=True)
    industry: Mapped[str|None] = mapped_column(String(120))
    size: Mapped[str|None] = mapped_column(String(40))
    city: Mapped[str] = mapped_column(String(100), default="Bengaluru")
    district: Mapped[str] = mapped_column(String(100), default="Bengaluru Urban")
    source_url: Mapped[str|None] = mapped_column(String(1000))
    evidence: Mapped[str|None] = mapped_column(Text)
    score: Mapped[float] = mapped_column(Float, default=0)
    score_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    suppressed: Mapped[bool] = mapped_column(Boolean, default=False)
    contacts: Mapped[list["Contact"]] = relationship(back_populates="company", cascade="all, delete-orphan")

class Contact(Base, TimestampMixin):
    __tablename__="contacts"; __table_args__=(UniqueConstraint("email", name="uq_contact_email"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    name: Mapped[str|None] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320), index=True)
    title: Mapped[str|None] = mapped_column(String(200))
    department: Mapped[str|None] = mapped_column(String(100))
    location: Mapped[str|None] = mapped_column(String(150))
    verification_status: Mapped[str] = mapped_column(String(40), default=VerificationStatus.UNVERIFIED.value)
    confidence: Mapped[float] = mapped_column(Float, default=0)
    manually_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    suppressed: Mapped[bool] = mapped_column(Boolean, default=False)
    company: Mapped[Company] = relationship(back_populates="contacts")
    sources: Mapped[list["ContactSource"]] = relationship(back_populates="contact", cascade="all, delete-orphan")

class ContactSource(Base, TimestampMixin):
    __tablename__="contact_sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("contacts.id"), index=True)
    source_type: Mapped[str] = mapped_column(String(80))
    source_url: Mapped[str|None] = mapped_column(String(1000))
    description: Mapped[str|None] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(80), default="manual")
    discovered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    contact: Mapped[Contact] = relationship(back_populates="sources")

class Campaign(Base, TimestampMixin):
    __tablename__="campaigns"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(30), default="DRAFT")
    filters: Mapped[dict] = mapped_column(JSON, default=dict)
    daily_limit: Mapped[int] = mapped_column(Integer, default=20)
    hourly_limit: Mapped[int] = mapped_column(Integer, default=5)
    max_contacts_per_company: Mapped[int] = mapped_column(Integer, default=3)

class Draft(Base, TimestampMixin):
    __tablename__="drafts"; __table_args__=(UniqueConstraint("idempotency_key", name="uq_draft_idempotency"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("contacts.id"), index=True)
    campaign_id: Mapped[int|None] = mapped_column(ForeignKey("campaigns.id"))
    subject: Mapped[str] = mapped_column(String(250))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="DRAFT")
    validation_errors: Mapped[list] = mapped_column(JSON, default=list)
    idempotency_key: Mapped[str] = mapped_column(String(100))
    sent_at: Mapped[datetime|None] = mapped_column(DateTime)
    provider_message_id: Mapped[str|None] = mapped_column(String(255))

class Activity(Base):
    __tablename__="activities"
    id: Mapped[int] = mapped_column(primary_key=True)
    event: Mapped[str] = mapped_column(String(100), index=True)
    message: Mapped[str] = mapped_column(Text)
    entity_type: Mapped[str|None] = mapped_column(String(50))
    entity_id: Mapped[int|None] = mapped_column(Integer)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

class AgentSettings(Base):
    __tablename__="agent_settings"
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    mode: Mapped[str] = mapped_column(String(30), default="OFF")
    paused: Mapped[bool] = mapped_column(Boolean, default=False)
    kill_switch: Mapped[bool] = mapped_column(Boolean, default=False)
    sending_paused: Mapped[bool] = mapped_column(Boolean, default=True)
    discovery_paused: Mapped[bool] = mapped_column(Boolean, default=False)
    daily_limit: Mapped[int] = mapped_column(Integer, default=20)
    hourly_limit: Mapped[int] = mapped_column(Integer, default=5)
    company_daily_limit: Mapped[int] = mapped_column(Integer, default=2)
    company_weekly_limit: Mapped[int] = mapped_column(Integer, default=5)
    approved_categories: Mapped[list] = mapped_column(JSON, default=list)

class DiscoveryCampaign(Base, TimestampMixin):
    __tablename__="discovery_campaigns"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    cities: Mapped[list] = mapped_column(JSON, default=list)
    districts: Mapped[list] = mapped_column(JSON, default=list)
    company_sizes: Mapped[list] = mapped_column(JSON, default=list)
    industries: Mapped[list] = mapped_column(JSON, default=list)
    contact_roles: Mapped[list] = mapped_column(JSON, default=list)
    score_threshold: Mapped[float] = mapped_column(Float, default=40)
    max_companies: Mapped[int] = mapped_column(Integer, default=25)
    max_contacts_per_company: Mapped[int] = mapped_column(Integer, default=3)
    provider: Mapped[str] = mapped_column(String(80), default="overpass")
    generate_drafts: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(30), default="DRAFT")
    discovered_count: Mapped[int] = mapped_column(Integer, default=0)
    qualified_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str|None] = mapped_column(Text)

class CampaignProspect(Base, TimestampMixin):
    __tablename__="campaign_prospects"
    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("discovery_campaigns.id"), index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    contact_id: Mapped[int|None] = mapped_column(ForeignKey("contacts.id"), index=True)
    draft_id: Mapped[int|None] = mapped_column(ForeignKey("drafts.id"), index=True)
    source_query: Mapped[str|None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="DISCOVERED")
    __table_args__=(UniqueConstraint("campaign_id","company_id","contact_id",name="uq_campaign_prospect"),)

class Job(Base, TimestampMixin):
    __tablename__="jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_type: Mapped[str] = mapped_column(String(50), index=True)
    campaign_id: Mapped[int|None] = mapped_column(ForeignKey("discovery_campaigns.id"), index=True)
    entity_id: Mapped[int|None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default="PENDING", index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    available_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    locked_at: Mapped[datetime|None] = mapped_column(DateTime)
    locked_by: Mapped[str|None] = mapped_column(String(100))
    error_message: Mapped[str|None] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    dedupe_key: Mapped[str] = mapped_column(String(255), unique=True)
    cancelled: Mapped[bool] = mapped_column(Boolean, default=False)

class GmailConnection(Base, TimestampMixin):
    __tablename__="gmail_connections"
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    email: Mapped[str|None] = mapped_column(String(320))
    encrypted_token: Mapped[str|None] = mapped_column(Text)
    scopes: Mapped[list] = mapped_column(JSON, default=list)
    expires_at: Mapped[datetime|None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(30), default="NOT_CONNECTED")
    oauth_state: Mapped[str|None] = mapped_column(String(255))
