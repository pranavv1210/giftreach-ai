from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

APPROVED_CATEGORIES = (
    "Corporate gifts", "Return gifts", "Tanjore art", "Wooden art",
    "Brass idols", "Antiques",
)

class Settings(BaseSettings):
    app_secret: str = "development-only-change-me"
    owner_email: str = "owner@giftreach.local"
    owner_password: str = "change-me-in-production"
    database_url: str = "sqlite:///./giftreach.db"
    frontend_origin: str = "http://localhost:3000"
    gmail_client_id: str | None = None
    gmail_client_secret: str | None = None
    gmail_redirect_uri: str = "http://localhost:8000/api/integrations/gmail/callback"
    openai_api_key: str | None = None
    search_api_key: str | None = None
    email_verification_api_key: str | None = None
    brave_search_api_key: str | None = None
    token_encryption_key: str | None = None
    worker_poll_seconds: int = 3
    environment: str = "development"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()
