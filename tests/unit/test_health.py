"""
RED tests for the detailed /health endpoint.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from ncrawler.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_health_has_status_field(client):
    response = client.get("/health")
    assert "status" in response.json()


def test_health_has_version_field(client):
    response = client.get("/health")
    assert "version" in response.json()


def test_health_has_components_field(client):
    response = client.get("/health")
    data = response.json()
    assert "components" in data
    components = data["components"]
    assert "database" in components
    assert "scheduler" in components


def test_health_database_component_has_status(client):
    response = client.get("/health")
    db_component = response.json()["components"]["database"]
    assert "status" in db_component
    assert db_component["status"] in ("ok", "error", "unreachable")


def test_health_scheduler_component_has_status(client):
    response = client.get("/health")
    sched_component = response.json()["components"]["scheduler"]
    assert "status" in sched_component
    assert sched_component["status"] in ("ok", "stopped", "not_started")


def test_health_scheduler_has_last_run_field(client):
    response = client.get("/health")
    sched_component = response.json()["components"]["scheduler"]
    # last_run is either a datetime string or null
    assert "last_run" in sched_component


def test_health_returns_ok_status_when_db_reachable(client):
    with patch("ncrawler.api.routers.health.check_db", return_value=True):
        response = client.get("/health")
    assert response.json()["status"] in ("ok", "degraded")
