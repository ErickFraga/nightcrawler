# CLAUDE.md — Nightcrawler Agent Continuity Guide

This document gives a successor AI agent everything needed to continue development without losing context.

---

## Project Overview

**Nightcrawler** is an autonomous media release monitoring daemon, similar to Radarr/Sonarr but built from scratch with a rules engine instead of a watchlist. It:

1. Polls TMDB weekly for new movie/series releases
2. Filters candidates through user-defined rules (genre, rating, director, actor, studio)
3. Searches torrent sources (YTS → PirateBay → 1337x fallback chain)
4. Downloads via qBittorrent Web API
5. Organizes files into Jellyfin-compatible directory structure
6. Exposes a FastAPI REST API with optional API key auth

**Package name:** `ncrawler`  
**Python:** ≥ 3.11  
**Current version:** 0.1.0  
**Branch:** `claude/movie-release-monitoring-YO0aG`

---

## Repository Layout

```
nightcrawler/
├── src/ncrawler/
│   ├── __init__.py              # __version__ = "0.1.0"
│   ├── config.py                # Pydantic Settings (reads .env)
│   ├── main.py                  # FastAPI app + APScheduler lifespan
│   ├── api/
│   │   ├── auth.py              # X-API-Key header guard
│   │   ├── dependencies.py      # Sync SQLAlchemy engine + get_db()
│   │   ├── schemas.py           # Pydantic request/response models
│   │   └── routers/
│   │       ├── rules.py         # CRUD /rules
│   │       ├── titles.py        # CRUD /titles + nested /downloads
│   │       ├── downloads.py     # GET/PATCH /downloads
│   │       ├── discovery.py     # POST /discovery/trigger, GET /discovery/status
│   │       └── health.py        # GET /health (public), scheduler state
│   ├── rules/
│   │   ├── schema.py            # MonitoringRule Pydantic model + matches()
│   │   └── engine.py            # RulesEngine + TitleCandidate dataclass
│   ├── discovery/
│   │   ├── tmdb.py              # TMDBClient (async httpx, retry/backoff)
│   │   └── release_finder.py    # ReleaseFinder: TMDB → TitleCandidate list
│   ├── torrent/
│   │   ├── base.py              # TorrentResult dataclass + TorrentProvider ABC
│   │   ├── yts.py               # YTS JSON API provider
│   │   ├── piratebay.py         # PirateBay apibay.org JSON provider
│   │   ├── l337x.py             # 1337x BeautifulSoup4 HTML scraper
│   │   └── orchestrator.py      # Fallback chain + concurrent search_all()
│   ├── downloader/
│   │   └── qbittorrent.py       # QBittorrentClient (login, add_magnet, status)
│   ├── library/
│   │   └── organizer.py         # Jellyfin path builder + file mover
│   ├── scheduler/
│   │   ├── tasks.py             # run_discovery() — full discovery pipeline
│   │   └── completion.py        # CompletionTracker — mark torrents done
│   └── db/
│       ├── base.py              # SQLAlchemy DeclarativeBase
│       └── models/
│           ├── rule.py          # RuleModel (JSON-backed list fields)
│           ├── title.py         # TitleModel (status machine)
│           └── download.py      # DownloadModel (FK → title)
├── tests/
│   ├── conftest.py              # mock_httpx fixture (respx)
│   ├── unit/                    # 21 unit test files, all mocked
│   └── integration/             # 1 file — skipped without real TMDB key
├── alembic/
│   ├── env.py                   # imports Base + models for autogenerate
│   └── versions/
│       └── 95e1b58cd16d_initial_schema.py
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── .github/workflows/ci.yml
```

---

## Development Commands

