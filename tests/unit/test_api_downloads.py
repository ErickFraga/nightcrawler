"""
RED tests for /titles and /downloads REST endpoints.
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


TITLE_PAYLOAD = {
    "tmdb_id": 27205,
    "imdb_id": "tt1375666",
    "title": "Inception",
    "year": 2010,
    "media_type": "movie",
    "genres": ["Action", "Sci-Fi"],
    "rating": 8.8,
    "directors": ["Christopher Nolan"],
    "cast": ["Leonardo DiCaprio"],
    "studios": ["Warner Bros"],
}

DOWNLOAD_PAYLOAD = {
    "source": "yts",
    "magnet_link": "magnet:?xt=urn:btih:FAKE&dn=Inception",
    "info_hash": "FAKEABC123",
    "quality": "1080p",
}


# ---------------------------------------------------------------------------
# POST /titles + GET /titles
# ---------------------------------------------------------------------------

def test_create_title_returns_201(client):
    response = client.post("/titles", json=TITLE_PAYLOAD)
    assert response.status_code == 201


def test_create_title_has_monitoring_status(client):
    response = client.post("/titles", json=TITLE_PAYLOAD)
    assert response.json()["status"] == "monitoring"


def test_list_titles_empty_initially(client):
    response = client.get("/titles")
    assert response.status_code == 200
    assert response.json() == []


def test_list_titles_returns_created(client):
    client.post("/titles", json=TITLE_PAYLOAD)
    response = client.get("/titles")
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Inception"


def test_get_title_by_id(client):
    created = client.post("/titles", json=TITLE_PAYLOAD).json()
    response = client.get(f"/titles/{created['id']}")
    assert response.status_code == 200
    assert response.json()["imdb_id"] == "tt1375666"


def test_get_title_404_for_unknown(client):
    response = client.get("/titles/99999")
    assert response.status_code == 404


def test_filter_titles_by_status(client):
    client.post("/titles", json=TITLE_PAYLOAD)
    response = client.get("/titles?status=monitoring")
    assert len(response.json()) == 1
    response2 = client.get("/titles?status=downloaded")
    assert response2.json() == []


def test_filter_titles_by_media_type(client):
    client.post("/titles", json=TITLE_PAYLOAD)
    series_payload = {**TITLE_PAYLOAD, "tmdb_id": 99999, "title": "Breaking Bad", "media_type": "series"}
    client.post("/titles", json=series_payload)

    movies = client.get("/titles?media_type=movie").json()
    series = client.get("/titles?media_type=series").json()
    assert len(movies) == 1
    assert len(series) == 1


# ---------------------------------------------------------------------------
# POST /titles/{id}/downloads
# ---------------------------------------------------------------------------

def test_create_download_job_returns_201(client):
    title = client.post("/titles", json=TITLE_PAYLOAD).json()
    response = client.post(f"/titles/{title['id']}/downloads", json=DOWNLOAD_PAYLOAD)
    assert response.status_code == 201


def test_create_download_sets_queued_status(client):
    title = client.post("/titles", json=TITLE_PAYLOAD).json()
    download = client.post(f"/titles/{title['id']}/downloads", json=DOWNLOAD_PAYLOAD).json()
    assert download["status"] == "queued"


def test_create_download_links_to_title(client):
    title = client.post("/titles", json=TITLE_PAYLOAD).json()
    download = client.post(f"/titles/{title['id']}/downloads", json=DOWNLOAD_PAYLOAD).json()
    assert download["title_id"] == title["id"]


def test_create_download_updates_title_status_to_found(client):
    title = client.post("/titles", json=TITLE_PAYLOAD).json()
    client.post(f"/titles/{title['id']}/downloads", json=DOWNLOAD_PAYLOAD)
    updated_title = client.get(f"/titles/{title['id']}").json()
    assert updated_title["status"] == "found"


# ---------------------------------------------------------------------------
# GET /downloads
# ---------------------------------------------------------------------------

def test_list_downloads_empty_initially(client):
    response = client.get("/downloads")
    assert response.status_code == 200
    assert response.json() == []


def test_list_downloads_returns_created_jobs(client):
    title = client.post("/titles", json=TITLE_PAYLOAD).json()
    client.post(f"/titles/{title['id']}/downloads", json=DOWNLOAD_PAYLOAD)
    response = client.get("/downloads")
    assert len(response.json()) == 1


def test_filter_downloads_by_status(client):
    title = client.post("/titles", json=TITLE_PAYLOAD).json()
    client.post(f"/titles/{title['id']}/downloads", json=DOWNLOAD_PAYLOAD)
    queued = client.get("/downloads?status=queued").json()
    assert len(queued) == 1
    completed = client.get("/downloads?status=completed").json()
    assert completed == []


# ---------------------------------------------------------------------------
# PATCH /downloads/{id} — status update
# ---------------------------------------------------------------------------

def test_update_download_status(client):
    title = client.post("/titles", json=TITLE_PAYLOAD).json()
    download = client.post(f"/titles/{title['id']}/downloads", json=DOWNLOAD_PAYLOAD).json()
    response = client.patch(f"/downloads/{download['id']}", json={"status": "downloading"})
    assert response.status_code == 200
    assert response.json()["status"] == "downloading"


def test_update_download_completed_sets_file_path(client):
    title = client.post("/titles", json=TITLE_PAYLOAD).json()
    download = client.post(f"/titles/{title['id']}/downloads", json=DOWNLOAD_PAYLOAD).json()
    response = client.patch(
        f"/downloads/{download['id']}",
        json={"status": "completed", "file_path": "/library/movies/Inception (2010)/Inception (2010).mkv"},
    )
    assert response.json()["file_path"].endswith("Inception (2010).mkv")
