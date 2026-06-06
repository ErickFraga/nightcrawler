"""
RED tests for the torrent orchestrator.
Implements fallback chain: YTS → PirateBay → 1337x
Returns the best result (highest seeders) from the first source that responds.
"""
import pytest
from unittest.mock import AsyncMock, patch

from ncrawler.torrent.base import TorrentResult
from ncrawler.torrent.orchestrator import TorrentOrchestrator


def _make_result(source: str, seeders: int, quality: str = "1080p") -> TorrentResult:
    return TorrentResult(
        title="Inception",
        year=2010,
        quality=quality,
        seeders=seeders,
        leechers=100,
        size_bytes=2_000_000_000,
        magnet_link=f"magnet:?xt=urn:btih:FAKE{source.upper()}&dn=Inception",
        torrent_url=None,
        info_hash=f"FAKE{source.upper()}",
        source=source,
    )


@pytest.fixture
def orchestrator():
    return TorrentOrchestrator()


# ---------------------------------------------------------------------------
# Happy path: YTS succeeds first
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_returns_yts_result_when_available(orchestrator):
    yts_results = [_make_result("yts", seeders=5000)]

    with patch.object(orchestrator._yts, "search", new_callable=AsyncMock, return_value=yts_results):
        result = await orchestrator.find_best("Inception", year=2010, quality="1080p")

    assert result is not None
    assert result.source == "yts"
    assert result.seeders == 5000


@pytest.mark.asyncio
async def test_falls_back_to_piratebay_when_yts_empty(orchestrator):
    tpb_results = [_make_result("piratebay", seeders=1500)]

    with patch.object(orchestrator._yts, "search", new_callable=AsyncMock, return_value=[]):
        with patch.object(orchestrator._tpb, "search", new_callable=AsyncMock, return_value=tpb_results):
            result = await orchestrator.find_best("Inception", year=2010, quality="1080p")

    assert result is not None
    assert result.source == "piratebay"


@pytest.mark.asyncio
async def test_falls_back_to_1337x_when_yts_and_tpb_empty(orchestrator):
    l337x_results = [_make_result("1337x", seeders=800)]

    with patch.object(orchestrator._yts, "search", new_callable=AsyncMock, return_value=[]):
        with patch.object(orchestrator._tpb, "search", new_callable=AsyncMock, return_value=[]):
            with patch.object(orchestrator._l337x, "search", new_callable=AsyncMock, return_value=l337x_results):
                result = await orchestrator.find_best("Inception", year=2010, quality="1080p")

    assert result is not None
    assert result.source == "1337x"


@pytest.mark.asyncio
async def test_returns_none_when_all_sources_empty(orchestrator):
    with patch.object(orchestrator._yts, "search", new_callable=AsyncMock, return_value=[]):
        with patch.object(orchestrator._tpb, "search", new_callable=AsyncMock, return_value=[]):
            with patch.object(orchestrator._l337x, "search", new_callable=AsyncMock, return_value=[]):
                result = await orchestrator.find_best("NonExistentFilm", year=2099)

    assert result is None


# ---------------------------------------------------------------------------
# Error tolerance: source raises, falls back gracefully
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_falls_back_when_yts_raises(orchestrator):
    tpb_results = [_make_result("piratebay", seeders=1500)]

    with patch.object(orchestrator._yts, "search", new_callable=AsyncMock, side_effect=Exception("timeout")):
        with patch.object(orchestrator._tpb, "search", new_callable=AsyncMock, return_value=tpb_results):
            result = await orchestrator.find_best("Inception", year=2010)

    assert result is not None
    assert result.source == "piratebay"


@pytest.mark.asyncio
async def test_returns_none_when_all_sources_raise(orchestrator):
    with patch.object(orchestrator._yts, "search", new_callable=AsyncMock, side_effect=Exception("error")):
        with patch.object(orchestrator._tpb, "search", new_callable=AsyncMock, side_effect=Exception("error")):
            with patch.object(orchestrator._l337x, "search", new_callable=AsyncMock, side_effect=Exception("error")):
                result = await orchestrator.find_best("Inception", year=2010)

    assert result is None


# ---------------------------------------------------------------------------
# Quality filtering and best-seeder selection
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_returns_highest_seeder_result_from_source(orchestrator):
    yts_results = [
        _make_result("yts", seeders=3000),
        _make_result("yts", seeders=8000),
        _make_result("yts", seeders=1000),
    ]

    with patch.object(orchestrator._yts, "search", new_callable=AsyncMock, return_value=yts_results):
        result = await orchestrator.find_best("Inception", year=2010, quality="1080p")

    assert result.seeders == 8000


@pytest.mark.asyncio
async def test_search_all_returns_results_from_all_sources(orchestrator):
    """search_all() collects results from every source (no fallback, no early exit)."""
    yts_results = [_make_result("yts", seeders=5000)]
    tpb_results = [_make_result("piratebay", seeders=1500)]
    l337x_results = [_make_result("1337x", seeders=800)]

    with patch.object(orchestrator._yts, "search", new_callable=AsyncMock, return_value=yts_results):
        with patch.object(orchestrator._tpb, "search", new_callable=AsyncMock, return_value=tpb_results):
            with patch.object(orchestrator._l337x, "search", new_callable=AsyncMock, return_value=l337x_results):
                all_results = await orchestrator.search_all("Inception", year=2010)

    sources = {r.source for r in all_results}
    assert "yts" in sources
    assert "piratebay" in sources
    assert "1337x" in sources
