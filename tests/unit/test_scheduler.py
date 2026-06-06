"""
RED tests for the scheduler task logic (fully mocked — no APScheduler internals).
Tests the run_discovery() coroutine that wires together discovery + torrent + download.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ncrawler.rules.engine import TitleCandidate
from ncrawler.rules.schema import MediaType
from ncrawler.torrent.base import TorrentResult
from ncrawler.scheduler.tasks import run_discovery


def _make_db() -> MagicMock:
    """Return a MagicMock DB session where query().filter().first() → None (no existing titles)."""
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    return db


def _make_candidate(title: str = "Inception", tmdb_id: int = 1001) -> TitleCandidate:
    return TitleCandidate(
        title=title,
        year=2010,
        genres=["Action"],
        rating=8.8,
        directors=["Christopher Nolan"],
        actors=["Leonardo DiCaprio"],
        studios=["Warner Bros"],
        media_type=MediaType.MOVIE,
        tmdb_id=tmdb_id,
        imdb_id="tt1375666",
    )


def _make_torrent(title: str = "Inception") -> TorrentResult:
    return TorrentResult(
        title=title,
        year=2010,
        quality="1080p",
        seeders=5000,
        leechers=200,
        size_bytes=2_000_000_000,
        magnet_link="magnet:?xt=urn:btih:FAKEABC&dn=Inception",
        torrent_url=None,
        info_hash="FAKEABC",
        source="yts",
    )


# ---------------------------------------------------------------------------
# run_discovery: end-to-end task flow
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_discovery_calls_release_finder(tmp_path):
    finder = MagicMock()
    finder.find_new_movies = AsyncMock(return_value=[])
    finder.find_new_series = AsyncMock(return_value=[])
    orchestrator = MagicMock()
    qb = MagicMock()
    db = _make_db()

    await run_discovery(finder=finder, orchestrator=orchestrator, qb_client=qb, db=db)

    finder.find_new_movies.assert_awaited_once()
    finder.find_new_series.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_discovery_searches_torrent_for_each_candidate():
    candidate = _make_candidate()
    finder = MagicMock()
    finder.find_new_movies = AsyncMock(return_value=[candidate])
    finder.find_new_series = AsyncMock(return_value=[])

    orchestrator = MagicMock()
    orchestrator.find_best = AsyncMock(return_value=None)

    qb = MagicMock()
    db = _make_db()

    await run_discovery(finder=finder, orchestrator=orchestrator, qb_client=qb, db=db)

    orchestrator.find_best.assert_awaited_once_with(
        "Inception", year=2010, quality="1080p"
    )


@pytest.mark.asyncio
async def test_run_discovery_adds_magnet_when_torrent_found():
    candidate = _make_candidate()
    torrent = _make_torrent()

    finder = MagicMock()
    finder.find_new_movies = AsyncMock(return_value=[candidate])
    finder.find_new_series = AsyncMock(return_value=[])

    orchestrator = MagicMock()
    orchestrator.find_best = AsyncMock(return_value=torrent)

    qb = MagicMock()
    qb.add_magnet = AsyncMock(return_value=True)

    db = _make_db()

    await run_discovery(finder=finder, orchestrator=orchestrator, qb_client=qb, db=db)

    qb.add_magnet.assert_awaited_once()
    call_kwargs = qb.add_magnet.call_args
    assert "magnet" in call_kwargs.kwargs or call_kwargs.args


@pytest.mark.asyncio
async def test_run_discovery_skips_magnet_when_no_torrent_found():
    candidate = _make_candidate()

    finder = MagicMock()
    finder.find_new_movies = AsyncMock(return_value=[candidate])
    finder.find_new_series = AsyncMock(return_value=[])

    orchestrator = MagicMock()
    orchestrator.find_best = AsyncMock(return_value=None)

    qb = MagicMock()
    qb.add_magnet = AsyncMock()

    db = _make_db()

    await run_discovery(finder=finder, orchestrator=orchestrator, qb_client=qb, db=db)

    qb.add_magnet.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_discovery_handles_multiple_candidates():
    candidates = [_make_candidate("Film A", 1001), _make_candidate("Film B", 1002)]
    torrent = _make_torrent()

    finder = MagicMock()
    finder.find_new_movies = AsyncMock(return_value=candidates)
    finder.find_new_series = AsyncMock(return_value=[])

    orchestrator = MagicMock()
    orchestrator.find_best = AsyncMock(return_value=torrent)

    qb = MagicMock()
    qb.add_magnet = AsyncMock(return_value=True)

    db = _make_db()

    await run_discovery(finder=finder, orchestrator=orchestrator, qb_client=qb, db=db)

    assert orchestrator.find_best.await_count == 2
    assert qb.add_magnet.await_count == 2


@pytest.mark.asyncio
async def test_run_discovery_continues_after_torrent_error():
    """A failure on one candidate must not abort the entire run."""
    candidates = [_make_candidate("Film A", 1001), _make_candidate("Film B", 1002)]

    finder = MagicMock()
    finder.find_new_movies = AsyncMock(return_value=candidates)
    finder.find_new_series = AsyncMock(return_value=[])

    orchestrator = MagicMock()
    orchestrator.find_best = AsyncMock(side_effect=[Exception("network error"), _make_torrent()])

    qb = MagicMock()
    qb.add_magnet = AsyncMock(return_value=True)

    db = MagicMock()

    # Should not raise
    await run_discovery(finder=finder, orchestrator=orchestrator, qb_client=qb, db=db)

    # Second candidate still processed
    qb.add_magnet.assert_awaited_once()
