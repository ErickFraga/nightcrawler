"""
RED tests for the 1337x torrent provider.
Uses the py1337x library (wraps HTML scraping) behind a mockable adapter.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ncrawler.torrent.l337x import L337xProvider, TorrentResult


# Simulated response from py1337x
MOCK_SEARCH_RESULT = {
    "items": [
        {
            "name": "Inception 2010 1080p BluRay",
            "seeders": "2500",
            "leechers": "300",
            "size": "2.2 GB",
            "link": "https://1337x.to/torrent/12345/inception-2010/",
            "info_hash": "CCDDEE112233445566778899AABBCCDDEE112233",
        }
    ],
    "currentPage": 1,
    "pageCount": 1,
    "itemCount": 1,
}

MOCK_TORRENT_INFO = {
    "name": "Inception 2010 1080p BluRay",
    "seeders": "2500",
    "leechers": "300",
    "size": "2.2 GB",
    "info_hash": "CCDDEE112233445566778899AABBCCDDEE112233",
    "magnetLink": "magnet:?xt=urn:btih:CCDDEE112233445566778899AABBCCDDEE112233&dn=Inception+2010",
}

EMPTY_SEARCH_RESULT = {
    "items": [],
    "currentPage": 1,
    "pageCount": 0,
    "itemCount": 0,
}


@pytest.fixture
def provider():
    return L337xProvider()


@pytest.mark.asyncio
async def test_search_returns_torrent_results(provider):
    with patch.object(provider, "_search_raw", new_callable=AsyncMock) as mock_search:
        with patch.object(provider, "_get_torrent_info", new_callable=AsyncMock) as mock_info:
            mock_search.return_value = MOCK_SEARCH_RESULT
            mock_info.return_value = MOCK_TORRENT_INFO

            results = await provider.search("Inception 2010")

    assert len(results) >= 1
    assert isinstance(results[0], TorrentResult)


@pytest.mark.asyncio
async def test_search_extracts_title(provider):
    with patch.object(provider, "_search_raw", new_callable=AsyncMock) as mock_search:
        with patch.object(provider, "_get_torrent_info", new_callable=AsyncMock) as mock_info:
            mock_search.return_value = MOCK_SEARCH_RESULT
            mock_info.return_value = MOCK_TORRENT_INFO

            results = await provider.search("Inception 2010")

    assert "Inception" in results[0].title


@pytest.mark.asyncio
async def test_search_includes_magnet_link(provider):
    with patch.object(provider, "_search_raw", new_callable=AsyncMock) as mock_search:
        with patch.object(provider, "_get_torrent_info", new_callable=AsyncMock) as mock_info:
            mock_search.return_value = MOCK_SEARCH_RESULT
            mock_info.return_value = MOCK_TORRENT_INFO

            results = await provider.search("Inception 2010")

    assert results[0].magnet_link is not None
    assert results[0].magnet_link.startswith("magnet:")


@pytest.mark.asyncio
async def test_search_includes_seeder_count(provider):
    with patch.object(provider, "_search_raw", new_callable=AsyncMock) as mock_search:
        with patch.object(provider, "_get_torrent_info", new_callable=AsyncMock) as mock_info:
            mock_search.return_value = MOCK_SEARCH_RESULT
            mock_info.return_value = MOCK_TORRENT_INFO

            results = await provider.search("Inception 2010")

    assert results[0].seeders == 2500


@pytest.mark.asyncio
async def test_search_returns_empty_on_no_results(provider):
    with patch.object(provider, "_search_raw", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = EMPTY_SEARCH_RESULT
        results = await provider.search("ZZZNonExistentFilmZZZ")

    assert results == []


@pytest.mark.asyncio
async def test_search_handles_scraping_exception_gracefully(provider):
    """If py1337x raises, provider should raise a consistent exception."""
    with patch.object(provider, "_search_raw", new_callable=AsyncMock) as mock_search:
        mock_search.side_effect = Exception("Connection error")
        with pytest.raises(Exception):
            await provider.search("Inception")
