from __future__ import annotations

from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class TorrentResult:
    title: str
    year: int | None
    quality: str
    seeders: int
    leechers: int
    size_bytes: int
    magnet_link: str | None
    torrent_url: str | None
    info_hash: str | None
    source: str


class TorrentProvider(ABC):
    @abstractmethod
    async def search(
        self,
        query: str,
        year: int | None = None,
        quality: str = "1080p",
    ) -> list[TorrentResult]:
        ...
