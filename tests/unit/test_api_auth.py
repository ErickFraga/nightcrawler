"""
RED tests for API Key authentication.

Protected endpoints require X-API-Key header.
Public endpoints (/health, /docs, /openapi.json) remain open.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ncrawler.db.base import Base
import ncrawler.db.models  # noqa: F401
from ncrawler.main import app
from ncrawler.api.dependencies import get_db

SQLALCHEMY_TEST_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


VALID_KEY = "test-secret-key-1234"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("API_KEY", VALID_KEY)
    monkeypatch.setenv("TMDB_API_KEY", "fake")  # suppress config errors
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Public endpoints — no key required
# ---------------------------------------------------------------------------

def test_health_is_public(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_docs_is_public(client):
    response = client.get("/docs")
    assert response.status_code == 200


def test_openapi_json_is_public(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Protected endpoints — key required
# ---------------------------------------------------------------------------

def test_list_rules_requires_api_key(client):
    response = client.get("/rules")
    assert response.status_code == 401


def test_list_rules_accepts_valid_key(client):
    response = client.get("/rules", headers={"X-API-Key": VALID_KEY})
    assert response.status_code == 200


def test_create_rule_requires_api_key(client):
    response = client.post("/rules", json={
        "name": "Test", "genres": [], "min_rating": 0,
        "directors": [], "actors": [], "studios": [],
        "media_type": "movie", "quality_profile": "1080p",
    })
    assert response.status_code == 401


def test_create_rule_accepts_valid_key(client):
    response = client.post(
        "/rules",
        json={
            "name": "Test", "genres": [], "min_rating": 0,
            "directors": [], "actors": [], "studios": [],
            "media_type": "movie", "quality_profile": "1080p",
        },
        headers={"X-API-Key": VALID_KEY},
    )
    assert response.status_code == 201


def test_wrong_api_key_returns_401(client):
    response = client.get("/rules", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 401


def test_list_titles_requires_api_key(client):
    response = client.get("/titles")
    assert response.status_code == 401


def test_list_downloads_requires_api_key(client):
    response = client.get("/downloads")
    assert response.status_code == 401


def test_discovery_trigger_requires_api_key(client):
    response = client.post("/discovery/trigger")
    assert response.status_code == 401


def test_discovery_status_requires_api_key(client):
    response = client.get("/discovery/status")
    assert response.status_code == 401


def test_api_key_missing_returns_meaningful_error(client):
    response = client.get("/rules")
    data = response.json()
    assert "detail" in data
