"""
RED tests for POST /discovery/trigger — manual discovery run.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ncrawler.db.base import Base
import ncrawler.db.models  # noqa: F401
from ncrawler.main import app
from ncrawler.api.dependencies import get_db


engine = create_engine(
    "sqlite://",
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
# POST /discovery/trigger
# ---------------------------------------------------------------------------

def test_trigger_returns_202(client):
    with patch("ncrawler.api.routers.discovery.run_discovery_now", new_callable=AsyncMock):
        response = client.post("/discovery/trigger")
    assert response.status_code == 202


def test_trigger_returns_accepted_body(client):
    with patch("ncrawler.api.routers.discovery.run_discovery_now", new_callable=AsyncMock):
        response = client.post("/discovery/trigger")
    data = response.json()
    assert data["status"] == "accepted"
    assert "message" in data


def test_trigger_calls_discovery(client):
    with patch("ncrawler.api.routers.discovery.run_discovery_now", new_callable=AsyncMock) as mock_run:
        client.post("/discovery/trigger")
    mock_run.assert_awaited_once()


# ---------------------------------------------------------------------------
# GET /discovery/status
# ---------------------------------------------------------------------------

def test_discovery_status_returns_200(client):
    response = client.get("/discovery/status")
    assert response.status_code == 200


def test_discovery_status_has_required_fields(client):
    response = client.get("/discovery/status")
    data = response.json()
    assert "last_run" in data
    assert "next_run" in data
    assert "status" in data
