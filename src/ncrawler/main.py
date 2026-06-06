from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from ncrawler.api.routers import rules, titles, downloads, health as health_router, discovery as discovery_router

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def _build_scheduler() -> AsyncIOScheduler:
    from ncrawler.config import settings
    from ncrawler.api.routers.discovery import run_discovery_now
    from ncrawler.api.dependencies import get_db

    async def _discovery_job() -> None:
        db = next(get_db())
        try:
            await run_discovery_now(db)
        finally:
            db.close()

    sched = AsyncIOScheduler()
    sched.add_job(
        _discovery_job,
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
app.include_router(discovery_router.router)
