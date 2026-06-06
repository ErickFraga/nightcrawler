"""
RED tests for the TMDB API client.
All HTTP calls are mocked with respx so no real network is used.
"""
import pytest
import httpx
import respx

from ncrawler.discovery.tmdb import TMDBClient, TMDBMovie, TMDBSeries


TMDB_BASE = "https://api.themoviedb.org/3"
FAKE_KEY = "test-api-key"


@pytest.fixture
def client():
    return TMDBClient(api_key=FAKE_KEY)


# ---------------------------------------------------------------------------
# Fixtures: fake TMDB responses
# ---------------------------------------------------------------------------

NOW_PLAYING_RESPONSE = {
    "results": [
        {
            "id": 1001,
            "title": "Thunder Road",
            "release_date": "2026-05-15",
            "genre_ids": [28, 12],
            "vote_average": 7.8,
            "vote_count": 1500,
            "overview": "An action film.",
            "original_language": "en",
        }
    ],
    "total_pages": 1,
    "total_results": 1,
}

MOVIE_DETAILS_RESPONSE = {
    "id": 1001,
    "title": "Thunder Road",
    "release_date": "2026-05-15",
    "genres": [{"id": 28, "name": "Action"}, {"id": 12, "name": "Adventure"}],
    "vote_average": 7.8,
    "vote_count": 1500,
    "imdb_id": "tt9999999",
    "production_companies": [{"id": 1, "name": "Studio X"}],
    "credits": {
        "crew": [{"job": "Director", "name": "Jane Doe"}],
        "cast": [{"name": "Actor One", "order": 0}, {"name": "Actor Two", "order": 1}],
    },
}

AIRING_TODAY_RESPONSE = {
    "results": [
        {
            "id": 2001,
            "name": "Space Opera",
            "first_air_date": "2026-06-01",
            "genre_ids": [10765],
            "vote_average": 8.5,
            "vote_count": 300,
            "overview": "A sci-fi series.",
        }
    ],
    "total_pages": 1,
    "total_results": 1,
}

SERIES_DETAILS_RESPONSE = {
    "id": 2001,
    "name": "Space Opera",
    "first_air_date": "2026-06-01",
    "genres": [{"id": 10765, "name": "Sci-Fi & Fantasy"}],
    "vote_average": 8.5,
    "vote_count": 300,
    "external_ids": {"imdb_id": "tt8888888"},
    "production_companies": [{"id": 2, "name": "Streaming Co"}],
    "created_by": [{"name": "Creator Person"}],
}

UPCOMING_RESPONSE = {
    "results": [
        {
            "id": 3001,
            "title": "Future Film",
            "release_date": "2026-12-25",
            "genre_ids": [18],
            "vote_average": 0.0,
            "vote_count": 0,
            "overview": "Upcoming drama.",
            "original_language": "en",
        }
    ],
    "total_pages": 1,
    "total_results": 1,
}


# ---------------------------------------------------------------------------
# Tests: now_playing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_now_playing_returns_list_of_movies(client):
    with respx.mock:
        respx.get(f"{TMDB_BASE}/movie/now_playing").mock(
            return_value=httpx.Response(200, json=NOW_PLAYING_RESPONSE)
        )
        movies = await client.get_now_playing()

    assert len(movies) == 1
    assert isinstance(movies[0], TMDBMovie)
    assert movies[0].tmdb_id == 1001
    assert movies[0].title == "Thunder Road"
    assert movies[0].rating == 7.8


@pytest.mark.asyncio
async def test_get_now_playing_raises_on_http_error(client):
    with respx.mock:
        respx.get(f"{TMDB_BASE}/movie/now_playing").mock(
            return_value=httpx.Response(401, json={"status_message": "Invalid API key"})
        )
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_now_playing()


# ---------------------------------------------------------------------------
# Tests: upcoming
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_upcoming_returns_list_of_movies(client):
    with respx.mock:
        respx.get(f"{TMDB_BASE}/movie/upcoming").mock(
            return_value=httpx.Response(200, json=UPCOMING_RESPONSE)
        )
        movies = await client.get_upcoming()

    assert len(movies) == 1
    assert movies[0].tmdb_id == 3001
    assert movies[0].title == "Future Film"


# ---------------------------------------------------------------------------
# Tests: movie details (with credits)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_movie_details_returns_full_metadata(client):
    with respx.mock:
        respx.get(f"{TMDB_BASE}/movie/1001").mock(
            return_value=httpx.Response(200, json=MOVIE_DETAILS_RESPONSE)
        )
        movie = await client.get_movie_details(1001)

    assert movie.tmdb_id == 1001
    assert movie.imdb_id == "tt9999999"
    assert "Action" in movie.genres
    assert "Jane Doe" in movie.directors
    assert "Actor One" in movie.cast
    assert "Studio X" in movie.studios


@pytest.mark.asyncio
async def test_get_movie_details_handles_missing_director(client):
    response = {**MOVIE_DETAILS_RESPONSE, "credits": {"crew": [], "cast": []}}
    with respx.mock:
        respx.get(f"{TMDB_BASE}/movie/1001").mock(
            return_value=httpx.Response(200, json=response)
        )
        movie = await client.get_movie_details(1001)

    assert movie.directors == []
    assert movie.cast == []


# ---------------------------------------------------------------------------
# Tests: airing today (series)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_airing_today_returns_series(client):
    with respx.mock:
        respx.get(f"{TMDB_BASE}/tv/airing_today").mock(
            return_value=httpx.Response(200, json=AIRING_TODAY_RESPONSE)
        )
        series_list = await client.get_airing_today()

    assert len(series_list) == 1
    assert isinstance(series_list[0], TMDBSeries)
    assert series_list[0].tmdb_id == 2001
    assert series_list[0].name == "Space Opera"


@pytest.mark.asyncio
async def test_get_series_details_returns_full_metadata(client):
    with respx.mock:
        respx.get(f"{TMDB_BASE}/tv/2001").mock(
            return_value=httpx.Response(200, json=SERIES_DETAILS_RESPONSE)
        )
        series = await client.get_series_details(2001)

    assert series.tmdb_id == 2001
    assert series.imdb_id == "tt8888888"
    assert "Sci-Fi & Fantasy" in series.genres
    assert "Streaming Co" in series.studios


# ---------------------------------------------------------------------------
# Tests: pagination
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_now_playing_sends_correct_api_key(client):
    with respx.mock as m:
        m.get(f"{TMDB_BASE}/movie/now_playing").mock(
            return_value=httpx.Response(200, json=NOW_PLAYING_RESPONSE)
        )
        await client.get_now_playing()
        request = m.calls[0].request
        assert "api_key" in str(request.url) or "Authorization" in request.headers


@pytest.mark.asyncio
async def test_get_now_playing_accepts_page_param(client):
    with respx.mock as m:
        m.get(f"{TMDB_BASE}/movie/now_playing").mock(
            return_value=httpx.Response(200, json=NOW_PLAYING_RESPONSE)
        )
        await client.get_now_playing(page=2)
        request = m.calls[0].request
        assert "page=2" in str(request.url)
