from __future__ import annotations

import logging

from ncrawler.discovery.release_finder import ReleaseFinder
from ncrawler.rules.engine import TitleCandidate
from ncrawler.torrent.orchestrator import TorrentOrchestrator
from ncrawler.downloader.qbittorrent import QBittorrentClient
from ncrawler.db.models.title import TitleModel
from ncrawler.db.models.download import DownloadModel

logger = logging.getLogger(__name__)

# Statuses that mean we already have (or had) a torrent for this title
_SKIP_STATUSES = {"found", "downloading", "downloaded"}


async def run_discovery(
    finder: ReleaseFinder,
    orchestrator: TorrentOrchestrator,
    qb_client: QBittorrentClient,
    db,
    quality: str = "1080p",
    downloads_path: str = "/downloads",
) -> None:
    """
    Weekly discovery task:
    1. Fetch candidates from TMDB filtered by rules
    2. Skip titles already tracked at or beyond 'found' state
    3. Search torrent sources (fallback chain)
    4. Persist TitleModel + DownloadModel, add magnet to qBittorrent
    """
    candidates: list[TitleCandidate] = []

    try:
        candidates.extend(await finder.find_new_movies())
    except Exception:
        logger.exception("Discovery: error fetching movies")

    try:
        candidates.extend(await finder.find_new_series())
    except Exception:
        logger.exception("Discovery: error fetching series")

    for candidate in candidates:
        try:
            await _process_candidate(candidate, orchestrator, qb_client, db, quality, downloads_path)
        except Exception:
            logger.exception("Error processing candidate %r", candidate.title)


async def _process_candidate(
    candidate: TitleCandidate,
    orchestrator: TorrentOrchestrator,
    qb_client: QBittorrentClient,
    db,
    quality: str,
    downloads_path: str,
) -> None:
    # ── deduplication ────────────────────────────────────────────────────────
    existing = _find_existing(db, candidate)
    if existing is not None:
        if existing.status in _SKIP_STATUSES:
            logger.debug("Skipping %r — already %s", candidate.title, existing.status)
            return
        title = existing
    else:
        title = _create_title(db, candidate)

    # ── torrent search ───────────────────────────────────────────────────────
    torrent = await orchestrator.find_best(candidate.title, year=candidate.year, quality=quality)

    if torrent is None:
        logger.info("No torrent found for %r", candidate.title)
        db.commit()
        return

    # ── persist download job ─────────────────────────────────────────────────
    download = DownloadModel(
        title_id=title.id,
        source=torrent.source,
        magnet_link=torrent.magnet_link,
        info_hash=torrent.info_hash,
        quality=quality,
        status="queued",
    )
    db.add(download)
    title.status = "found"
    db.commit()

    # ── send to qBittorrent ───────────────────────────────────────────────────
    await qb_client.add_magnet(magnet=torrent.magnet_link, save_path=downloads_path)
    logger.info("Added %r (%s, %d seeders)", candidate.title, torrent.source, torrent.seeders)


def _find_existing(db, candidate: TitleCandidate) -> TitleModel | None:
    if candidate.tmdb_id:
        return db.query(TitleModel).filter(TitleModel.tmdb_id == candidate.tmdb_id).first()
    return db.query(TitleModel).filter(TitleModel.title == candidate.title).first()


def _create_title(db, candidate: TitleCandidate) -> TitleModel:
    title = TitleModel(
        tmdb_id=candidate.tmdb_id,
        imdb_id=candidate.imdb_id,
        title=candidate.title,
        year=candidate.year,
        media_type=candidate.media_type.value,
        rating=candidate.rating,
        status="monitoring",
    )
    title.genres = candidate.genres
    title.directors = candidate.directors
    title.cast = candidate.actors
    title.studios = candidate.studios
    db.add(title)
    db.flush()  # populate title.id before use
    return title
