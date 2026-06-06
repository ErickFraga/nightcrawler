from __future__ import annotations

from fastapi import FastAPI

from ncrawler.api.routers import rules, titles, downloads

app = FastAPI(
    title="Nightcrawler",
    description="Automated movie & series release monitoring for Jellyfin",
    version="0.1.0",
)

app.include_router(rules.router)
app.include_router(titles.router)
app.include_router(downloads.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
