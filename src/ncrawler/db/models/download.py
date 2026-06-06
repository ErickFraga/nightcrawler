from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ncrawler.db.base import Base


class DownloadModel(Base):
    __tablename__ = "downloads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title_id: Mapped[int] = mapped_column(Integer, ForeignKey("titles.id"), nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    magnet_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    info_hash: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    quality: Mapped[str] = mapped_column(String(20), default="1080p")
    status: Mapped[str] = mapped_column(String(30), default="queued")
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    title: Mapped["TitleModel"] = relationship(  # noqa: F821
        "TitleModel", back_populates="downloads"
    )
