from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


# Characters that are illegal in filenames across Windows/Linux/macOS
_ILLEGAL_CHARS = re.compile(r'[<>:"/\\|?*]')
# Matches the year pattern in a torrent name (e.g. "Film.2010.1080p" or "Film 2010 BluRay")
_YEAR_RE = re.compile(r"\b(19[0-9]{2}|20[0-9]{2})\b")


def _sanitize(name: str) -> str:
    return _ILLEGAL_CHARS.sub("", name).strip()


def parse_torrent_name(raw_name: str) -> tuple[str, int | None]:
    """Extract (title, year) from a torrent name like 'Film.Name.2010.1080p.BluRay'."""
    # Normalise dots/underscores to spaces
    normalised = re.sub(r"[._]", " ", raw_name)

    match = _YEAR_RE.search(normalised)
    year: int | None = int(match.group()) if match else None

    if match:
        title = normalised[: match.start()].strip()
    else:
        # Strip common release tags
        title = re.split(r"\b(bluray|bdrip|webrip|web-dl|hdtv|1080p|720p|2160p|x264|x265|hevc)\b",
                         normalised, flags=re.IGNORECASE)[0].strip()

    return title, year


@dataclass
class MediaFile:
    title: str
    year: int
    ext: str


class LibraryOrganizer:
    def __init__(self, movies_root: Path, series_root: Path) -> None:
        self.movies_root = Path(movies_root)
        self.series_root = Path(series_root)

    def movie_path(self, mf: MediaFile) -> Path:
        folder_name = _sanitize(f"{mf.title} ({mf.year})")
        file_name = f"{folder_name}.{mf.ext}"
        return self.movies_root / folder_name / file_name

    def episode_path(
        self,
        series_title: str,
        season: int,
        episode: int,
        ext: str,
    ) -> Path:
        safe_title = _sanitize(series_title)
        season_dir = f"Season {season:02d}"
        file_name = f"{safe_title} - S{season:02d}E{episode:02d}.{ext}"
        return self.series_root / safe_title / season_dir / file_name

    def ensure_dir(self, file_path: Path) -> None:
        file_path.parent.mkdir(parents=True, exist_ok=True)
