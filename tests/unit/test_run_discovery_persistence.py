"""
RED tests exposing the critical gap: run_discovery() must persist
TitleModel and DownloadModel records to the DB after adding a magnet.
Also covers duplicate-title detection (same tmdb_id should not be added twice).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ncrawler.db.base import Base
import ncrawler.db.models  # noqa: F401 — register models
from ncrawler.db.models.title import TitleModel
from ncrawler.db.models.download import DownloadModel
from ncrawler.rules.engine import TitleCandidate
from ncrawler.rules.schema import MediaType
from ncrawler.torrent.base import TorrentResult
from ncrawler.scheduler.tasks import run_discovery


# ── shared in-memory DB for this test module ─────────────────────────────────

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = Session()
    try:
        yield session
    finally:
        session.close()


# ── helpers ──────────────────────────────────────────────────────────────────

def _candidate(title="Inception", tmdb_id=27205, year=2010) -> TitleCandidate:
    return TitleCandidate(
        title=title, year=year, genres=["Action"], rating=8.8,
        directors=["Christopher Nolan"], actors=["Leonardo DiCaprio"],
        studios=["Warner Bros"], media_type=MediaType.MOVIE,
        tmdb_id=tmdb_id, imdb_id="tt1375666",
    )


def _torrent(title="Inception") -> TorrentResult:
    return TorrentResult(
        title=title, year=2010, quality="1080p", seeders=5000, leechers=200,
        size_bytes=2_000_000_000,
        magnet_link="magnet:?xt=urn:btih:FAKEABC123&dn=Inception",
        torrent_url=None, info_hash="FAKEABC123", source="yts",
    )


def _make_deps(candidates, torrent=None):
    finder = MagicMock()
    finder.find_new_movies = AsyncMock(return_value=candidates)
    finder.find_new_series = AsyncMock(return_value=[])

    orchestrator = MagicMock()
    orchestrator.find_best = AsyncMock(return_value=torrent)

    qb = MagicMock()
    qb.add_magnet = AsyncMock(return_value=True)

    return finder, orchestrator, qb


# ── TitleModel persistence ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_discovery_creates_title_record(db):
    finder, orchestrator, qb = _make_deps([_candidate()], torrent=_torrent())

    await run_discovery(finder=finder, orchestrator=orchestrator, qb_client=qb, db=db)

    titles = db.query(TitleModel).all()
    assert len(titles) == 1
    assert titles[0].title == "Inception"
    assert titles[0].tmdb_id == 27205


@pytest.mark.asyncio
async def test_run_discovery_sets_title_status_to_found(db):
    finder, orchestrator, qb = _make_deps([_candidate()], torrent=_torrent())

    await run_discovery(finder=finder, orchestrator=orchestrator, qb_client=qb, db=db)

    title = db.query(TitleModel).first()
    assert title.status == "found"


@pytest.mark.asyncio
async def test_run_discovery_status_monitoring_when_no_torrent(db):
    finder, orchestrator, qb = _make_deps([_candidate()], torrent=None)

    await run_discovery(finder=finder, orchestrator=orchestrator, qb_client=qb, db=db)

    title = db.query(TitleModel).first()
    assert title is not None
    assert title.status == "monitoring"


# ── DownloadModel persistence ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_discovery_creates_download_record(db):
    finder, orchestrator, qb = _make_deps([_candidate()], torrent=_torrent())

    await run_discovery(finder=finder, orchestrator=orchestrator, qb_client=qb, db=db)

    downloads = db.query(DownloadModel).all()
    assert len(downloads) == 1
    d = downloads[0]
    assert d.source == "yts"
    assert d.info_hash == "FAKEABC123"
    assert d.quality == "1080p"
    assert d.status == "queued"


@pytest.mark.asyncio
async def test_run_discovery_download_linked_to_title(db):
    finder, orchestrator, qb = _make_deps([_candidate()], torrent=_torrent())

    await run_discovery(finder=finder, orchestrator=orchestrator, qb_client=qb, db=db)

    title = db.query(TitleModel).first()
    download = db.query(DownloadModel).first()
    assert download.title_id == title.id


@pytest.mark.asyncio
async def test_run_discovery_no_download_record_when_no_torrent(db):
    finder, orchestrator, qb = _make_deps([_candidate()], torrent=None)

    await run_discovery(finder=finder, orchestrator=orchestrator, qb_client=qb, db=db)

    assert db.query(DownloadModel).count() == 0


# ── Duplicate detection ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_discovery_skips_existing_tmdb_id(db):
    """Same tmdb_id on two runs must NOT create a second TitleModel."""
    existing = TitleModel(
        tmdb_id=27205, title="Inception", year=2010,
        media_type="movie", status="monitoring", rating=8.8,
    )
    existing.genres = ["Action"]
    existing.directors = []
    existing.cast = []
    existing.studios = []
    db.add(existing)
    db.commit()

    finder, orchestrator, qb = _make_deps([_candidate(tmdb_id=27205)], torrent=_torrent())

    await run_discovery(finder=finder, orchestrator=orchestrator, qb_client=qb, db=db)

    assert db.query(TitleModel).count() == 1  # still 1, not 2


@pytest.mark.asyncio
async def test_run_discovery_skips_already_downloaded_title(db):
    """A title already marked downloaded must not be re-queued."""
    existing = TitleModel(
        tmdb_id=27205, title="Inception", year=2010,
        media_type="movie", status="downloaded", rating=8.8,
    )
    existing.genres = []
    existing.directors = []
    existing.cast = []
    existing.studios = []
    db.add(existing)
    db.commit()

    finder, orchestrator, qb = _make_deps([_candidate(tmdb_id=27205)], torrent=_torrent())

    await run_discovery(finder=finder, orchestrator=orchestrator, qb_client=qb, db=db)

    # No new download created
    assert db.query(DownloadModel).count() == 0
    qb.add_magnet.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_discovery_handles_multiple_candidates(db):
    candidates = [
        _candidate("Film A", tmdb_id=1001),
        _candidate("Film B", tmdb_id=1002),
    ]
    finder, orchestrator, qb = _make_deps(candidates, torrent=_torrent())

    await run_discovery(finder=finder, orchestrator=orchestrator, qb_client=qb, db=db)

    assert db.query(TitleModel).count() == 2
    assert db.query(DownloadModel).count() == 2
