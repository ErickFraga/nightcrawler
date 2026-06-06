from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ncrawler.api.dependencies import get_db
from ncrawler.api.routers.health import _scheduler_state, record_scheduler_run

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/discovery", tags=["discovery"])


class TriggerResponse(BaseModel):
    status: str
    message: str


class DiscoveryStatus(BaseModel):
    status: str
    last_run: Optional[str]
    next_run: Optional[str]


async def run_discovery_now(db: Session) -> None:
    """Build all infrastructure and run a full discovery + completion cycle."""
    from ncrawler.config import settings
    from ncrawler.discovery.tmdb import TMDBClient
    from ncrawler.discovery.release_finder import ReleaseFinder
    from ncrawler.downloader.qbittorrent import QBittorrentClient
    from ncrawler.library.organizer import LibraryOrganizer
    from ncrawler.db.models.rule import RuleModel
    from ncrawler.rules.engine import RulesEngine
    from ncrawler.rules.schema import MonitoringRule, MediaType
    from ncrawler.torrent.orchestrator import TorrentOrchestrator
    from ncrawler.scheduler.tasks import run_discovery
    from ncrawler.scheduler.completion import CompletionTracker
    from pathlib import Path

    rows = db.query(RuleModel).filter(RuleModel.enabled == True).all()  # noqa: E712
    rules = [
        MonitoringRule(
            id=r.id, name=r.name, enabled=r.enabled,
            genres=r.genres, min_rating=r.min_rating,
            directors=r.directors, actors=r.actors, studios=r.studios,
            media_type=MediaType(r.media_type),
            quality_profile=r.quality_profile,
        )
        for r in rows
    ]

    tmdb = TMDBClient(api_key=settings.tmdb_api_key)
    engine = RulesEngine(rules=rules)
    finder = ReleaseFinder(tmdb_client=tmdb, engine=engine)
    orchestrator = TorrentOrchestrator()
    qb = QBittorrentClient(
        host=settings.qbittorrent_host,
        port=settings.qbittorrent_port,
        username=settings.qbittorrent_username,
        password=settings.qbittorrent_password,
    )
    organizer = LibraryOrganizer(
        movies_root=Path(settings.movies_root),
        series_root=Path(settings.series_root),
    )
    tracker = CompletionTracker(qb_client=qb, db=db, organizer=organizer)

    await run_discovery(
        finder=finder,
        orchestrator=orchestrator,
        qb_client=qb,
        db=db,
        quality=settings.preferred_quality,
        downloads_path=settings.downloads_path,
    )
    await tracker.check()
    record_scheduler_run("ok")


@router.post("/trigger", response_model=TriggerResponse, status_code=202)
async def trigger_discovery(db: Session = Depends(get_db)) -> TriggerResponse:
    asyncio.create_task(run_discovery_now(db))
    return TriggerResponse(
        status="accepted",
        message="Discovery run started in background",
    )


@router.get("/status", response_model=DiscoveryStatus)
def discovery_status() -> DiscoveryStatus:
    return DiscoveryStatus(
        status=_scheduler_state["status"],
        last_run=_scheduler_state["last_run"],
        next_run=None,
    )
