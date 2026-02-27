import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from database.session import Base, get_db
import database.session
from database import models

# Setup an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
import api
api.SessionLocal = TestingSessionLocal  # ensure background tasks use the test db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_create_short_url():
    response = client.post(
        "/api/shorten",
        json={"original_url": "https://www.example.com"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["original_url"] == "https://www.example.com/"
    assert "short_code" in data
    assert len(data["short_code"]) == 7

def test_redirect_to_url():
    # 1. Create a URL
    create_response = client.post(
        "/api/shorten",
        json={"original_url": "https://www.google.com"}
    )
    short_code = create_response.json()["short_code"]
    
    # 2. Test Redirection
    redirect_response = client.get(f"/{short_code}", follow_redirects=False)
    assert redirect_response.status_code == 302
    assert redirect_response.headers["location"] == "https://www.google.com/"

def test_redirect_not_found():
    response = client.get("/invalidCode123")
    assert response.status_code == 404

def test_get_url_stats():
    # 1. Create a URL
    create_response = client.post(
        "/api/shorten",
        json={"original_url": "https://www.teststats.com"}
    )
    short_code = create_response.json()["short_code"]
    
    # 2. Click it twice
    client.get(f"/{short_code}", headers={"User-Agent": "TestBrowser"})
    client.get(f"/{short_code}", headers={"User-Agent": "TestBrowser2"})
    
    # 3. Check stats
    stats_response = client.get(f"/api/stats/{short_code}")
    assert stats_response.status_code == 200
    stats_data = stats_response.json()
    assert stats_data["clicks"] == 2
    assert len(stats_data["analytics"]) == 2
    assert stats_data["analytics"][0]["user_agent"] in ["TestBrowser", "TestBrowser2"]
