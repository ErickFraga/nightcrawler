"""
RED tests for the rules engine.
A MonitoringRule defines criteria (genre, rating, director, actor, studio).
The engine evaluates a TitleCandidate against a list of rules and returns matches.
"""
import pytest
from ncrawler.rules.schema import MonitoringRule, MediaType
from ncrawler.rules.engine import RulesEngine, TitleCandidate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def action_rule():
    return MonitoringRule(
        id=1,
        name="Action 7+",
        enabled=True,
        genres=["Action"],
        min_rating=7.0,
        directors=[],
        actors=[],
        studios=[],
        media_type=MediaType.MOVIE,
        quality_profile="1080p",
    )


@pytest.fixture
def drama_rule():
    return MonitoringRule(
        id=2,
        name="Drama any rating",
        enabled=True,
        genres=["Drama"],
        min_rating=0.0,
        directors=[],
        actors=[],
        studios=[],
        media_type=MediaType.MOVIE,
        quality_profile="1080p",
    )


@pytest.fixture
def director_rule():
    return MonitoringRule(
        id=3,
        name="Nolan movies",
        enabled=True,
        genres=[],
        min_rating=0.0,
        directors=["Christopher Nolan"],
        actors=[],
        studios=[],
        media_type=MediaType.MOVIE,
        quality_profile="1080p",
    )


@pytest.fixture
def actor_rule():
    return MonitoringRule(
        id=4,
        name="Cillian Murphy",
        enabled=True,
        genres=[],
        min_rating=0.0,
        directors=[],
        actors=["Cillian Murphy"],
        studios=[],
        media_type=MediaType.MOVIE,
        quality_profile="1080p",
    )


@pytest.fixture
def studio_rule():
    return MonitoringRule(
        id=5,
        name="A24 everything",
        enabled=True,
        genres=[],
        min_rating=0.0,
        directors=[],
        actors=[],
        studios=["A24"],
        media_type=MediaType.MOVIE,
        quality_profile="1080p",
    )


@pytest.fixture
def disabled_rule():
    return MonitoringRule(
        id=6,
        name="Disabled rule",
        enabled=False,
        genres=["Action"],
        min_rating=0.0,
        directors=[],
        actors=[],
        studios=[],
        media_type=MediaType.MOVIE,
        quality_profile="1080p",
    )


@pytest.fixture
def series_rule():
    return MonitoringRule(
        id=7,
        name="Sci-Fi series",
        enabled=True,
        genres=["Sci-Fi"],
        min_rating=8.0,
        directors=[],
        actors=[],
        studios=[],
        media_type=MediaType.SERIES,
        quality_profile="1080p",
    )


@pytest.fixture
def engine(action_rule, drama_rule, director_rule, actor_rule, studio_rule, disabled_rule, series_rule):
    return RulesEngine(rules=[action_rule, drama_rule, director_rule, actor_rule, studio_rule, disabled_rule, series_rule])


# ---------------------------------------------------------------------------
# Genre matching
# ---------------------------------------------------------------------------

def test_rule_matches_by_genre(action_rule):
    candidate = TitleCandidate(
        title="Mad Max",
        year=2024,
        genres=["Action", "Adventure"],
        rating=8.1,
        directors=["George Miller"],
        actors=["Tom Hardy"],
        studios=["Village Roadshow"],
        media_type=MediaType.MOVIE,
    )
    assert action_rule.matches(candidate) is True


def test_rule_does_not_match_wrong_genre(action_rule):
    candidate = TitleCandidate(
        title="Quiet Romance",
        year=2024,
        genres=["Romance"],
        rating=8.5,
        directors=["Sofia Coppola"],
        actors=["Saoirse Ronan"],
        studios=["A24"],
        media_type=MediaType.MOVIE,
    )
    assert action_rule.matches(candidate) is False


def test_rule_with_empty_genres_matches_any_genre(drama_rule):
    """A rule with no genre filter matches titles of any genre."""
    drama_rule.genres = []
    candidate = TitleCandidate(
        title="Sci-Fi Epic",
        year=2024,
        genres=["Sci-Fi"],
        rating=5.0,
        directors=[],
        actors=[],
        studios=[],
        media_type=MediaType.MOVIE,
    )
    assert drama_rule.matches(candidate) is True


# ---------------------------------------------------------------------------
# Rating matching
# ---------------------------------------------------------------------------

def test_rule_matches_above_min_rating(action_rule):
    candidate = TitleCandidate(
        title="Good Action Film",
        year=2024,
        genres=["Action"],
        rating=7.5,
        directors=[],
        actors=[],
        studios=[],
        media_type=MediaType.MOVIE,
    )
    assert action_rule.matches(candidate) is True


def test_rule_fails_below_min_rating(action_rule):
    candidate = TitleCandidate(
        title="Bad Action Film",
        year=2024,
        genres=["Action"],
        rating=6.9,
        directors=[],
        actors=[],
        studios=[],
        media_type=MediaType.MOVIE,
    )
    assert action_rule.matches(candidate) is False


