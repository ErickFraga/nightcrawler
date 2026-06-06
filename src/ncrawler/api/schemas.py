from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from ncrawler.rules.schema import MediaType


# ── Rules ────────────────────────────────────────────────────────────────────

class RuleCreate(BaseModel):
    name: str
    enabled: bool = True
    genres: list[str] = Field(default_factory=list)
    min_rating: float = 0.0
    directors: list[str] = Field(default_factory=list)
    actors: list[str] = Field(default_factory=list)
    studios: list[str] = Field(default_factory=list)
    media_type: MediaType = MediaType.BOTH
    quality_profile: str = "1080p"


class RuleUpdate(BaseModel):
    name: Optional[str] = None
    enabled: Optional[bool] = None
    genres: Optional[list[str]] = None
    min_rating: Optional[float] = None
    directors: Optional[list[str]] = None
    actors: Optional[list[str]] = None
    studios: Optional[list[str]] = None
    media_type: Optional[MediaType] = None
    quality_profile: Optional[str] = None


class RuleRead(BaseModel):
    id: int
    name: str
    enabled: bool
    genres: list[str]
    min_rating: float
    directors: list[str]
    actors: list[str]
    studios: list[str]
    media_type: MediaType
    quality_profile: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Titles ───────────────────────────────────────────────────────────────────

class TitleCreate(BaseModel):
    tmdb_id: Optional[int] = None
    imdb_id: Optional[str] = None
    title: str
    year: Optional[int] = None
    media_type: MediaType = MediaType.MOVIE
    genres: list[str] = Field(default_factory=list)
    rating: float = 0.0
    directors: list[str] = Field(default_factory=list)
    cast: list[str] = Field(default_factory=list)
    studios: list[str] = Field(default_factory=list)


class TitleRead(BaseModel):
    id: int
    tmdb_id: Optional[int]
    imdb_id: Optional[str]
    title: str
    year: Optional[int]
    media_type: str
    genres: list[str]
    rating: float
    directors: list[str]
    cast: list[str]
    studios: list[str]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Downloads ─────────────────────────────────────────────────────────────────

class DownloadCreate(BaseModel):
    source: str
    magnet_link: Optional[str] = None
    info_hash: Optional[str] = None
    quality: str = "1080p"


class DownloadUpdate(BaseModel):
    status: Optional[str] = None
    file_path: Optional[str] = None


class DownloadRead(BaseModel):
    id: int
    title_id: int
    source: str
    magnet_link: Optional[str]
    info_hash: Optional[str]
    quality: str
    status: str
    file_path: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
