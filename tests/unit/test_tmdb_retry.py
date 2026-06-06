"""
RED tests for TMDB client retry / backoff behavior.
- 429 Too Many Requests → wait and retry
- 5xx server errors → retry with backoff
- 404 Not Found → raise immediately (no retry)
- Success after N failures → returns result
"""
import pytest
import httpx
import respx
from unittest.mock import patch, AsyncMock

from ncrawler.discovery.tmdb import TMDBClient

TMDB_BASE = "https://api.themoviedb.org/3"
FAKE_KEY = "test-key"

MOVIE_RESPONSE = {
    "results": [{"id": 1, "title": "Film", "release_date": "2026-01-01",
                 "genre_ids": [28], "vote_average": 7.5, "vote_count": 100,
                 "overview": ""}],
    "total_pages": 1, "total_results": 1,
}


@pytest.fixture
def client():
    return TMDBClient(api_key=FAKE_KEY, max_retries=3, retry_delay=0.0)


# ---------------------------------------------------------------------------
# 429 rate-limit handling
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_retries_once_on_429(client):
    with respx.mock:
        respx.get(f"{TMDB_BASE}/movie/now_playing").mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": "0"}),
                httpx.Response(200, json=MOVIE_RESPONSE),
            ]
        )
        movies = await client.get_now_playing()

    assert len(movies) == 1


@pytest.mark.asyncio
async def test_retries_up_to_max_on_429(client):
    with respx.mock:
        # All 3 attempts → 429 → final raises
        respx.get(f"{TMDB_BASE}/movie/now_playing").mock(
            side_effect=[
                httpx.Response(429),
                httpx.Response(429),
                httpx.Response(429),
            ]
        )
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_now_playing()


@pytest.mark.asyncio
async def test_succeeds_on_third_attempt(client):
    with respx.mock:
        respx.get(f"{TMDB_BASE}/movie/now_playing").mock(
            side_effect=[
                httpx.Response(429),
                httpx.Response(500),
                httpx.Response(200, json=MOVIE_RESPONSE),
            ]
        )
        movies = await client.get_now_playing()

    assert len(movies) == 1


# ---------------------------------------------------------------------------
# 5xx server error handling
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_retries_on_500(client):
    with respx.mock:
        respx.get(f"{TMDB_BASE}/movie/now_playing").mock(
            side_effect=[
                httpx.Response(500),
                httpx.Response(200, json=MOVIE_RESPONSE),
            ]
        )
        movies = await client.get_now_playing()

    assert len(movies) == 1


@pytest.mark.asyncio
async def test_raises_after_all_5xx_retries(client):
    with respx.mock:
        respx.get(f"{TMDB_BASE}/movie/now_playing").mock(
            side_effect=[
                httpx.Response(503),
                httpx.Response(503),
                httpx.Response(503),
            ]
        )
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_now_playing()


# ---------------------------------------------------------------------------
# Non-retryable errors
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_does_not_retry_on_401(client):
    """Auth errors should fail immediately."""
    with respx.mock as m:
        m.get(f"{TMDB_BASE}/movie/now_playing").mock(
            return_value=httpx.Response(401, json={"status_message": "Invalid API key"})
        )
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_now_playing()

        # Only called once — no retry
        assert m.calls.call_count == 1


@pytest.mark.asyncio
async def test_does_not_retry_on_404(client):
    with respx.mock as m:
        m.get(f"{TMDB_BASE}/movie/1").mock(
            return_value=httpx.Response(404, json={"status_message": "Not found"})
        )
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_movie_details(1)

        assert m.calls.call_count == 1


# ---------------------------------------------------------------------------
# Retry count reset between independent calls
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_retry_counter_resets_per_request(client):
    """Two independent requests each get their own retry budget."""
    with respx.mock:
        respx.get(f"{TMDB_BASE}/movie/now_playing").mock(
            side_effect=[
                httpx.Response(429),
                httpx.Response(200, json=MOVIE_RESPONSE),
                httpx.Response(500),
                httpx.Response(200, json=MOVIE_RESPONSE),
            ]
        )
        r1 = await client.get_now_playing()
        r2 = await client.get_now_playing()

    assert len(r1) == 1
    assert len(r2) == 1
