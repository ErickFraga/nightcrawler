from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from ncrawler import __version__

router = APIRouter(tags=["health"])

# Mutable state updated by the scheduler on each run
_scheduler_state: dict = {
    "status": "not_started",
    "last_run": None,
}


def record_scheduler_run(status: str = "ok") -> None:
    _scheduler_state["status"] = status
    _scheduler_state["last_run"] = datetime.utcnow().isoformat()


def check_db() -> bool:
    """Return True if the database is reachable. Swallowed on import errors."""
    try:
        from ncrawler.api.dependencies import get_db
        db = next(get_db())
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        return True
    except Exception:
        return False


class ComponentStatus(BaseModel):
    status: str
    detail: Optional[str] = None
    last_run: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    components: dict[str, ComponentStatus]


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    db_ok = check_db()
    db_component = ComponentStatus(status="ok" if db_ok else "unreachable")

    sched_component = ComponentStatus(
        status=_scheduler_state["status"],
        last_run=_scheduler_state["last_run"],
    )

    overall = "ok" if db_ok else "degraded"

    return HealthResponse(
        status=overall,
        version=__version__,
        components={
            "database": db_component,
            "scheduler": sched_component,
        },
    )
