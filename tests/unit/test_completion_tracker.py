"""
RED tests for the download completion tracker.
Polls qBittorrent for finished torrents, organizes files, updates DB status.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from ncrawler.downloader.qbittorrent import TorrentStatus
from ncrawler.scheduler.completion import CompletionTracker


def _make_qb_status(info_hash: str, state: str, progress: float = 1.0, name: str = "Inception.2010.1080p") -> TorrentStatus:
    return TorrentStatus(
        info_hash=info_hash,
        name=name,
        state=state,
        progress=progress,
        download_speed=0,
        save_path="/downloads",
    )


# ---------------------------------------------------------------------------
# CompletionTracker.check()
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_calls_qbittorrent_list(tmp_path):
    qb = MagicMock()
    qb.list_torrents = AsyncMock(return_value=[])
    db = MagicMock()
    organizer = MagicMock()

    tracker = CompletionTracker(qb_client=qb, db=db, organizer=organizer)
    await tracker.check()

    qb.list_torrents.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_ignores_downloading_torrents(tmp_path):
    downloading = _make_qb_status("HASH1", state="downloading", progress=0.5)

    qb = MagicMock()
    qb.list_torrents = AsyncMock(return_value=[downloading])
    db = MagicMock()
    db.query = MagicMock(return_value=MagicMock(filter=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))))
    organizer = MagicMock()

    tracker = CompletionTracker(qb_client=qb, db=db, organizer=organizer)
    await tracker.check()

    organizer.movie_path.assert_not_called()
    organizer.episode_path.assert_not_called()


@pytest.mark.asyncio
async def test_check_processes_seeding_torrent(tmp_path):
    seeding = _make_qb_status("HASH1", state="seeding", progress=1.0, name="Inception.2010.1080p.BluRay")

    download_job = MagicMock()
    download_job.info_hash = "HASH1"
    download_job.status = "downloading"
    download_job.title = MagicMock()
    download_job.title.title = "Inception"
    download_job.title.year = 2010
    download_job.title.media_type = "movie"

    db = MagicMock()
    query_chain = MagicMock()
    query_chain.first.return_value = download_job
    db.query.return_value.filter.return_value = query_chain

    organizer = MagicMock()
    organizer.movie_path.return_value = tmp_path / "movies" / "Inception (2010)" / "Inception (2010).mkv"
    organizer.ensure_dir = MagicMock()

    qb = MagicMock()
    qb.list_torrents = AsyncMock(return_value=[seeding])

    tracker = CompletionTracker(qb_client=qb, db=db, organizer=organizer)
    await tracker.check()

    # Should update download job status
    assert download_job.status == "completed"
    db.commit.assert_called()


@pytest.mark.asyncio
async def test_check_skips_torrent_not_in_db():
    seeding = _make_qb_status("UNKNOWNHASH", state="seeding")

    db = MagicMock()
    query_chain = MagicMock()
    query_chain.first.return_value = None  # not found in DB
    db.query.return_value.filter.return_value = query_chain

    organizer = MagicMock()
    qb = MagicMock()
    qb.list_torrents = AsyncMock(return_value=[seeding])

    tracker = CompletionTracker(qb_client=qb, db=db, organizer=organizer)
    await tracker.check()

    organizer.movie_path.assert_not_called()


@pytest.mark.asyncio
async def test_check_skips_already_completed_jobs():
    seeding = _make_qb_status("HASH1", state="seeding")

    download_job = MagicMock()
    download_job.info_hash = "HASH1"
    download_job.status = "completed"  # already done

    db = MagicMock()
    query_chain = MagicMock()
    query_chain.first.return_value = download_job
    db.query.return_value.filter.return_value = query_chain

    organizer = MagicMock()
    qb = MagicMock()
    qb.list_torrents = AsyncMock(return_value=[seeding])

    tracker = CompletionTracker(qb_client=qb, db=db, organizer=organizer)
    await tracker.check()

    organizer.movie_path.assert_not_called()


@pytest.mark.asyncio
async def test_check_updates_title_status_to_downloaded():
    seeding = _make_qb_status("HASH1", state="seeding", name="Inception.2010.1080p")

    title = MagicMock()
    title.title = "Inception"
    title.year = 2010
    title.media_type = "movie"
    title.status = "downloading"

    download_job = MagicMock()
    download_job.info_hash = "HASH1"
    download_job.status = "downloading"
    download_job.title = title

    db = MagicMock()
    query_chain = MagicMock()
    query_chain.first.return_value = download_job
    db.query.return_value.filter.return_value = query_chain

    organizer = MagicMock()
    organizer.movie_path.return_value = Path("/library/movies/Inception (2010)/Inception (2010).mkv")
    organizer.ensure_dir = MagicMock()

    qb = MagicMock()
    qb.list_torrents = AsyncMock(return_value=[seeding])

    tracker = CompletionTracker(qb_client=qb, db=db, organizer=organizer)
    await tracker.check()

    assert title.status == "downloaded"


@pytest.mark.asyncio
async def test_check_continues_after_per_torrent_error():
    seeding_a = _make_qb_status("HASH_A", state="seeding", name="Film A 2020 1080p")
    seeding_b = _make_qb_status("HASH_B", state="seeding", name="Film B 2021 1080p")

    title_b = MagicMock()
    title_b.title = "Film B"
    title_b.year = 2021
    title_b.media_type = "movie"
    title_b.status = "downloading"

    job_a = MagicMock()
    job_a.info_hash = "HASH_A"
    job_a.status = "downloading"
    job_a.title = MagicMock(side_effect=Exception("DB error"))  # HASH_A causes error

    job_b = MagicMock()
    job_b.info_hash = "HASH_B"
    job_b.status = "downloading"
    job_b.title = title_b

    def side_effect_query(*args):
        mock = MagicMock()
        mock.filter.return_value.first.side_effect = [job_a, job_b]
        return mock

    db = MagicMock()
    db.query.return_value.filter.return_value.first.side_effect = [job_a, job_b]

    organizer = MagicMock()
    organizer.movie_path.return_value = Path("/library/movies/Film B (2021)/Film B (2021).mkv")
    organizer.ensure_dir = MagicMock()

    qb = MagicMock()
    qb.list_torrents = AsyncMock(return_value=[seeding_a, seeding_b])

    tracker = CompletionTracker(qb_client=qb, db=db, organizer=organizer)
    # Should not raise even if HASH_A processing fails
    await tracker.check()
