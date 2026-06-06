from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ncrawler.db.base import Base

# Lazy engine — initialised on first import of this module.
# Tests override get_db() via dependency_overrides.
_engine = None
_SessionLocal = None


def _get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        from ncrawler.config import settings
        _engine = create_engine(
            settings.database_url.replace("postgresql+asyncpg", "postgresql"),
            pool_pre_ping=True,
        )
        _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
    return _engine


def get_db() -> Generator[Session, None, None]:
    engine = _get_engine()
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