```bash
# Install (editable + dev deps)
pip install -e ".[dev]"

# Run all tests with coverage
python -m pytest tests/ -q --cov=src/ncrawler --cov-report=term-missing --cov-fail-under=80

# Run only unit tests (fast, no network)
python -m pytest tests/unit/ -q

# Run integration tests (requires TMDB_API_KEY env var)
TMDB_API_KEY=your_key python -m pytest tests/integration/ -v

# Lint
ruff check src/ tests/ --select E,F,W --ignore E501

# Run dev server
TMDB_API_KEY=fake uvicorn ncrawler.main:app --reload

# Apply DB migrations
alembic upgrade head

# Generate new migration after model change
alembic revision --autogenerate -m "description"

# Docker stack
docker compose up --build
```

---

## Key Design Decisions

### TDD Convention
All features follow Red → Green. Write failing tests first, then implement. Tests live in `tests/unit/` (fully mocked) or `tests/integration/` (real external calls, skipped in CI if no secret).

### SQLite in Tests
Unit tests use `sqlite://` with `poolclass=StaticPool` to share a single in-memory connection across the session. Without `StaticPool`, SQLite creates a fresh DB per connection and tables disappear.

```python
engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
```

### JSON-backed List Fields
PostgreSQL ARRAY is ideal but SQLite (used in tests) doesn't support it. All list fields (`genres`, `directors`, `cast`, `studios`) are stored as `Text` with JSON serialization via `@property` in the model. Never set them via the raw `_json` column — always use the property.

```python
# Correct
title.genres = ["Action", "Thriller"]
# Wrong
title.genres_json = '["Action", "Thriller"]'
```

### API Key Auth
`require_api_key()` in `src/ncrawler/api/auth.py` reads `API_KEY` from `os.environ` **at call time** (not at import time). This is intentional — it makes `monkeypatch.setenv("API_KEY", ...)` work in tests without `importlib.reload()`.

- Empty `API_KEY` = dev mode (all requests pass through)
- Set `API_KEY` = enforces header `X-API-Key: <key>` on all non-public endpoints

### APScheduler Async Jobs
`AsyncIOScheduler` runs inside the FastAPI/uvicorn event loop. Jobs **must be async coroutines**. Never call `asyncio.get_event_loop().run_until_complete()` from inside a running loop — it deadlocks. The job registered in `main.py` is `async def _discovery_job()`.

### Title Status Machine
```
monitoring → found → downloading → downloaded
```
- `monitoring`: known but no torrent yet
- `found`: torrent located, magnet sent to qBittorrent
- `downloading`: in-progress (set externally or by completion tracker)
- `downloaded`: complete, file moved to library

`_SKIP_STATUSES = {"found", "downloading", "downloaded"}` — if a title is at any of these, `run_discovery()` will not re-queue it.

### Deduplication in run_discovery()
`_find_existing()` checks `tmdb_id` first (preferred), then falls back to title string match. If found with a skip status, returns early. If found with `monitoring`, re-processes (allows retry).

### Torrent Fallback Chain
`TorrentOrchestrator.find_best()` tries providers in order: YTS → PirateBay → 1337x. Returns the result with the most seeders from the **first non-empty source**. Per-provider exceptions are swallowed. Returns `None` if all sources fail.

---

## Module Reference

### `src/ncrawler/config.py`
`Settings(BaseSettings)` — reads from `.env` file and environment variables.

| Variable | Default | Notes |
|---|---|---|
| `TMDB_API_KEY` | *(required)* | TMDB v3 API key |
| `DATABASE_URL` | `postgresql+asyncpg://...` | For sync usage, driver is swapped to `psycopg2` in dependencies.py |
| `QBITTORRENT_HOST` | `qbittorrent` | Docker service name |
| `QBITTORRENT_PORT` | `8080` | Web UI port |
| `QBITTORRENT_USERNAME` | `admin` | |
| `QBITTORRENT_PASSWORD` | `adminadmin` | |
| `MOVIES_ROOT` | `/library/movies` | Jellyfin movies volume mount |
| `SERIES_ROOT` | `/library/series` | Jellyfin series volume mount |
| `DOWNLOADS_PATH` | `/downloads` | qBittorrent save path |
| `DISCOVERY_INTERVAL_HOURS` | `168` | Weekly = 168h |
| `PREFERRED_QUALITY` | `1080p` | Passed to torrent providers |
| `API_KEY` | *(empty)* | Empty = dev mode, no auth |

