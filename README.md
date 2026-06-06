# Nightcrawler

Automated movie and series release monitoring for [Jellyfin](https://jellyfin.org/). Discovers new releases on TMDB, filters by configurable rules, searches torrent sources, and downloads via qBittorrent — fully autonomous, no manual watchlist required.

---

## Features

- **Rule-based discovery** — define rules by genre, rating, director, actor, studio, or any combination
- **TMDB integration** — polls now-playing, upcoming, and airing-today endpoints weekly
- **Torrent fallback chain** — searches YTS → The Pirate Bay → 1337x, picks the most-seeded result
- **qBittorrent automation** — sends magnets to your existing qBittorrent instance via Web API
- **Jellyfin-compatible library** — organizes downloaded files into `/movies/Title (Year)/` and `/series/Title/Season XX/` structures
- **REST API** — manage rules, inspect titles and downloads, trigger manual discovery runs
- **Optional API key auth** — secure the API with a static key or leave open in dev mode
- **Docker-native** — single `docker compose up` gets everything running

---

## Quick Start

### Prerequisites

- Docker + Docker Compose
- TMDB API key (free at [themoviedb.org](https://www.themoviedb.org/settings/api))
- qBittorrent with Web UI enabled

### 1. Clone and configure

```bash
git clone https://github.com/erickfraga/nightcrawler.git
cd nightcrawler
cp .env.example .env
```

Edit `.env`:

```env
TMDB_API_KEY=your_tmdb_api_key_here
API_KEY=your_secret_api_key_here   # leave empty to disable auth
```

### 2. Set library paths (optional)

By default, the stack mounts `/srv/jellyfin/movies` and `/srv/jellyfin/series`. Override in `.env`:

```env
MOVIES_ROOT=/your/jellyfin/movies
SERIES_ROOT=/your/jellyfin/series
```

### 3. Start the stack

```bash
docker compose up -d
```

Services:
- **nightcrawler API** → `http://localhost:8000`
- **qBittorrent Web UI** → `http://localhost:8080` (default credentials: `admin` / `adminadmin`)

### 4. Create your first rule

```bash
curl -X POST http://localhost:8000/rules \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_secret_api_key_here" \
  -d '{
    "name": "Action movies 7+",
    "genres": ["Action"],
    "min_rating": 7.0,
    "media_type": "movie",
    "quality_profile": "1080p"
  }'
```

### 5. Trigger a discovery run

```bash
curl -X POST http://localhost:8000/discovery/trigger \
  -H "X-API-Key: your_secret_api_key_here"
```

Discovery also runs automatically on the configured interval (default: weekly).

---

## Configuration Reference

All settings are read from environment variables or `.env` file.

| Variable | Default | Description |
|---|---|---|
| `TMDB_API_KEY` | *(required)* | TMDB v3 API key |
| `DATABASE_URL` | `postgresql+asyncpg://ncrawler:ncrawler@postgres:5432/ncrawler` | PostgreSQL connection string |
| `QBITTORRENT_HOST` | `qbittorrent` | qBittorrent hostname (Docker service name) |
| `QBITTORRENT_PORT` | `8080` | qBittorrent Web UI port |
| `QBITTORRENT_USERNAME` | `admin` | qBittorrent Web UI username |
| `QBITTORRENT_PASSWORD` | `adminadmin` | qBittorrent Web UI password |
| `MOVIES_ROOT` | `/library/movies` | Jellyfin movies root (mounted volume) |
| `SERIES_ROOT` | `/library/series` | Jellyfin series root (mounted volume) |
| `DOWNLOADS_PATH` | `/downloads` | Where qBittorrent saves files |
| `DISCOVERY_INTERVAL_HOURS` | `168` | How often to poll TMDB (168 = weekly) |
| `PREFERRED_QUALITY` | `1080p` | Preferred torrent quality (`720p`, `1080p`, `2160p`) |
| `API_KEY` | *(empty)* | Shared secret for `X-API-Key` header. Empty = no auth (dev only) |

---

## API Reference

Interactive docs: `http://localhost:8000/docs`

### Authentication

Set `API_KEY` in your environment to enable auth. All protected endpoints require the header:

```
X-API-Key: your_secret_api_key_here
```

Public endpoints (no key required): `/health`, `/docs`, `/openapi.json`

---

### Rules

Rules define what content to monitor. A release is downloaded if it matches **any** rule.

Within a single rule, all configured criteria must match (AND logic). Empty lists are wildcards.

**Create a rule**

```http
POST /rules
Content-Type: application/json
X-API-Key: <key>

{
  "name": "Sci-Fi 8+",
  "genres": ["Science Fiction"],
  "min_rating": 8.0,
  "directors": [],
  "actors": [],
  "studios": [],
  "media_type": "movie",
  "quality_profile": "1080p"
}
```

`media_type` values: `movie`, `series`, `both`

**List rules**

```http
GET /rules
X-API-Key: <key>
```

**Update a rule**

```http
PATCH /rules/1
Content-Type: application/json
X-API-Key: <key>

{"enabled": false}
```

**Delete a rule**

```http
DELETE /rules/1
X-API-Key: <key>
```

---

### Titles

Titles are movies/series tracked by the system. They are created automatically by discovery, or can be added manually.

**List titles**

```http
GET /titles?status=monitoring&media_type=movie
X-API-Key: <key>
```

Query params:
- `status`: `monitoring`, `found`, `downloading`, `downloaded`
- `media_type`: `movie`, `series`

**Get title**

```http
GET /titles/42
X-API-Key: <key>
```

**Manually add a title**

```http
POST /titles
Content-Type: application/json
X-API-Key: <key>

{
  "title": "Dune: Part Two",
  "year": 2024,
  "media_type": "movie",
  "tmdb_id": 693134
}
```

---

### Downloads

**List downloads**

```http
GET /downloads?status=queued
X-API-Key: <key>
```

**Update a download** (e.g. mark done manually)

```http
PATCH /downloads/7
Content-Type: application/json
X-API-Key: <key>

{"status": "downloaded", "file_path": "/library/movies/Dune Part Two (2024)/Dune Part Two (2024).mkv"}
```

---

### Discovery

**Trigger manual run**

```http
POST /discovery/trigger
X-API-Key: <key>
```

Response `202 Accepted` — run starts in background.

**Check status**

```http
GET /discovery/status
X-API-Key: <key>
```

```json
{
  "status": "ok",
  "last_run": "2024-03-15T02:00:00.000000",
  "next_run": null
}
```

---

### Health

```http
GET /health
```

```json
{
  "status": "ok",
  "version": "0.1.0",
  "components": {
    "database": {"status": "ok"},
    "scheduler": {"status": "ok", "last_run": "2024-03-15T02:00:00.000000"}
  }
}
```

---

## How It Works

```
TMDB (now_playing / upcoming / airing_today)
    ↓  genre mapping + rules filter
TitleCandidate list
    ↓  dedup (tmdb_id → title string)
TorrentOrchestrator
    ├─ YTS JSON API
    ├─ PirateBay apibay.org
    └─ 1337x scraper
    ↓  best result (most seeders)
qBittorrent Web API (add magnet)
    ↓  CompletionTracker (polls torrent states)
LibraryOrganizer (Jellyfin-compatible paths)
```

### Discovery Cycle

1. Fetch TMDB releases → build `TitleCandidate` objects
2. Filter through `RulesEngine` — only candidates matching at least one rule proceed
3. Skip titles already in `found`, `downloading`, or `downloaded` state
4. Search torrent sources via fallback chain (YTS → PirateBay → 1337x)
5. If a torrent is found: create `DownloadModel`, update title status → `found`, send magnet to qBittorrent
6. `CompletionTracker.check()` polls qBittorrent for finished torrents, moves files, marks `downloaded`

### Library Structure

```
/library/movies/
  Dune Part Two (2024)/
    Dune Part Two (2024).mkv

/library/series/
  The Bear/
    Season 01/
      The Bear - S01E01.mkv
```

---

## Development

### Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Running Tests

```bash
# Unit tests only (fast, no network)
python -m pytest tests/unit/ -q

# All tests with coverage
python -m pytest tests/ -q --cov=src/ncrawler --cov-report=term-missing

# Integration tests (requires real TMDB API key)
TMDB_API_KEY=your_key python -m pytest tests/integration/ -v
```

### Lint

```bash
ruff check src/ tests/ --select E,F,W --ignore E501
```

### Database Migrations

```bash
# Apply migrations
alembic upgrade head

# Generate a new migration after changing models
alembic revision --autogenerate -m "add_column_foo"
```

---

## Architecture Notes

- **Framework:** FastAPI with lifespan-managed scheduler (APScheduler `AsyncIOScheduler`)
- **Database:** PostgreSQL via SQLAlchemy (sync sessions in route handlers); SQLite in-memory for tests
- **Torrent search:** Three providers with graceful fallback — no single point of failure
- **Auth:** `X-API-Key` header, read from env at request time (testable without module reload)
- **List fields:** Stored as JSON text columns for SQLite compatibility in tests; accessed via `@property`

---

## License

MIT
