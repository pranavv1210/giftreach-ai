import secrets
from datetime import datetime, timedelta, timezone
from fastapi import Cookie, Header, HTTPException, Response
from jose import jwt, JWTError
from passlib.context import CryptContext
from .config import get_settings

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
def verify_password(value: str, expected: str) -> bool:
    return secrets.compare_digest(value.encode(), expected.encode())
def create_session(email: str):
    csrf=secrets.token_urlsafe(24); exp=datetime.now(timezone.utc)+timedelta(hours=12)
    return jwt.encode({"sub":email,"csrf":csrf,"exp":exp}, get_settings().app_secret, algorithm="HS256"), csrf
def current_user(session: str|None=Cookie(None)):
    if not session: raise HTTPException(401,"Authentication required")
    try: return jwt.decode(session,get_settings().app_secret,algorithms=["HS256"])
    except JWTError: raise HTTPException(401,"Session expired")
def require_csrf(user=__import__('fastapi').Depends(current_user), x_csrf_token: str|None=Header(None)):
    if not x_csrf_token or not secrets.compare_digest(x_csrf_token,user["csrf"]): raise HTTPException(403,"Invalid CSRF token")
    return user
def set_session(response: Response, token: str):
    production=get_settings().environment=="production"
    response.set_cookie("session",token,httponly=True,samesite="none" if production else "lax",secure=production,max_age=43200)
