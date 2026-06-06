from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

import httpx

TMDB_BASE = "https://api.themoviedb.org/3"
logger = logging.getLogger(__name__)

# HTTP status codes that warrant a retry
_RETRYABLE = {429, 500, 502, 503, 504}
# HTTP status codes that should fail immediately without retry
_NO_RETRY = {400, 401, 403, 404, 422}


@dataclass
class TMDBMovie:
    tmdb_id: int
    title: str
    year: int | None
    genre_ids: list[int]
    genres: list[str]
    rating: float
    vote_count: int
    imdb_id: str | None = None
    directors: list[str] = field(default_factory=list)
    cast: list[str] = field(default_factory=list)
    studios: list[str] = field(default_factory=list)
    overview: str = ""


@dataclass
class TMDBSeries:
    tmdb_id: int
    name: str
    year: int | None
    genre_ids: list[int]
    genres: list[str]
    rating: float
    vote_count: int
    imdb_id: str | None = None
    directors: list[str] = field(default_factory=list)
    cast: list[str] = field(default_factory=list)
    studios: list[str] = field(default_factory=list)
    overview: str = ""


def _parse_year(date_str: str | None) -> int | None:
    if date_str and len(date_str) >= 4:
        try:
            return int(date_str[:4])
        except ValueError:
            return None
    return None


class TMDBClient:
    def __init__(self, api_key: str, max_retries: int = 3, retry_delay: float = 1.0) -> None:
        self._api_key = api_key
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._client = httpx.AsyncClient(
            base_url=TMDB_BASE,
            params={"api_key": api_key},
            timeout=30,
        )

    async def _get(self, path: str, params: dict | None = None) -> dict:
        last_exc: httpx.HTTPStatusError | None = None
        for attempt in range(self._max_retries):
            response = await self._client.get(path, params=params or {})
            if response.status_code in _NO_RETRY:
                response.raise_for_status()
            if response.status_code < 400:
                return response.json()
            if response.status_code in _RETRYABLE:
                last_exc = httpx.HTTPStatusError(
                    f"HTTP {response.status_code}", request=response.request, response=response
                )
                wait = self._retry_delay * (2 ** attempt)
                logger.warning("TMDB %s → %d, retry %d/%d in %.1fs",
                               path, response.status_code, attempt + 1, self._max_retries, wait)
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(wait)
                continue
            response.raise_for_status()
        raise last_exc  # type: ignore[misc]

    # ------------------------------------------------------------------
    # Movies
    # ------------------------------------------------------------------

    async def get_now_playing(self, page: int = 1) -> list[TMDBMovie]:
        data = await self._get("/movie/now_playing", {"page": page})
        return [self._parse_movie_summary(r) for r in data.get("results", [])]

    async def get_upcoming(self, page: int = 1) -> list[TMDBMovie]:
        data = await self._get("/movie/upcoming", {"page": page})
        return [self._parse_movie_summary(r) for r in data.get("results", [])]

    async def get_movie_details(self, tmdb_id: int) -> TMDBMovie:
        data = await self._get(f"/movie/{tmdb_id}", {"append_to_response": "credits"})
        crew = data.get("credits", {}).get("crew", [])
        cast_raw = data.get("credits", {}).get("cast", [])
        directors = [p["name"] for p in crew if p.get("job") == "Director"]
        cast = [p["name"] for p in sorted(cast_raw, key=lambda x: x.get("order", 999))[:10]]
        studios = [c["name"] for c in data.get("production_companies", [])]
        genres = [g["name"] for g in data.get("genres", [])]
        return TMDBMovie(
            tmdb_id=data["id"],
            title=data["title"],
            year=_parse_year(data.get("release_date")),
            genre_ids=[g["id"] for g in data.get("genres", [])],
            genres=genres,
            rating=data.get("vote_average", 0.0),
            vote_count=data.get("vote_count", 0),
            imdb_id=data.get("imdb_id"),
            directors=directors,
            cast=cast,
            studios=studios,
            overview=data.get("overview", ""),
        )

    # ------------------------------------------------------------------
    # Series
    # ------------------------------------------------------------------

    async def get_airing_today(self, page: int = 1) -> list[TMDBSeries]:
        data = await self._get("/tv/airing_today", {"page": page})
        return [self._parse_series_summary(r) for r in data.get("results", [])]

    async def get_series_details(self, tmdb_id: int) -> TMDBSeries:
        data = await self._get(f"/tv/{tmdb_id}", {"append_to_response": "external_ids"})
        external_ids = data.get("external_ids", {})
        genres = [g["name"] for g in data.get("genres", [])]
        studios = [c["name"] for c in data.get("production_companies", [])]
        creators = [c["name"] for c in data.get("created_by", [])]
        return TMDBSeries(
            tmdb_id=data["id"],
            name=data["name"],
            year=_parse_year(data.get("first_air_date")),
            genre_ids=[g["id"] for g in data.get("genres", [])],
            genres=genres,
            rating=data.get("vote_average", 0.0),
            vote_count=data.get("vote_count", 0),
            imdb_id=external_ids.get("imdb_id"),
            directors=creators,
            cast=[],
            studios=studios,
            overview=data.get("overview", ""),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _parse_movie_summary(self, raw: dict) -> TMDBMovie:
        return TMDBMovie(
            tmdb_id=raw["id"],
            title=raw["title"],
            year=_parse_year(raw.get("release_date")),
            genre_ids=raw.get("genre_ids", []),
            genres=[],
            rating=raw.get("vote_average", 0.0),
            vote_count=raw.get("vote_count", 0),
            overview=raw.get("overview", ""),
        )

    def _parse_series_summary(self, raw: dict) -> TMDBSeries:
        return TMDBSeries(
            tmdb_id=raw["id"],
            name=raw["name"],
            year=_parse_year(raw.get("first_air_date")),
            genre_ids=raw.get("genre_ids", []),
            genres=[],
            rating=raw.get("vote_average", 0.0),
            vote_count=raw.get("vote_count", 0),
            overview=raw.get("overview", ""),
        )

    async def get_genre_map(self, media: str = "movie") -> dict[int, str]:
        data = await self._get(f"/genre/{media}/list")
        return {g["id"]: g["name"] for g in data.get("genres", [])}
