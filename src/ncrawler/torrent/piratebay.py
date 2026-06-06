from __future__ import annotations

import urllib.parse
import httpx

from ncrawler.torrent.base import TorrentProvider, TorrentResult

APIBAY_BASE = "https://apibay.org"
TRACKER_LIST = [
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://open.demonii.com:1337/announce",
    "udp://tracker.openbittorrent.com:80",
]
# category 207 = HD Movies; 208 = Movies; 200 = Video (all)
DEFAULT_CATEGORY = "207"


def _build_magnet(info_hash: str, name: str) -> str:
    trackers = "&".join(f"tr={urllib.parse.quote(t)}" for t in TRACKER_LIST)
    dn = urllib.parse.quote(name)
    return f"magnet:?xt=urn:btih:{info_hash}&dn={dn}&{trackers}"


def _parse_quality(name: str) -> str:
    name_lower = name.lower()
    if "2160p" in name_lower or "4k" in name_lower:
        return "2160p"
    if "1080p" in name_lower:
        return "1080p"
    if "720p" in name_lower:
        return "720p"
    return "unknown"


class PirateBayProvider(TorrentProvider):
    def __init__(self, category: str = DEFAULT_CATEGORY) -> None:
        self._client = httpx.AsyncClient(timeout=30)
        self._category = category

    async def search(
        self,
        query: str,
        year: int | None = None,
        quality: str = "1080p",
    ) -> list[TorrentResult]:
        params = {"q": query, "cat": self._category}
        response = await self._client.get(f"{APIBAY_BASE}/q.php", params=params)
        response.raise_for_status()

        items = response.json()

        # apibay returns a single-item list with id=0 when nothing found
        if not items or (len(items) == 1 and items[0].get("id") == "0"):
            return []

        results: list[TorrentResult] = []
        for item in items:
            info_hash = item.get("info_hash", "")
            name = item.get("name", "")
            results.append(
                TorrentResult(
                    title=name,
                    year=year,
                    quality=_parse_quality(name),
                    seeders=int(item.get("seeders", 0)),
                    leechers=int(item.get("leechers", 0)),
                    size_bytes=int(item.get("size", 0)),
                    magnet_link=_build_magnet(info_hash, name),
                    torrent_url=None,
                    info_hash=info_hash,
                    source="piratebay",
                )
            )

        return results
