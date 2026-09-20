from pydantic import BaseModel, EmailStr, Field
from typing import Any

class LoginIn(BaseModel): email: EmailStr; password: str
class CompanyIn(BaseModel):
    name: str = Field(min_length=2, max_length=200); domain: str|None=None; industry: str|None=None; size: str|None=None
    city: str="Bengaluru"; district: str="Bengaluru Urban"; source_url: str|None=None; evidence: str|None=None
class ContactIn(BaseModel):
    company_id: int; name: str|None=None; email: EmailStr; title: str|None=None; department: str|None=None; location: str|None=None
    source_type: str="Founder-provided"; source_url: str|None=None; source_description: str|None=None
class CampaignIn(BaseModel):
    name: str; filters: dict[str,Any]={}; daily_limit: int=Field(20,ge=1,le=100); hourly_limit: int=Field(5,ge=1,le=50); max_contacts_per_company: int=Field(3,ge=1,le=10)
class DraftIn(BaseModel): contact_id: int; campaign_id: int|None=None
class DraftEdit(BaseModel): subject: str=Field(max_length=250); body: str
class AgentPatch(BaseModel): mode: str|None=None; paused: bool|None=None; sending_paused: bool|None=None; discovery_paused: bool|None=None

