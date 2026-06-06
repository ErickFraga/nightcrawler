"""
RED tests for The Pirate Bay torrent provider.
Uses the unofficial apibay.org JSON API (no HTML scraping).
Category 207 = HD Movies.
"""
import pytest
import httpx
import respx

from ncrawler.torrent.piratebay import PirateBayProvider, TorrentResult


APIBAY_BASE = "https://apibay.org"

SEARCH_RESPONSE = [
    {
        "id": "11111",
        "name": "Inception 2010 1080p BluRay x264",
        "info_hash": "AABBCCDDEEFF00112233445566778899AABBCCDD",
        "leechers": "200",
        "seeders": "1500",
        "num_files": "1",
        "size": "2340000000",
        "username": "uploader1",
        "added": "1278864000",
        "status": "vip",
        "category": "207",
        "imdb": "tt1375666",
    }
]

NO_RESULTS_RESPONSE = [
    {
        "id": "0",
        "name": "No results returned",
        "info_hash": "0000000000000000000000000000000000000000",
        "leechers": "0",
        "seeders": "0",
        "num_files": "0",
        "size": "0",
        "username": "",
        "added": "0",
        "status": "ok",
        "category": "0",
        "imdb": "",
    }
]


@pytest.fixture
def provider():
    return PirateBayProvider()


@pytest.mark.asyncio
async def test_search_returns_torrent_results(provider):
    with respx.mock:
        respx.get(f"{APIBAY_BASE}/q.php").mock(
            return_value=httpx.Response(200, json=SEARCH_RESPONSE)
        )
        results = await provider.search("Inception 2010")

    assert len(results) == 1
    assert isinstance(results[0], TorrentResult)


@pytest.mark.asyncio
async def test_search_extracts_name_from_response(provider):
    with respx.mock:
        respx.get(f"{APIBAY_BASE}/q.php").mock(
            return_value=httpx.Response(200, json=SEARCH_RESPONSE)
        )
        results = await provider.search("Inception 2010")

    assert "Inception" in results[0].title


@pytest.mark.asyncio
async def test_search_builds_magnet_link(provider):
    """A magnet link must be built from info_hash."""
    with respx.mock:
        respx.get(f"{APIBAY_BASE}/q.php").mock(
            return_value=httpx.Response(200, json=SEARCH_RESPONSE)
        )
        results = await provider.search("Inception 2010")

    magnet = results[0].magnet_link
    assert magnet is not None
    assert magnet.startswith("magnet:?xt=urn:btih:")
    assert "AABBCCDDEEFF00112233445566778899AABBCCDD" in magnet.upper()


@pytest.mark.asyncio
async def test_search_returns_seeder_count(provider):
    with respx.mock:
        respx.get(f"{APIBAY_BASE}/q.php").mock(
            return_value=httpx.Response(200, json=SEARCH_RESPONSE)
        )
        results = await provider.search("Inception 2010")

    assert results[0].seeders == 1500


@pytest.mark.asyncio
async def test_search_returns_empty_on_no_results(provider):
    """apibay returns a single-item list with id=0 when nothing found."""
    with respx.mock:
        respx.get(f"{APIBAY_BASE}/q.php").mock(
            return_value=httpx.Response(200, json=NO_RESULTS_RESPONSE)
        )
        results = await provider.search("ZZZNonExistentFilmZZZ")

    assert results == []


@pytest.mark.asyncio
async def test_search_sends_query_and_category_params(provider):
    with respx.mock as m:
        m.get(f"{APIBAY_BASE}/q.php").mock(
            return_value=httpx.Response(200, json=NO_RESULTS_RESPONSE)
        )
        await provider.search("Inception")
        url_str = str(m.calls[0].request.url)
        assert "q=" in url_str
        # category 200 = video (general), 207 = HD movies
        assert "cat=" in url_str


@pytest.mark.asyncio
async def test_search_raises_on_http_error(provider):
    with respx.mock:
        respx.get(f"{APIBAY_BASE}/q.php").mock(
            return_value=httpx.Response(500)
        )
        with pytest.raises(httpx.HTTPStatusError):
            await provider.search("Inception")
