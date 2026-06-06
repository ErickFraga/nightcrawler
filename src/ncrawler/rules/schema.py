from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from ncrawler.rules.engine import TitleCandidate


class MediaType(str, Enum):
    MOVIE = "movie"
    SERIES = "series"
    BOTH = "both"


class MonitoringRule(BaseModel):
    id: int
    name: str
    enabled: bool = True
    genres: list[str] = Field(default_factory=list)
    min_rating: float = 0.0
    directors: list[str] = Field(default_factory=list)
    actors: list[str] = Field(default_factory=list)
    studios: list[str] = Field(default_factory=list)
    media_type: MediaType = MediaType.BOTH
    quality_profile: str = "1080p"

    def matches(self, candidate: "TitleCandidate") -> bool:
        if not self.enabled:
            return False

        if self.media_type != MediaType.BOTH and self.media_type != candidate.media_type:
            return False

        if candidate.rating < self.min_rating:
            return False

        if self.genres and not set(self.genres) & set(candidate.genres):
            return False

        if self.directors and not set(self.directors) & set(candidate.directors):
            return False

        if self.actors and not set(self.actors) & set(candidate.actors):
            return False

        if self.studios and not set(self.studios) & set(candidate.studios):
            return False

        return True
