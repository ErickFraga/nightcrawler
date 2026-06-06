from __future__ import annotations

import os

from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _configured_key() -> str:
    """Read API_KEY at call time so tests can monkeypatch os.environ."""
    return os.environ.get("API_KEY", "")


def require_api_key(api_key: str | None = Security(_api_key_header)) -> str:
    """FastAPI dependency — raises 401 if the header is missing or incorrect."""
    expected = _configured_key()
    if not expected:
        # No key configured → open access (development mode)
        return ""
    if api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Supply X-API-Key header.",
        )
    return api_key
