from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ncrawler.db.base import Base


class TitleModel(Base):
    __tablename__ = "titles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tmdb_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    imdb_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    media_type: Mapped[str] = mapped_column(String(20), default="movie")
    genres_json: Mapped[str] = mapped_column(Text, default="[]")
    rating: Mapped[float] = mapped_column(Float, default=0.0)
    directors_json: Mapped[str] = mapped_column(Text, default="[]")
    cast_json: Mapped[str] = mapped_column(Text, default="[]")
    studios_json: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(30), default="monitoring")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    downloads: Mapped[list["DownloadModel"]] = relationship(  # noqa: F821
        "DownloadModel", back_populates="title", cascade="all, delete-orphan"
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
    def cast(self) -> list[str]:
        return json.loads(self.cast_json)

    @cast.setter
    def cast(self, value: list[str]) -> None:
        self.cast_json = json.dumps(value)

    @property
    def studios(self) -> list[str]:
        return json.loads(self.studios_json)

    @studios.setter
    def studios(self, value: list[str]) -> None:
        self.studios_json = json.dumps(value)
