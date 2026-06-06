from __future__ import annotations

import asyncio
import urllib.parse
from typing import Any

import httpx
from bs4 import BeautifulSoup

from ncrawler.torrent.base import TorrentProvider, TorrentResult

L337X_BASE = "https://1337x.to"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
TRACKER_LIST = [
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://open.demonii.com:1337/announce",
]


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


class L337xProvider(TorrentProvider):
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True)

    async def _search_raw(self, query: str) -> dict[str, Any]:
        encoded = urllib.parse.quote(query)
        url = f"{L337X_BASE}/search/{encoded}/1/"
        response = await self._client.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        items = []

        for row in soup.select("table.table-list tbody tr"):
            name_td = row.select_one("td.name a:nth-of-type(2)")
            seeds_td = row.select_one("td.seeds")
            leeches_td = row.select_one("td.leeches")
            size_td = row.select_one("td.size")
            link_td = row.select_one("td.name a:nth-of-type(2)")

            if not name_td:
                continue

            items.append({
                "name": name_td.get_text(strip=True),
                "seeders": seeds_td.get_text(strip=True) if seeds_td else "0",
                "leechers": leeches_td.get_text(strip=True) if leeches_td else "0",
                "size": size_td.get_text(strip=True) if size_td else "0",
                "link": L337X_BASE + name_td["href"] if name_td.get("href") else "",
                "info_hash": "",
            })

        return {
            "items": items,
            "currentPage": 1,
            "pageCount": 1,
            "itemCount": len(items),
        }

    async def _get_torrent_info(self, url: str) -> dict[str, Any]:
        response = await self._client.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        magnet = ""
        info_hash = ""

        magnet_tag = soup.select_one("a[href^='magnet:']")
        if magnet_tag:
            magnet = magnet_tag["href"]
            # extract info_hash from magnet
            if "urn:btih:" in magnet:
                info_hash = magnet.split("urn:btih:")[1].split("&")[0]

        return {
            "magnetLink": magnet,
            "info_hash": info_hash,
        }

    async def search(
        self,
        query: str,
        year: int | None = None,
        quality: str = "1080p",
    ) -> list[TorrentResult]:
        raw = await self._search_raw(query)
        items = raw.get("items", [])

        if not items:
            return []

        results: list[TorrentResult] = []
        # Fetch magnet links for top-5 results to avoid overwhelming the site
        for item in items[:5]:
            try:
                if item.get("link"):
                    info = await self._get_torrent_info(item["link"])
                    magnet = info.get("magnetLink") or (
                        _build_magnet(item["info_hash"], item["name"]) if item["info_hash"] else None
                    )
                    info_hash = info.get("info_hash") or item.get("info_hash")
                else:
                    magnet = None
                    info_hash = item.get("info_hash")

                results.append(
                    TorrentResult(
                        title=item["name"],
                        year=year,
                        quality=_parse_quality(item["name"]),
                        seeders=int(item.get("seeders", "0").replace(",", "") or 0),
                        leechers=int(item.get("leechers", "0").replace(",", "") or 0),
                        size_bytes=0,
                        magnet_link=magnet,
                        torrent_url=item.get("link"),
                        info_hash=info_hash,
                        source="1337x",
                    )
                )
                await asyncio.sleep(0.5)  # polite rate limit
            except Exception:
                continue

        return results
