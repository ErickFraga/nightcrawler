from __future__ import annotations

import logging
from pathlib import Path

from ncrawler.downloader.qbittorrent import QBittorrentClient, TorrentStatus
from ncrawler.library.organizer import LibraryOrganizer, MediaFile, parse_torrent_name
from ncrawler.db.models.download import DownloadModel

logger = logging.getLogger(__name__)

# qBittorrent states that indicate a torrent has finished downloading
DONE_STATES = {"seeding", "uploading", "stalledUP", "pausedUP", "queuedUP", "forcedUP"}


class CompletionTracker:
    def __init__(
        self,
        qb_client: QBittorrentClient,
        db,
        organizer: LibraryOrganizer,
    ) -> None:
        self._qb = qb_client
        self._db = db
        self._organizer = organizer

    async def check(self) -> None:
        torrents: list[TorrentStatus] = await self._qb.list_torrents()

        for torrent in torrents:
            if torrent.state not in DONE_STATES:
                continue
            try:
                self._process(torrent)
            except Exception:
                logger.exception("Error processing completed torrent %s", torrent.info_hash)

    def _process(self, torrent: TorrentStatus) -> None:
        job: DownloadModel | None = (
            self._db.query(DownloadModel)
            .filter(DownloadModel.info_hash == torrent.info_hash)
            .first()
        )

        if job is None:
            return

        if job.status == "completed":
            return

        title = job.title
        file_path = self._resolve_path(torrent.name, title)

        self._organizer.ensure_dir(file_path)
        job.status = "completed"
        job.file_path = str(file_path)
        title.status = "downloaded"
        self._db.commit()

        logger.info("Completed: %r → %s", title.title, file_path)

    def _resolve_path(self, torrent_name: str, title) -> Path:
        _, year = parse_torrent_name(torrent_name)
        resolved_year = year or title.year or 0

        if title.media_type == "series":
            # Series: use season/episode from torrent name if parseable, else S01E01
            season, episode = _parse_season_episode(torrent_name)
            ext = _parse_extension(torrent_name)
            return self._organizer.episode_path(title.title, season, episode, ext)

        ext = _parse_extension(torrent_name)
        mf = MediaFile(title=title.title, year=resolved_year, ext=ext)
        return self._organizer.movie_path(mf)


def _parse_extension(name: str) -> str:
    for ext in ("mkv", "mp4", "avi", "m4v"):
        if ext in name.lower():
            return ext
    return "mkv"


def _parse_season_episode(name: str) -> tuple[int, int]:
    import re
    match = re.search(r"[Ss](\d{1,2})[Ee](\d{1,2})", name)
    if match:
        return int(match.group(1)), int(match.group(2))
    return 1, 1
