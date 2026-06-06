from __future__ import annotations

import asyncio

from ncrawler.torrent.base import TorrentProvider, TorrentResult
from ncrawler.torrent.yts import YTSProvider
from ncrawler.torrent.piratebay import PirateBayProvider
from ncrawler.torrent.l337x import L337xProvider


class TorrentOrchestrator:
    def __init__(self) -> None:
        self._yts = YTSProvider()
        self._tpb = PirateBayProvider()
        self._l337x = L337xProvider()

    async def find_best(
        self,
        query: str,
        year: int | None = None,
        quality: str = "1080p",
    ) -> TorrentResult | None:
        """
        Fallback chain: YTS → PirateBay → 1337x.
        Returns the result with the most seeders from the first non-empty source.
        """
        for provider in (self._yts, self._tpb, self._l337x):
            try:
                results = await provider.search(query, year=year, quality=quality)
                if results:
                    return max(results, key=lambda r: r.seeders)
            except Exception:
                continue
        return None

    async def search_all(
        self,
        query: str,
        year: int | None = None,
        quality: str = "1080p",
    ) -> list[TorrentResult]:
        """Query all providers concurrently; ignore individual failures."""
        tasks = [
            self._yts.search(query, year=year, quality=quality),
            self._tpb.search(query, year=year, quality=quality),
            self._l337x.search(query, year=year, quality=quality),
        ]
        gathered = await asyncio.gather(*tasks, return_exceptions=True)
        results: list[TorrentResult] = []
        for item in gathered:
            if isinstance(item, list):
                results.extend(item)
        return results
