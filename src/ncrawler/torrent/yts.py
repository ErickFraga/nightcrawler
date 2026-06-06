from __future__ import annotations

import urllib.parse
import httpx

from ncrawler.torrent.base import TorrentProvider, TorrentResult

YTS_API = "https://yts.mx/api/v2"
TRACKER_LIST = [
    "udp://open.demonii.com:1337/announce",
    "udp://tracker.openbittorrent.com:80",
    "udp://tracker.coppersurfer.tk:6969",
    "udp://glotorrents.pw:6969/announce",
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://torrent.gresille.org:80/announce",
    "udp://p4p.arenabg.com:1337",
    "udp://tracker.leechers-paradise.org:6969",
]


def _build_magnet(info_hash: str, title: str) -> str:
    trackers = "&".join(f"tr={urllib.parse.quote(t)}" for t in TRACKER_LIST)
    dn = urllib.parse.quote(title)
    return f"magnet:?xt=urn:btih:{info_hash}&dn={dn}&{trackers}"


class YTSProvider(TorrentProvider):
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=30)

    async def search(
        self,
        query: str,
        year: int | None = None,
        quality: str = "1080p",
    ) -> list[TorrentResult]:
        params: dict[str, str | int] = {
            "query_term": query,
            "limit": 20,
            "sort_by": "seeds",
            "order_by": "desc",
        }
        if quality:
            params["quality"] = quality
        if year:
            params["year"] = year

        response = await self._client.get(f"{YTS_API}/list_movies.json", params=params)
        response.raise_for_status()

        data = response.json().get("data", {})
        movies = data.get("movies") or []

        results: list[TorrentResult] = []
        for movie in movies:
            for torrent in movie.get("torrents", []):
                if quality and torrent["quality"] != quality:
                    continue
                results.append(
                    TorrentResult(
                        title=movie["title"],
                        year=movie.get("year"),
                        quality=torrent["quality"],
                        seeders=torrent.get("seeds", 0),
                        leechers=torrent.get("peers", 0),
                        size_bytes=torrent.get("size_bytes", 0),
                        magnet_link=_build_magnet(torrent["hash"], movie["title"]),
                        torrent_url=torrent.get("url"),
                        info_hash=torrent["hash"],
                        source="yts",
                    )
                )

        return results
