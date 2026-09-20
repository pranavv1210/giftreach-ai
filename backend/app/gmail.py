import base64,hashlib,json,secrets
from datetime import datetime,timedelta
from email.message import EmailMessage
from urllib.parse import urlencode
import httpx
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session
from .config import get_settings
from .models import GmailConnection

SCOPES=["https://www.googleapis.com/auth/gmail.send","openid","email"]
def _fernet():
    secret=get_settings().token_encryption_key or get_settings().app_secret
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest()))
def encrypt_token(data):return _fernet().encrypt(json.dumps(data).encode()).decode()
def decrypt_token(value):return json.loads(_fernet().decrypt(value.encode()))
def authorization_url(db:Session):
    s=get_settings()
    if not s.gmail_client_id or not s.gmail_client_secret:raise ValueError("Gmail OAuth credentials are not configured")
    conn=db.get(GmailConnection,1) or GmailConnection(id=1);conn.oauth_state=secrets.token_urlsafe(32);conn.status="CONNECTING";db.add(conn);db.commit()
    params={"client_id":s.gmail_client_id,"redirect_uri":s.gmail_redirect_uri,"response_type":"code","scope":" ".join(SCOPES),"access_type":"offline","prompt":"consent","state":conn.oauth_state,"include_granted_scopes":"true"}
    return "https://accounts.google.com/o/oauth2/v2/auth?"+urlencode(params)
def exchange_code(db:Session,code,state):
    s=get_settings();conn=db.get(GmailConnection,1)
    if not conn or not state or not secrets.compare_digest(state,conn.oauth_state or ""):raise ValueError("Invalid OAuth state")
    r=httpx.post("https://oauth2.googleapis.com/token",data={"code":code,"client_id":s.gmail_client_id,"client_secret":s.gmail_client_secret,"redirect_uri":s.gmail_redirect_uri,"grant_type":"authorization_code"},timeout=15);r.raise_for_status();token=r.json()
    info=httpx.get("https://openidconnect.googleapis.com/v1/userinfo",headers={"Authorization":f"Bearer {token['access_token']}"},timeout=15);info.raise_for_status()
    conn.email=info.json().get("email");conn.encrypted_token=encrypt_token(token);conn.scopes=token.get("scope","").split();conn.expires_at=datetime.utcnow()+timedelta(seconds=token.get("expires_in",3600));conn.status="CONNECTED";conn.oauth_state=None;db.commit();return conn
def _access_token(db,conn):
    token=decrypt_token(conn.encrypted_token)
    if conn.expires_at and conn.expires_at>datetime.utcnow()+timedelta(minutes=2):return token["access_token"]
    s=get_settings();r=httpx.post("https://oauth2.googleapis.com/token",data={"client_id":s.gmail_client_id,"client_secret":s.gmail_client_secret,"refresh_token":token.get("refresh_token"),"grant_type":"refresh_token"},timeout=15);r.raise_for_status();fresh=r.json();token.update(fresh);conn.encrypted_token=encrypt_token(token);conn.expires_at=datetime.utcnow()+timedelta(seconds=fresh.get("expires_in",3600));db.commit();return token["access_token"]
def send_gmail(db,recipient,subject,body):
    conn=db.get(GmailConnection,1)
    if not conn or conn.status!="CONNECTED" or not conn.encrypted_token:raise ValueError("Gmail is not connected")
    msg=EmailMessage();msg["To"]=recipient;msg["From"]=conn.email;msg["Subject"]=subject;msg.set_content(body)
    raw=base64.urlsafe_b64encode(msg.as_bytes()).decode();token=_access_token(db,conn)
    r=httpx.post("https://gmail.googleapis.com/gmail/v1/users/me/messages/send",headers={"Authorization":f"Bearer {token}"},json={"raw":raw},timeout=20);r.raise_for_status();return r.json()
def revoke(db):
    conn=db.get(GmailConnection,1)
    if conn and conn.encrypted_token:
        try:httpx.post("https://oauth2.googleapis.com/revoke",params={"token":decrypt_token(conn.encrypted_token).get("refresh_token")},timeout=10)
        except httpx.HTTPError:pass
    if conn:conn.encrypted_token=None;conn.email=None;conn.status="NOT_CONNECTED";conn.scopes=[];db.commit()
