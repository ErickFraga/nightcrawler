"""
RED tests for the /rules REST API.
Uses FastAPI TestClient (synchronous) with an in-memory SQLite DB for isolation.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ncrawler.db.base import Base
import ncrawler.db.models  # registers all models with Base.metadata  # noqa: F401
from ncrawler.main import app
from ncrawler.api.dependencies import get_db


# ── in-memory SQLite for tests ───────────────────────────────────────────────
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


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /rules
# ---------------------------------------------------------------------------

VALID_RULE_PAYLOAD = {
    "name": "Action 7+",
    "enabled": True,
    "genres": ["Action"],
    "min_rating": 7.0,
    "directors": [],
    "actors": [],
    "studios": [],
    "media_type": "movie",
    "quality_profile": "1080p",
}


def test_create_rule_returns_201(client):
    response = client.post("/rules", json=VALID_RULE_PAYLOAD)
    assert response.status_code == 201


def test_create_rule_returns_rule_with_id(client):
    response = client.post("/rules", json=VALID_RULE_PAYLOAD)
    data = response.json()
    assert "id" in data
    assert data["name"] == "Action 7+"


def test_create_rule_stores_all_fields(client):
    response = client.post("/rules", json=VALID_RULE_PAYLOAD)
    data = response.json()
    assert data["genres"] == ["Action"]
    assert data["min_rating"] == 7.0
    assert data["quality_profile"] == "1080p"
    assert data["media_type"] == "movie"


def test_create_rule_rejects_missing_name(client):
    payload = {**VALID_RULE_PAYLOAD}
    del payload["name"]
    response = client.post("/rules", json=payload)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /rules
# ---------------------------------------------------------------------------

def test_list_rules_returns_empty_initially(client):
    response = client.get("/rules")
    assert response.status_code == 200
    assert response.json() == []


def test_list_rules_returns_created_rules(client):
    client.post("/rules", json=VALID_RULE_PAYLOAD)
    client.post("/rules", json={**VALID_RULE_PAYLOAD, "name": "Drama rule"})
    response = client.get("/rules")
    assert len(response.json()) == 2


# ---------------------------------------------------------------------------
# GET /rules/{id}
# ---------------------------------------------------------------------------

def test_get_rule_by_id(client):
    created = client.post("/rules", json=VALID_RULE_PAYLOAD).json()
    response = client.get(f"/rules/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_rule_returns_404_for_unknown_id(client):
    response = client.get("/rules/99999")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /rules/{id}
# ---------------------------------------------------------------------------

def test_update_rule_changes_fields(client):
    created = client.post("/rules", json=VALID_RULE_PAYLOAD).json()
    response = client.patch(
        f"/rules/{created['id']}",
        json={"min_rating": 8.5, "enabled": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["min_rating"] == 8.5
    assert data["enabled"] is False


def test_update_rule_returns_404_for_unknown_id(client):
    response = client.patch("/rules/99999", json={"min_rating": 8.0})
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /rules/{id}
# ---------------------------------------------------------------------------

def test_delete_rule_returns_204(client):
    created = client.post("/rules", json=VALID_RULE_PAYLOAD).json()
    response = client.delete(f"/rules/{created['id']}")
    assert response.status_code == 204


def test_delete_rule_removes_from_list(client):
    created = client.post("/rules", json=VALID_RULE_PAYLOAD).json()
    client.delete(f"/rules/{created['id']}")
    response = client.get("/rules")
    assert response.json() == []


def test_delete_rule_returns_404_for_unknown_id(client):
    response = client.delete("/rules/99999")
    assert response.status_code == 404