### `src/ncrawler/api/dependencies.py`
Lazy initialization of a **sync** SQLAlchemy engine. The `DATABASE_URL` from settings uses `asyncpg` driver (async), which is replaced with `psycopg2` for sync sessions (tests use `sqlite://`).

```python
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### `src/ncrawler/discovery/tmdb.py`
`TMDBClient(api_key, max_retries=3, retry_delay=1.0)`

Retry logic in `_get()`:
- `_RETRYABLE = {429, 500, 502, 503, 504}` → exponential backoff: `retry_delay * 2^attempt`
- `_NO_RETRY = {400, 401, 403, 404, 422}` → raise immediately
- After exhausting retries, re-raises the last `httpx.HTTPStatusError`

Methods:
- `get_now_playing(page)` → `list[TMDBMovie]`
- `get_upcoming(page)` → `list[TMDBMovie]`
- `get_movie_details(tmdb_id)` → `TMDBMovie` (with credits)
- `get_airing_today(page)` → `list[TMDBSeries]`
- `get_series_details(tmdb_id)` → `TMDBSeries` (with external_ids)
- `get_genre_map(media="movie")` → `dict[int, str]`

### `src/ncrawler/discovery/release_finder.py`
`ReleaseFinder(tmdb_client, engine)`

- `find_new_movies()` → fetches `now_playing` + `upcoming`, resolves genre IDs → names, filters via `RulesEngine`, deduplicates by `tmdb_id`
- `find_new_series()` → fetches `airing_today`, filters, deduplicates

Returns `list[TitleCandidate]` — lightweight dataclasses for the rules engine.

### `src/ncrawler/rules/schema.py`
`MonitoringRule.matches(candidate)` returns `True` if ALL configured criteria match:
- Rule must be enabled
- `media_type` matches or rule is `BOTH`
- `candidate.rating >= min_rating`
- Genre intersection non-empty (if `genres` list is non-empty)
- Director intersection non-empty (if `directors` list is non-empty)
- Actor intersection non-empty (if `actors` list is non-empty)
- Studio intersection non-empty (if `studios` list is non-empty)

Empty filter list = wildcard (matches everything for that criterion).

### `src/ncrawler/torrent/yts.py`
Uses YTS official JSON API: `https://yts.mx/api/v2/list_movies.json`

Params: `query_term`, `quality`, `year`, `limit=20`, `sort_by=seeds`

Builds magnet from `info_hash` + hardcoded tracker list.

### `src/ncrawler/torrent/piratebay.py`
Uses unofficial apibay.org: `https://apibay.org/q.php?q=...&cat=207`

Category 207 = HD Movies. Detects empty results by checking `id == "0"` sentinel in response. Builds magnet from `info_hash`.

### `src/ncrawler/torrent/l337x.py`
BeautifulSoup4 scraper. Uses `lxml` parser.

- Search URL: `https://1337x.to/search/{query}/1/`
- CSS selector for results: `table.table-list tbody tr`
- Fetches individual torrent page to extract magnet link
- 0.5s sleep between requests (polite scraping)
- Sets `User-Agent` header to mimic a browser

**Coverage note:** Only ~49% line coverage because `_search_raw()` and `_get_torrent_info()` are patched in tests — actual HTML parsing is never executed in the test suite. This is acceptable; real HTTP calls in unit tests are undesirable.

### `src/ncrawler/downloader/qbittorrent.py`
`QBittorrentClient(host, port, username, password)`

- `login()` → POST `/api/v2/auth/login`, raises `DownloadError` if response is not `"Ok."`
- `add_magnet(magnet, save_path)` → POST `/api/v2/torrents/add`
- `get_status(info_hash)` → `TorrentStatus | None`
- `list_torrents()` → `list[TorrentStatus]`

`TorrentStatus` fields: `info_hash`, `name`, `state`, `progress`, `download_speed`, `save_path`

