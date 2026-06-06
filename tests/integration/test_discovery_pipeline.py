"""
Integration tests for the full discovery pipeline.
Unit: mocked HTTP. Integration: real TMDB API calls (requires TMDB_API_KEY env var).

Run unit (mocked) version always. Real API tests skipped if TMDB_API_KEY not set.
"""
import os
import pytest
import httpx
import respx

from ncrawler.rules.schema import MonitoringRule, MediaType
from ncrawler.rules.engine import RulesEngine, TitleCandidate
from ncrawler.discovery.tmdb import TMDBClient, TMDBMovie
from ncrawler.discovery.release_finder import ReleaseFinder


TMDB_BASE = "https://api.themoviedb.org/3"
FAKE_KEY = "test-integration-key"
REAL_KEY = os.getenv("TMDB_API_KEY")


# ---------------------------------------------------------------------------
# Mocked pipeline: discovery → rules filtering → candidates
# ---------------------------------------------------------------------------

NOW_PLAYING_RESPONSE = {
    "results": [
        {
            "id": 1001,
            "title": "Action Hero",
            "release_date": "2026-05-20",
            "genre_ids": [28],        # Action
            "vote_average": 7.5,
            "vote_count": 2000,
            "overview": "Great action film.",
            "original_language": "en",
        },
        {
            "id": 1002,
            "title": "Boring Documentary",
            "release_date": "2026-05-18",
            "genre_ids": [99],        # Documentary
            "vote_average": 6.0,
            "vote_count": 100,
            "overview": "Very slow.",
            "original_language": "en",
        },
    ],
    "total_pages": 1,
    "total_results": 2,
}

GENRES_RESPONSE = {
    "genres": [
        {"id": 28, "name": "Action"},
        {"id": 99, "name": "Documentary"},
        {"id": 18, "name": "Drama"},
    ]
}


@pytest.fixture
def action_rule():
    return MonitoringRule(
        id=1,
        name="Action 7+",
        enabled=True,
        genres=["Action"],
        min_rating=7.0,
        directors=[],
        actors=[],
        studios=[],
        media_type=MediaType.MOVIE,
        quality_profile="1080p",
    )


@pytest.fixture
def engine(action_rule):
    return RulesEngine(rules=[action_rule])


@pytest.mark.asyncio
async def test_release_finder_returns_only_matching_titles(engine):
    """ReleaseFinder fetches now_playing, maps genre IDs, and filters by rules."""
    tmdb = TMDBClient(api_key=FAKE_KEY)
    finder = ReleaseFinder(tmdb_client=tmdb, engine=engine)

    empty_page = {"results": [], "total_pages": 0, "total_results": 0}

    with respx.mock:
        respx.get(f"{TMDB_BASE}/movie/now_playing").mock(
            return_value=httpx.Response(200, json=NOW_PLAYING_RESPONSE)
        )
        respx.get(f"{TMDB_BASE}/movie/upcoming").mock(
            return_value=httpx.Response(200, json=empty_page)
        )
        respx.get(f"{TMDB_BASE}/genre/movie/list").mock(
            return_value=httpx.Response(200, json=GENRES_RESPONSE)
        )

        candidates = await finder.find_new_movies()

    # Only Action Hero should pass the action rule
    assert len(candidates) == 1
    assert candidates[0].title == "Action Hero"


@pytest.mark.asyncio
async def test_release_finder_returns_empty_when_nothing_matches(engine):
    only_doc = {**NOW_PLAYING_RESPONSE, "results": [NOW_PLAYING_RESPONSE["results"][1]]}
    empty_page = {"results": [], "total_pages": 0, "total_results": 0}
    tmdb = TMDBClient(api_key=FAKE_KEY)
    finder = ReleaseFinder(tmdb_client=tmdb, engine=engine)

    with respx.mock:
        respx.get(f"{TMDB_BASE}/movie/now_playing").mock(
            return_value=httpx.Response(200, json=only_doc)
        )
        respx.get(f"{TMDB_BASE}/movie/upcoming").mock(
            return_value=httpx.Response(200, json=empty_page)
        )
        respx.get(f"{TMDB_BASE}/genre/movie/list").mock(
            return_value=httpx.Response(200, json=GENRES_RESPONSE)
        )

        candidates = await finder.find_new_movies()

    assert candidates == []


# ---------------------------------------------------------------------------
# Real API tests (skipped if no key)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not REAL_KEY, reason="TMDB_API_KEY not set")
@pytest.mark.asyncio
async def test_real_tmdb_now_playing_returns_results():
    client = TMDBClient(api_key=REAL_KEY)
    movies = await client.get_now_playing()
    assert len(movies) > 0
    assert all(isinstance(m, TMDBMovie) for m in movies)


@pytest.mark.skipif(not REAL_KEY, reason="TMDB_API_KEY not set")
@pytest.mark.asyncio
async def test_real_tmdb_upcoming_returns_results():
    client = TMDBClient(api_key=REAL_KEY)
    movies = await client.get_upcoming()
    assert len(movies) > 0


@pytest.mark.skipif(not REAL_KEY, reason="TMDB_API_KEY not set")
@pytest.mark.asyncio
async def test_real_tmdb_movie_details_has_genres():
    client = TMDBClient(api_key=REAL_KEY)
    movies = await client.get_now_playing()
    if movies:
        details = await client.get_movie_details(movies[0].tmdb_id)
        assert len(details.genres) > 0
