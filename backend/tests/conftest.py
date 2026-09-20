import os
os.environ["DATABASE_URL"]="sqlite:///./test_giftreach.db"
os.environ["APP_SECRET"]="test-secret-long-enough"
os.environ["OWNER_EMAIL"]="owner@example.com"
os.environ["OWNER_PASSWORD"]="correct-horse-battery-staple"
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import Base, engine

@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
    from app.db import SessionLocal
    from app.models import AgentSettings
    with SessionLocal() as db: db.add(AgentSettings(id=1,approved_categories=["Corporate gifts","Return gifts","Tanjore art","Wooden art","Brass idols","Antiques"]));db.commit()
    yield

@pytest.fixture
def client():
    with TestClient(app) as c: yield c

@pytest.fixture
def auth(client):
    r=client.post("/api/auth/login",json={"email":"owner@example.com","password":"correct-horse-battery-staple"})
    assert r.status_code==200
    return {"X-CSRF-Token":r.json()["csrf_token"]}

