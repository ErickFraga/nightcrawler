"""
RED tests for the Jellyfin library organizer.
Generates correct directory and file names per Jellyfin naming conventions.
"""
import pytest
from pathlib import Path

from ncrawler.library.organizer import LibraryOrganizer, MediaFile


@pytest.fixture
def organizer(tmp_path):
    return LibraryOrganizer(
        movies_root=tmp_path / "movies",
        series_root=tmp_path / "series",
    )


# ---------------------------------------------------------------------------
# Movie path generation
# ---------------------------------------------------------------------------

def test_movie_path_follows_jellyfin_convention(organizer, tmp_path):
    """Expected: /movies/Inception (2010)/Inception (2010).mkv"""
    mf = MediaFile(title="Inception", year=2010, ext="mkv")
    path = organizer.movie_path(mf)

    assert path == tmp_path / "movies" / "Inception (2010)" / "Inception (2010).mkv"


def test_movie_path_uses_correct_extension(organizer, tmp_path):
    mf = MediaFile(title="Dune", year=2021, ext="mp4")
    path = organizer.movie_path(mf)

    assert path.suffix == ".mp4"


def test_movie_path_sanitizes_special_characters(organizer, tmp_path):
    """Characters like : / \\ ? * are invalid in filenames."""
    mf = MediaFile(title="Spider-Man: No Way Home", year=2021, ext="mkv")
    path = organizer.movie_path(mf)

    # Colon should be replaced or removed
    assert ":" not in path.name
    assert "Spider-Man" in path.name or "Spider Man" in path.name


def test_movie_path_handles_ampersand_in_title(organizer, tmp_path):
    mf = MediaFile(title="Romeo & Juliet", year=1968, ext="mkv")
    path = organizer.movie_path(mf)

    # Ampersand is valid in most filesystems — should be preserved
    assert path.parent.name == "Romeo & Juliet (1968)"


def test_movie_path_handles_unicode_title(organizer, tmp_path):
    mf = MediaFile(title="Amélie", year=2001, ext="mkv")
    path = organizer.movie_path(mf)

    assert "Amélie" in path.name or "Amelie" in path.name


# ---------------------------------------------------------------------------
# Series path generation
# ---------------------------------------------------------------------------

def test_series_episode_path_follows_jellyfin_convention(organizer, tmp_path):
    """Expected: /series/Breaking Bad/Season 01/Breaking Bad - S01E05.mkv"""
    path = organizer.episode_path(
        series_title="Breaking Bad",
        season=1,
        episode=5,
        ext="mkv",
    )

    assert path == (
        tmp_path / "series" / "Breaking Bad" / "Season 01" / "Breaking Bad - S01E05.mkv"
    )


def test_series_episode_path_pads_season_and_episode(organizer, tmp_path):
    path = organizer.episode_path(
        series_title="The Bear",
        season=3,
        episode=12,
        ext="mkv",
    )

    assert "S03E12" in path.name


def test_series_episode_path_handles_double_digit_season(organizer, tmp_path):
    path = organizer.episode_path(
        series_title="Grey's Anatomy",
        season=20,
        episode=1,
        ext="mkv",
    )

    assert "Season 20" in str(path)
    assert "S20E01" in path.name


def test_series_path_sanitizes_title(organizer, tmp_path):
    path = organizer.episode_path(
        series_title="Grey's Anatomy",
        season=1,
        episode=1,
        ext="mkv",
    )

    # Apostrophe is safe on most filesystems
    assert "Grey" in str(path)


# ---------------------------------------------------------------------------
# Directory creation
# ---------------------------------------------------------------------------

def test_ensure_movie_dir_creates_directory(organizer, tmp_path):
    mf = MediaFile(title="Dune", year=2021, ext="mkv")
    organizer.ensure_dir(organizer.movie_path(mf))

    assert (tmp_path / "movies" / "Dune (2021)").is_dir()


def test_ensure_episode_dir_creates_nested_directory(organizer, tmp_path):
    path = organizer.episode_path("Breaking Bad", 1, 1, "mkv")
    organizer.ensure_dir(path)

    assert (tmp_path / "series" / "Breaking Bad" / "Season 01").is_dir()


# ---------------------------------------------------------------------------
# Source name → (title, year) parsing
# ---------------------------------------------------------------------------

def test_parse_torrent_name_extracts_title_and_year():
    from ncrawler.library.organizer import parse_torrent_name

    title, year = parse_torrent_name("Inception.2010.1080p.BluRay.x264-GROUP")
    assert title == "Inception"
    assert year == 2010


def test_parse_torrent_name_handles_spaces():
    from ncrawler.library.organizer import parse_torrent_name

    title, year = parse_torrent_name("The Dark Knight 2008 1080p")
    assert title == "The Dark Knight"
    assert year == 2008


def test_parse_torrent_name_returns_none_year_when_not_found():
    from ncrawler.library.organizer import parse_torrent_name

    title, year = parse_torrent_name("SomeFilm.Without.Year.BluRay")
    assert year is None