### `src/ncrawler/library/organizer.py`
`LibraryOrganizer(movies_root: Path, series_root: Path)`

- `movie_path(mf: MediaFile)` → `movies_root/Title (Year)/Title (Year).ext`
- `episode_path(series_title, season, episode, ext)` → `series_root/Title/Season 01/Title - S01E01.ext`
- `parse_torrent_name(raw)` → `(title: str, year: int | None)` — strips quality tags, extracts year
- `_sanitize(name)` — removes `[<>:"/\\|?*]` (Windows-safe filenames)
- `ensure_dir(file_path)` — `mkdir(parents=True, exist_ok=True)`

### `src/ncrawler/scheduler/completion.py`
`CompletionTracker(qb_client, db, organizer)`

Done states from qBittorrent: `{"seeding", "uploading", "stalledUP", "pausedUP", "queuedUP", "forcedUP"}`

- `check()` → calls `qb_client.list_torrents()`, processes each done torrent
- `_process(torrent)` → finds `DownloadModel` by `info_hash`, resolves output path, calls `ensure_dir`, updates `status = "downloaded"`, commits

---

## REST API Reference

All endpoints except `/health`, `/docs`, and `/openapi.json` require `X-API-Key` header when `API_KEY` env var is set.

### Rules

| Method | Path | Description |
|---|---|---|
| `GET` | `/rules` | List all rules |
| `POST` | `/rules` | Create rule (201) |
| `GET` | `/rules/{id}` | Get rule by ID |
| `PATCH` | `/rules/{id}` | Partial update |
| `DELETE` | `/rules/{id}` | Delete (204) |

### Titles

| Method | Path | Description |
|---|---|---|
| `GET` | `/titles` | List titles (filter: `status`, `media_type`) |
| `POST` | `/titles` | Manually add title (201) |
| `GET` | `/titles/{id}` | Get title by ID |
| `POST` | `/titles/{id}/downloads` | Create download record (201) |

### Downloads

| Method | Path | Description |
|---|---|---|
| `GET` | `/downloads` | List downloads (filter: `status`) |
| `PATCH` | `/downloads/{id}` | Update status/file_path |

### Discovery

| Method | Path | Description |
|---|---|---|
| `POST` | `/discovery/trigger` | Start discovery run in background (202) |
| `GET` | `/discovery/status` | Last run time + status |

### Health (public)

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | DB + scheduler status |

---

## Database Models

### `rules` table
| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `name` | String | Unique rule name |
| `enabled` | Boolean | Default True |
| `genres_json` | Text | JSON-encoded list |
| `min_rating` | Float | Default 0.0 |
| `directors_json` | Text | JSON-encoded list |
| `actors_json` | Text | JSON-encoded list |
| `studios_json` | Text | JSON-encoded list |
| `media_type` | String | `movie`, `series`, `both` |
| `quality_profile` | String | e.g. `1080p` |
| `created_at` | DateTime | |
| `updated_at` | DateTime | |

### `titles` table
| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `tmdb_id` | Integer | Unique, nullable, indexed |
| `imdb_id` | String | Nullable |
| `title` | String | |
| `year` | Integer | Nullable |
| `media_type` | String | `movie` or `series` |
| `genres_json` | Text | JSON-encoded list |
| `rating` | Float | |
| `directors_json` | Text | JSON-encoded list |
| `cast_json` | Text | JSON-encoded list |
| `studios_json` | Text | JSON-encoded list |
| `status` | String | `monitoring`/`found`/`downloading`/`downloaded` |
| `created_at` | DateTime | |
| `updated_at` | DateTime | |

### `downloads` table
| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `title_id` | Integer FK | → titles.id |
| `source` | String | `yts`, `piratebay`, `1337x` |
| `magnet_link` | Text | Nullable |
| `info_hash` | String | Nullable, indexed |
| `quality` | String | e.g. `1080p` |
| `status` | String | `queued`/`downloading`/`done` |
| `file_path` | String | Nullable — set by CompletionTracker |
| `created_at` | DateTime | |

