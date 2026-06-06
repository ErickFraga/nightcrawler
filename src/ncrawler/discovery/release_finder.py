from __future__ import annotations

from ncrawler.discovery.tmdb import TMDBClient, TMDBMovie, TMDBSeries
from ncrawler.rules.engine import RulesEngine, TitleCandidate
from ncrawler.rules.schema import MediaType


class ReleaseFinder:
    def __init__(self, tmdb_client: TMDBClient, engine: RulesEngine) -> None:
        self._tmdb = tmdb_client
        self._engine = engine

    async def find_new_movies(self) -> list[TitleCandidate]:
        genre_map = await self._tmdb.get_genre_map("movie")
        movies = await self._tmdb.get_now_playing()
        movies += await self._tmdb.get_upcoming()

        seen: set[int] = set()
        candidates: list[TitleCandidate] = []

        for movie in movies:
            if movie.tmdb_id in seen:
                continue
            seen.add(movie.tmdb_id)

            genres = [genre_map.get(gid, "") for gid in movie.genre_ids]
            candidate = TitleCandidate(
                title=movie.title,
                year=movie.year or 0,
                genres=genres,
                rating=movie.rating,
                directors=movie.directors,
                actors=movie.cast,
                studios=movie.studios,
                media_type=MediaType.MOVIE,
                tmdb_id=movie.tmdb_id,
                imdb_id=movie.imdb_id,
            )

            if self._engine.evaluate(candidate):
                candidates.append(candidate)

        return candidates

    async def find_new_series(self) -> list[TitleCandidate]:
        genre_map = await self._tmdb.get_genre_map("tv")
        series_list = await self._tmdb.get_airing_today()

        candidates: list[TitleCandidate] = []
        seen: set[int] = set()

        for series in series_list:
            if series.tmdb_id in seen:
                continue
            seen.add(series.tmdb_id)

            genres = [genre_map.get(gid, "") for gid in series.genre_ids]
            candidate = TitleCandidate(
                title=series.name,
                year=series.year or 0,
                genres=genres,
                rating=series.rating,
                directors=series.directors,
                actors=series.cast,
                studios=series.studios,
                media_type=MediaType.SERIES,
                tmdb_id=series.tmdb_id,
                imdb_id=series.imdb_id,
            )

            if self._engine.evaluate(candidate):
                candidates.append(candidate)

        return candidates
