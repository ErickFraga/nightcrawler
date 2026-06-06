from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from ncrawler.api.routers import rules, titles, downloads, health as health_router

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def _build_scheduler() -> AsyncIOScheduler:
    from ncrawler.config import settings
    from ncrawler.discovery.tmdb import TMDBClient
    from ncrawler.discovery.release_finder import ReleaseFinder
    from ncrawler.downloader.qbittorrent import QBittorrentClient
    from ncrawler.library.organizer import LibraryOrganizer
    from ncrawler.rules.engine import RulesEngine
    from ncrawler.torrent.orchestrator import TorrentOrchestrator
    from ncrawler.scheduler.tasks import run_discovery
    from ncrawler.scheduler.completion import CompletionTracker
    from ncrawler.api.routers.health import record_scheduler_run
    from pathlib import Path
    import asyncio

    # Infrastructure
    tmdb = TMDBClient(api_key=settings.tmdb_api_key)
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
    orchestrator = TorrentOrchestrator()

    # Load rules from DB at startup
    from ncrawler.api.dependencies import get_db
    from ncrawler.db.models.rule import RuleModel
    from ncrawler.rules.schema import MonitoringRule, MediaType

    def _load_rules():
        db = next(get_db())
        rows = db.query(RuleModel).filter(RuleModel.enabled == True).all()
        return [
            MonitoringRule(
                id=r.id,
                name=r.name,
                enabled=r.enabled,
                genres=r.genres,
                min_rating=r.min_rating,
                directors=r.directors,
                actors=r.actors,
                studios=r.studios,
                media_type=MediaType(r.media_type),
                quality_profile=r.quality_profile,
            )
            for r in rows
        ]

    def _run_discovery_sync():
        rules_list = _load_rules()
        engine = RulesEngine(rules=rules_list)
        finder = ReleaseFinder(tmdb_client=tmdb, engine=engine)
        db = next(get_db())
        tracker = CompletionTracker(qb_client=qb, db=db, organizer=organizer)

        async def _task():
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

        asyncio.get_event_loop().run_until_complete(_task())

    sched = AsyncIOScheduler()
    sched.add_job(
        _run_discovery_sync,
        "interval",
        hours=settings.discovery_interval_hours,
        id="discovery",
        replace_existing=True,
    )
    return sched


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scheduler
    try:
        _scheduler = _build_scheduler()
        _scheduler.start()
        logger.info("Scheduler started")
    except Exception:
        logger.exception("Scheduler failed to start — running without it")
        _scheduler = None
    yield
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


app = FastAPI(
    title="Nightcrawler",
    description="Automated movie & series release monitoring for Jellyfin",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(rules.router)
app.include_router(titles.router)
app.include_router(downloads.router)
app.include_router(health_router.router)