---

## Test Conventions

```python
# Unit test — use StaticPool for SQLite in-memory isolation
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

# Integration test — skip if no real API key
pytestmark = pytest.mark.skipif(
    not os.environ.get("TMDB_API_KEY") or os.environ["TMDB_API_KEY"] == "ci-placeholder",
    reason="Requires real TMDB_API_KEY",
)

# Mock httpx — use respx
import respx, httpx
with respx.mock:
    respx.get("https://api.themoviedb.org/3/movie/now_playing").mock(
        return_value=httpx.Response(200, json={...})
    )

# Mock qBittorrent client — use AsyncMock
from unittest.mock import AsyncMock, MagicMock
qb = AsyncMock(spec=QBittorrentClient)
qb.list_torrents.return_value = [...]
```

**Critical:** when mocking `db` for scheduler tests, always reset `first()` to return `None` for new candidates:

```python
def _make_db():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    return db
```

---

## Known Gaps / Backlog

These are areas that exist but need improvement, or features that were scoped out:

### Technical Debt
1. **1337x coverage at ~49%** — `_search_raw()` and `_get_torrent_info()` are stubbed in tests. The actual HTML parsing paths are never exercised. Consider adding a fixture with real HTML snippets.
2. **No OpenAPI security schema** — `require_api_key` works at runtime but isn't reflected in `/openapi.json`. Add `SecurityScheme` to the FastAPI app definition for proper Swagger UI lock icon.
3. **Sync DB in async app** — The app uses a sync SQLAlchemy session (`Session`) inside async route handlers. This blocks the event loop on DB I/O. Should migrate to `AsyncSession` with `async_sessionmaker` for production workloads.
4. **`run_discovery_now()` uses `asyncio.create_task()`** — The DB session passed to the background task may be closed by the time it runs if the route handler exits. Consider passing a factory instead of a session.
5. **No pagination in list endpoints** — `/rules`, `/titles`, `/downloads` return all records with no limit/offset. For large libraries, this will cause memory/timeout issues.

### Missing Features
1. **Series episode tracking** — `CompletionTracker._resolve_path()` has a basic S01E01 parser but it's not well-tested. Series season/episode extraction from torrent names is fragile.
2. **Notifications** — No webhook, email, or push notification when a download completes.
3. **Quality upgrade logic** — If a 720p torrent is downloaded and a 1080p version appears later, there's no mechanism to re-download at higher quality.
4. **Soft deletes** — Deleting a rule via `DELETE /rules/{id}` hard-deletes from the database with no audit trail.
5. **Rate limiting on API** — No per-IP or per-key rate limiting on the REST API.
6. **Retry failed downloads** — Titles stuck in `monitoring` (no torrent found) are retried every weekly run, but titles in `found` (magnet sent, qBittorrent accepted) are never re-checked for actual download progress.
7. **Frontend** — No UI. API-only. Consider adding a minimal React or HTMX dashboard.

---

## CI/CD

GitHub Actions at `.github/workflows/ci.yml`:

- **test** job: Python 3.11 + 3.12 matrix, `pip install -e ".[dev]"`, `pytest --cov-fail-under=80`
  - `TMDB_API_KEY` from `secrets.TMDB_API_KEY`, fallback to `ci-placeholder` (integration tests skip)
- **lint** job: `ruff check src/ tests/ --select E,F,W --ignore E501`

Coverage must stay ≥ 80%. If you add new modules, add corresponding unit tests.

---

## Quick-Start Checklist for a New Agent

1. `git checkout claude/movie-release-monitoring-YO0aG`
2. `pip install -e ".[dev]"`
3. `python -m pytest tests/unit/ -q` — should show ~164 passing, 3 skipped
4. Read this file fully before touching any module
5. Follow TDD: write the failing test first, then implement
6. Run `ruff check src/ tests/ --select E,F,W --ignore E501` before committing
7. `git push -u origin claude/movie-release-monitoring-YO0aG`
