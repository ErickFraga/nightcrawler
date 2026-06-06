from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ncrawler.db.base import Base


class RuleModel(Base):
    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    genres_json: Mapped[str] = mapped_column(Text, default="[]")
    min_rating: Mapped[float] = mapped_column(Float, default=0.0)
    directors_json: Mapped[str] = mapped_column(Text, default="[]")
    actors_json: Mapped[str] = mapped_column(Text, default="[]")
    studios_json: Mapped[str] = mapped_column(Text, default="[]")
    media_type: Mapped[str] = mapped_column(String(20), default="both")
    quality_profile: Mapped[str] = mapped_column(String(20), default="1080p")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    @property
    def genres(self) -> list[str]:
        return json.loads(self.genres_json)

    @genres.setter
    def genres(self, value: list[str]) -> None:
        self.genres_json = json.dumps(value)

    @property
    def directors(self) -> list[str]:
        return json.loads(self.directors_json)

    @directors.setter
    def directors(self, value: list[str]) -> None:
        self.directors_json = json.dumps(value)

    @property
    def actors(self) -> list[str]:
        return json.loads(self.actors_json)

    @actors.setter
    def actors(self, value: list[str]) -> None:
        self.actors_json = json.dumps(value)

    @property
    def studios(self) -> list[str]:
        return json.loads(self.studios_json)

    @studios.setter
    def studios(self, value: list[str]) -> None:
        self.studios_json = json.dumps(value)
