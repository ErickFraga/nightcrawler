"""
RED tests for the YTS torrent provider.
YTS has an official public JSON API — no scraping needed.
"""
import pytest
import httpx
import respx

from ncrawler.torrent.yts import YTSProvider, TorrentResult


YTS_BASE = "https://yts.mx/api/v2"

LIST_MOVIES_RESPONSE = {
    "status": "ok",
    "data": {
        "movie_count": 1,
        "movies": [
            {
                "id": 55555,
                "title": "Inception",
                "year": 2010,
                "rating": 8.8,
                "imdb_code": "tt1375666",
                "torrents": [
                    {
                        "url": "https://yts.mx/torrent/download/ABC123",
                        "hash": "ABC123HASH",
                        "quality": "1080p",
                        "type": "bluray",
                        "seeds": 5000,
                        "peers": 800,
                        "size": "2.18 GB",
                        "size_bytes": 2340000000,
                    },
                    {
                        "url": "https://yts.mx/torrent/download/DEF456",
                        "hash": "DEF456HASH",
                        "quality": "720p",
                        "type": "bluray",
                        "seeds": 3000,
                        "peers": 500,
                        "size": "1.10 GB",
                        "size_bytes": 1180000000,
                    },
                ],
            }
        ],
    },
}

EMPTY_RESPONSE = {
    "status": "ok",
    "data": {
        "movie_count": 0,
    },
}


@pytest.fixture
def provider():
    return YTSProvider()


@pytest.mark.asyncio
async def test_search_returns_torrent_results(provider):
    with respx.mock:
        respx.get(f"{YTS_BASE}/list_movies.json").mock(
            return_value=httpx.Response(200, json=LIST_MOVIES_RESPONSE)
        )
        results = await provider.search("Inception", year=2010)

    assert len(results) >= 1
    assert all(isinstance(r, TorrentResult) for r in results)


@pytest.mark.asyncio
async def test_search_returns_correct_title_and_year(provider):
    with respx.mock:
        respx.get(f"{YTS_BASE}/list_movies.json").mock(
            return_value=httpx.Response(200, json=LIST_MOVIES_RESPONSE)
        )
        results = await provider.search("Inception", year=2010)

    assert results[0].title == "Inception"
    assert results[0].year == 2010


@pytest.mark.asyncio
async def test_search_filters_by_preferred_quality(provider):
    """Provider should prefer 1080p results."""
    with respx.mock:
        respx.get(f"{YTS_BASE}/list_movies.json").mock(
            return_value=httpx.Response(200, json=LIST_MOVIES_RESPONSE)
        )
        results = await provider.search("Inception", year=2010, quality="1080p")

    qualities = [r.quality for r in results]
    assert "1080p" in qualities


@pytest.mark.asyncio
async def test_search_returns_magnet_or_torrent_url(provider):
    with respx.mock:
        respx.get(f"{YTS_BASE}/list_movies.json").mock(
            return_value=httpx.Response(200, json=LIST_MOVIES_RESPONSE)
        )
        results = await provider.search("Inception", year=2010)

    r = results[0]
    assert r.magnet_link or r.torrent_url


@pytest.mark.asyncio
async def test_search_returns_empty_on_no_results(provider):
    with respx.mock:
        respx.get(f"{YTS_BASE}/list_movies.json").mock(
            return_value=httpx.Response(200, json=EMPTY_RESPONSE)
        )
        results = await provider.search("NonExistentFilm12345", year=2099)

    assert results == []


@pytest.mark.asyncio
async def test_search_raises_on_api_error(provider):
    with respx.mock:
        respx.get(f"{YTS_BASE}/list_movies.json").mock(
            return_value=httpx.Response(503)
        )
        with pytest.raises(httpx.HTTPStatusError):
            await provider.search("Inception")


@pytest.mark.asyncio
async def test_search_includes_seeder_count(provider):
    with respx.mock:
        respx.get(f"{YTS_BASE}/list_movies.json").mock(
            return_value=httpx.Response(200, json=LIST_MOVIES_RESPONSE)
        )
        results = await provider.search("Inception", quality="1080p")

    assert results[0].seeders == 5000


@pytest.mark.asyncio
async def test_search_sends_query_param(provider):
    with respx.mock as m:
        m.get(f"{YTS_BASE}/list_movies.json").mock(
            return_value=httpx.Response(200, json=EMPTY_RESPONSE)
        )
        await provider.search("Inception", year=2010)
        url_str = str(m.calls[0].request.url)
        assert "query_term" in url_str
