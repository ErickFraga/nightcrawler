from __future__ import annotations

from dataclasses import dataclass

import httpx


class DownloadError(Exception):
    pass


@dataclass
class TorrentStatus:
    info_hash: str
    name: str
    state: str
    progress: float
    download_speed: int
    save_path: str


class QBittorrentClient:
    def __init__(self, host: str, port: int, username: str, password: str) -> None:
        self._base = f"http://{host}:{port}/api/v2"
        self._username = username
        self._password = password
        self._client = httpx.AsyncClient(timeout=30)

    async def login(self) -> None:
        response = await self._client.post(
            f"{self._base}/auth/login",
            data={"username": self._username, "password": self._password},
        )
        response.raise_for_status()
        if response.text.strip() != "Ok.":
            raise DownloadError(f"qBittorrent authentication failed: {response.text!r}")

    async def add_magnet(self, magnet: str, save_path: str) -> bool:
        await self.login()
        response = await self._client.post(
            f"{self._base}/torrents/add",
            data={"urls": magnet, "savePath": save_path},
        )
        if response.status_code >= 400:
            raise DownloadError(f"Failed to add magnet: HTTP {response.status_code}")
        return True

    async def get_status(self, info_hash: str) -> TorrentStatus | None:
        await self.login()
        response = await self._client.get(
            f"{self._base}/torrents/info",
            params={"hashes": info_hash},
        )
        response.raise_for_status()
        torrents = response.json()
        if not torrents:
            return None
        t = torrents[0]
        return TorrentStatus(
            info_hash=t["hash"],
            name=t["name"],
            state=t["state"],
            progress=t["progress"],
            download_speed=t.get("dlspeed", 0),
            save_path=t.get("save_path", ""),
        )

    async def list_torrents(self) -> list[TorrentStatus]:
        await self.login()
        response = await self._client.get(f"{self._base}/torrents/info")
        response.raise_for_status()
        return [
            TorrentStatus(
                info_hash=t["hash"],
                name=t["name"],
                state=t["state"],
                progress=t["progress"],
                download_speed=t.get("dlspeed", 0),
                save_path=t.get("save_path", ""),
            )
            for t in response.json()
        ]
