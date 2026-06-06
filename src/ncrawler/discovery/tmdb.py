from __future__ import annotations

from dataclasses import dataclass, field

import httpx

TMDB_BASE = "https://api.themoviedb.org/3"


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
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=TMDB_BASE,
            params={"api_key": api_key},
            timeout=30,
        )

    def _common_params(self, extra: dict | None = None) -> dict:
        params = {"api_key": self._api_key}
        if extra:
            params.update(extra)
        return params

    async def _get(self, path: str, params: dict | None = None) -> dict:
        response = await self._client.get(path, params=params or {})
        response.raise_for_status()
        return response.json()

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