def test_rule_matches_exact_min_rating(action_rule):
    candidate = TitleCandidate(
        title="Borderline Film",
        year=2024,
        genres=["Action"],
        rating=7.0,
        directors=[],
        actors=[],
        studios=[],
        media_type=MediaType.MOVIE,
    )
    assert action_rule.matches(candidate) is True


# ---------------------------------------------------------------------------
# Director / actor / studio matching
# ---------------------------------------------------------------------------

def test_rule_matches_by_director(director_rule):
    candidate = TitleCandidate(
        title="Inception 2",
        year=2026,
        genres=["Thriller"],
        rating=6.0,
        directors=["Christopher Nolan"],
        actors=["Leonardo DiCaprio"],
        studios=["Warner Bros"],
        media_type=MediaType.MOVIE,
    )
    assert director_rule.matches(candidate) is True


def test_rule_does_not_match_wrong_director(director_rule):
    candidate = TitleCandidate(
        title="Some Film",
        year=2026,
        genres=["Thriller"],
        rating=6.0,
        directors=["James Cameron"],
        actors=[],
        studios=[],
        media_type=MediaType.MOVIE,
    )
    assert director_rule.matches(candidate) is False


def test_rule_matches_by_actor(actor_rule):
    candidate = TitleCandidate(
        title="New Thriller",
        year=2026,
        genres=["Thriller"],
        rating=5.0,
        directors=["Unknown Director"],
        actors=["Cillian Murphy", "Emily Blunt"],
        studios=[],
        media_type=MediaType.MOVIE,
    )
    assert actor_rule.matches(candidate) is True


def test_rule_matches_by_studio(studio_rule):
    candidate = TitleCandidate(
        title="Indie Gem",
        year=2024,
        genres=["Drama"],
        rating=4.0,
        directors=["Ari Aster"],
        actors=[],
        studios=["A24"],
        media_type=MediaType.MOVIE,
    )
    assert studio_rule.matches(candidate) is True


# ---------------------------------------------------------------------------
# Media type matching
# ---------------------------------------------------------------------------

def test_rule_movie_type_does_not_match_series(action_rule):
    candidate = TitleCandidate(
        title="Action Series",
        year=2024,
        genres=["Action"],
        rating=8.0,
        directors=[],
        actors=[],
        studios=[],
        media_type=MediaType.SERIES,
    )
    assert action_rule.matches(candidate) is False


def test_rule_both_type_matches_movie_and_series():
    rule = MonitoringRule(
        id=99,
        name="Everything",
        enabled=True,
        genres=["Action"],
        min_rating=0.0,
        directors=[],
        actors=[],
        studios=[],
        media_type=MediaType.BOTH,
        quality_profile="1080p",
    )
    movie = TitleCandidate(title="A", year=2024, genres=["Action"], rating=5.0,
                           directors=[], actors=[], studios=[], media_type=MediaType.MOVIE)
    series = TitleCandidate(title="B", year=2024, genres=["Action"], rating=5.0,
                            directors=[], actors=[], studios=[], media_type=MediaType.SERIES)
    assert rule.matches(movie) is True
    assert rule.matches(series) is True


# ---------------------------------------------------------------------------
# Disabled rule
# ---------------------------------------------------------------------------

def test_disabled_rule_never_matches(disabled_rule):
    candidate = TitleCandidate(
        title="Perfect Match",
        year=2024,
        genres=["Action"],
        rating=9.9,
        directors=[],
        actors=[],
        studios=[],
        media_type=MediaType.MOVIE,
    )
    assert disabled_rule.matches(candidate) is False


# ---------------------------------------------------------------------------
# Engine: evaluate list of rules
# ---------------------------------------------------------------------------

def test_engine_returns_matching_rules(engine):
    candidate = TitleCandidate(
        title="Epic Action",
        year=2024,
        genres=["Action"],
        rating=8.0,
        directors=[],
        actors=[],
        studios=[],
        media_type=MediaType.MOVIE,
    )
    matching = engine.evaluate(candidate)
    # Should match action_rule (id=1) only; drama needs Drama genre, etc.
    assert any(r.id == 1 for r in matching)
    assert not any(r.id == 6 for r in matching)  # disabled


def test_engine_returns_empty_when_no_rules_match(engine):
    candidate = TitleCandidate(
        title="Boring Documentary",
        year=2024,
        genres=["Documentary"],
        rating=3.0,
        directors=[],
        actors=[],
        studios=[],
        media_type=MediaType.MOVIE,
    )
    matching = engine.evaluate(candidate)
    assert matching == []


def test_engine_can_match_multiple_rules(engine, action_rule, drama_rule):
    """A title matching several rules returns all of them."""
    candidate = TitleCandidate(
        title="Action Drama",
        year=2024,
        genres=["Action", "Drama"],
        rating=8.0,
        directors=[],
        actors=[],
        studios=[],
        media_type=MediaType.MOVIE,
    )
    matching = engine.evaluate(candidate)
    ids = {r.id for r in matching}
    assert 1 in ids  # action_rule
    assert 2 in ids  # drama_rule
