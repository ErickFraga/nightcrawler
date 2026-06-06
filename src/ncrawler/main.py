from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(
    title="Nightcrawler",
    description="Automated movie & series release monitoring for Jellyfin",
    version="0.1.0",
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
