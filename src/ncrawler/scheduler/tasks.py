from __future__ import annotations

import logging

from ncrawler.discovery.release_finder import ReleaseFinder
from ncrawler.rules.engine import TitleCandidate
from ncrawler.torrent.orchestrator import TorrentOrchestrator
from ncrawler.downloader.qbittorrent import QBittorrentClient

logger = logging.getLogger(__name__)


async def run_discovery(
    finder: ReleaseFinder,
    orchestrator: TorrentOrchestrator,
    qb_client: QBittorrentClient,
    db,
    quality: str = "1080p",
    downloads_path: str = "/downloads",
) -> None:
    """
    Main discovery task: find new releases → search torrent → add to qBittorrent.
    Designed to be called by APScheduler on a configured interval.
    """
    candidates: list[TitleCandidate] = []

    try:
        movies = await finder.find_new_movies()
        candidates.extend(movies)
    except Exception:
        logger.exception("Discovery: error fetching new movies")

    try:
        series = await finder.find_new_series()
        candidates.extend(series)
    except Exception:
        logger.exception("Discovery: error fetching new series")

    for candidate in candidates:
        try:
            torrent = await orchestrator.find_best(
                candidate.title,
                year=candidate.year,
                quality=quality,
            )
            if torrent is None:
                logger.info("No torrent found for %r", candidate.title)
                continue

            await qb_client.add_magnet(
                magnet=torrent.magnet_link,
                save_path=downloads_path,
            )
            logger.info("Added %r from %s (%d seeders)", candidate.title, torrent.source, torrent.seeders)

        except Exception:
            logger.exception("Error processing candidate %r", candidate.title)
            continue
