from __future__ import annotations

from dataclasses import dataclass, field

from ncrawler.rules.schema import MediaType, MonitoringRule


@dataclass
class TitleCandidate:
    title: str
    year: int
    genres: list[str]
    rating: float
    directors: list[str]
    actors: list[str]
    studios: list[str]
    media_type: MediaType
    tmdb_id: int | None = None
    imdb_id: str | None = None


class RulesEngine:
    def __init__(self, rules: list[MonitoringRule]) -> None:
        self._rules = rules

    def evaluate(self, candidate: TitleCandidate) -> list[MonitoringRule]:
        return [rule for rule in self._rules if rule.matches(candidate)]
