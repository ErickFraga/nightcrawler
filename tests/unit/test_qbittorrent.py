"""
RED tests for the qBittorrent Web API client.
All HTTP calls are mocked with respx.
"""
import pytest
import httpx
import respx

from ncrawler.downloader.qbittorrent import QBittorrentClient, TorrentStatus, DownloadError


QB_BASE = "http://localhost:8080"


@pytest.fixture
def client():
    return QBittorrentClient(
        host="localhost",
        port=8080,
        username="admin",
        password="adminadmin",
    )


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_succeeds(client):
    with respx.mock:
        respx.post(f"{QB_BASE}/api/v2/auth/login").mock(
            return_value=httpx.Response(200, text="Ok.")
        )
        # login should not raise
        await client.login()


@pytest.mark.asyncio
async def test_login_raises_on_bad_credentials(client):
    with respx.mock:
        respx.post(f"{QB_BASE}/api/v2/auth/login").mock(
            return_value=httpx.Response(200, text="Fails.")
        )
        with pytest.raises(DownloadError, match="authentication"):
            await client.login()


# ---------------------------------------------------------------------------
# Add torrent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_add_magnet_link_returns_true_on_success(client):
    with respx.mock:
        respx.post(f"{QB_BASE}/api/v2/auth/login").mock(
            return_value=httpx.Response(200, text="Ok.")
        )
        respx.post(f"{QB_BASE}/api/v2/torrents/add").mock(
            return_value=httpx.Response(200, text="Ok.")
        )
        result = await client.add_magnet(
            magnet="magnet:?xt=urn:btih:ABC123&dn=TestFilm",
            save_path="/downloads/movies",
        )
    assert result is True


@pytest.mark.asyncio
async def test_add_magnet_raises_on_http_error(client):
    with respx.mock:
        respx.post(f"{QB_BASE}/api/v2/auth/login").mock(
            return_value=httpx.Response(200, text="Ok.")
        )
        respx.post(f"{QB_BASE}/api/v2/torrents/add").mock(
            return_value=httpx.Response(500)
        )
        with pytest.raises(DownloadError):
            await client.add_magnet(
                magnet="magnet:?xt=urn:btih:ABC123&dn=TestFilm",
                save_path="/downloads/movies",
            )


@pytest.mark.asyncio
async def test_add_magnet_sends_save_path(client):
    with respx.mock as m:
        m.post(f"{QB_BASE}/api/v2/auth/login").mock(
            return_value=httpx.Response(200, text="Ok.")
        )
        m.post(f"{QB_BASE}/api/v2/torrents/add").mock(
            return_value=httpx.Response(200, text="Ok.")
        )
        await client.add_magnet(
            magnet="magnet:?xt=urn:btih:ABC123",
            save_path="/downloads/movies",
        )
        add_request = m.calls[-1].request
        assert b"savePath" in add_request.content or b"save_path" in add_request.content


# ---------------------------------------------------------------------------
# Get torrent status
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_status_returns_torrent_info(client):
    torrent_list = [
        {
            "hash": "abc123",
            "name": "TestFilm",
            "state": "downloading",
            "progress": 0.42,
            "dlspeed": 1024000,
            "save_path": "/downloads/movies",
        }
    ]
    with respx.mock:
        respx.post(f"{QB_BASE}/api/v2/auth/login").mock(
            return_value=httpx.Response(200, text="Ok.")
        )
        respx.get(f"{QB_BASE}/api/v2/torrents/info").mock(
            return_value=httpx.Response(200, json=torrent_list)
        )
        status = await client.get_status("abc123")

    assert isinstance(status, TorrentStatus)
    assert status.info_hash == "abc123"
    assert status.progress == pytest.approx(0.42)
    assert status.state == "downloading"


@pytest.mark.asyncio
async def test_get_status_returns_none_when_not_found(client):
    with respx.mock:
        respx.post(f"{QB_BASE}/api/v2/auth/login").mock(
            return_value=httpx.Response(200, text="Ok.")
        )
        respx.get(f"{QB_BASE}/api/v2/torrents/info").mock(
            return_value=httpx.Response(200, json=[])
        )
        status = await client.get_status("nonexistent_hash")

    assert status is None


# ---------------------------------------------------------------------------
# List all torrents
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_torrents_returns_list(client):
    torrent_list = [
        {"hash": "aaa", "name": "Film A", "state": "seeding", "progress": 1.0, "dlspeed": 0, "save_path": "/d"},
        {"hash": "bbb", "name": "Film B", "state": "downloading", "progress": 0.5, "dlspeed": 512000, "save_path": "/d"},
    ]
    with respx.mock:
        respx.post(f"{QB_BASE}/api/v2/auth/login").mock(
            return_value=httpx.Response(200, text="Ok.")
        )
        respx.get(f"{QB_BASE}/api/v2/torrents/info").mock(
            return_value=httpx.Response(200, json=torrent_list)
        )
        torrents = await client.list_torrents()

    assert len(torrents) == 2
    assert all(isinstance(t, TorrentStatus) for t in torrents)
