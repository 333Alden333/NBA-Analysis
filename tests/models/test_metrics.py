"""Tests for metrics module -- accuracy computation and calibration."""

from datetime import date, datetime

import pytest

from hermes.data.models.game import Game
from hermes.data.models.player import Player
from hermes.data.models.team import Team
from hermes.data.models.prediction import Prediction, PredictionOutcome


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _seed_teams(session):
    session.add(Team(team_id=1, full_name="Home Hawks"))
    session.add(Team(team_id=2, full_name="Away Eagles"))
    session.flush()


def _seed_game(session, game_id="0022400100"):
    _seed_teams(session)
    g = Game(
        game_id=game_id, home_team_id=1, away_team_id=2,
        home_score=110, away_score=105,
        status="Final", game_date=date(2024, 6, 15),
    )
    session.add(g)
    session.flush()
    return g


def _add_resolved_prediction(session, game_id, pred_type, predicted_value,
                              actual_value, is_correct, win_probability=None,
                              player_id=None, confidence_lower=None,
                              confidence_upper=None, created_at=None):
    """Insert a Prediction + PredictionOutcome pair."""
    pred = Prediction(
        game_id=game_id,
        prediction_type=pred_type,
        predicted_value=predicted_value,
        win_probability=win_probability,
        player_id=player_id,
        confidence_lower=confidence_lower,
        confidence_upper=confidence_upper,
        model_version="v2026-03-08",
        created_at=created_at or datetime.utcnow(),
    )
    session.add(pred)
    session.flush()

    outcome = PredictionOutcome(
        prediction_id=pred.id,
        actual_value=actual_value,
        is_correct=is_correct,
        resolved_at=datetime.utcnow(),
    )
    session.add(outcome)
    session.flush()
    return pred, outcome


# ---------------------------------------------------------------------------
# Test 1: compute_metrics for game_winner returns hit_rate and brier_score
# ---------------------------------------------------------------------------

def test_compute_metrics_game_winner(session):
    """compute_metrics for game_winner returns hit_rate, brier_score, counts."""
    from hermes.models.metrics import compute_metrics

    game = _seed_game(session)

    # 3 correct, 1 incorrect out of 4
    _add_resolved_prediction(session, game.game_id, "game_winner", 1.0, 1.0, 1, win_probability=0.8)
    for gid_suffix in range(1, 4):
        gid = f"002240010{gid_suffix}"
        g = Game(game_id=gid, home_team_id=1, away_team_id=2,
                 home_score=110, away_score=105, status="Final",
                 game_date=date(2024, 6, 15))
        session.add(g)
        session.flush()
        if gid_suffix < 3:
            _add_resolved_prediction(session, gid, "game_winner", 1.0, 1.0, 1, win_probability=0.7)
        else:
            _add_resolved_prediction(session, gid, "game_winner", 1.0, 0.0, 0, win_probability=0.6)

    metrics = compute_metrics(session, prediction_type="game_winner")

    assert "hit_rate" in metrics
    assert metrics["hit_rate"] == pytest.approx(0.75)
    assert "brier_score" in metrics
    assert metrics["total_resolved"] == 4
    assert metrics["total_predictions"] == 4


# ---------------------------------------------------------------------------
# Test 2: Brier score for perfect predictions is 0.0
# ---------------------------------------------------------------------------

def test_brier_score_perfect(session):
    """Brier score should be 0.0 for perfectly calibrated predictions."""
    from hermes.models.metrics import compute_metrics

    game = _seed_game(session)

    # Home win predicted with prob 1.0, actual home win
    _add_resolved_prediction(session, game.game_id, "game_winner", 1.0, 1.0, 1, win_probability=1.0)

    gid2 = "0022400102"
    session.add(Game(game_id=gid2, home_team_id=1, away_team_id=2,
                     home_score=100, away_score=110, status="Final",
                     game_date=date(2024, 6, 15)))
    session.flush()
    # Away win predicted with prob 0.0, actual away win
    _add_resolved_prediction(session, gid2, "game_winner", 0.0, 0.0, 1, win_probability=0.0)

    metrics = compute_metrics(session, prediction_type="game_winner")
    assert metrics["brier_score"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Test 3: Brier score for always-wrong approaches 1.0
# ---------------------------------------------------------------------------

def test_brier_score_always_wrong(session):
    """Brier score should approach 1.0 for always-wrong predictions."""
    from hermes.models.metrics import compute_metrics

    game = _seed_game(session)

    # Home predicted with prob 1.0, but away won
    _add_resolved_prediction(session, game.game_id, "game_winner", 1.0, 0.0, 0, win_probability=1.0)

    gid2 = "0022400102"
    session.add(Game(game_id=gid2, home_team_id=1, away_team_id=2,
                     home_score=120, away_score=100, status="Final",
                     game_date=date(2024, 6, 15)))
    session.flush()
    # Away predicted with prob 0.0, but home won
    _add_resolved_prediction(session, gid2, "game_winner", 0.0, 1.0, 0, win_probability=0.0)

    metrics = compute_metrics(session, prediction_type="game_winner")
    assert metrics["brier_score"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Test 4: MAE for regression types
# ---------------------------------------------------------------------------

def test_compute_metrics_regression_mae(session):
    """Regression types should return MAE instead of Brier score."""
    from hermes.models.metrics import compute_metrics

    game = _seed_game(session)

    _add_resolved_prediction(session, game.game_id, "game_spread", 5.0, 3.0, 1,
                              confidence_lower=-5.0, confidence_upper=15.0)

    gid2 = "0022400102"
    session.add(Game(game_id=gid2, home_team_id=1, away_team_id=2,
                     home_score=110, away_score=105, status="Final",
                     game_date=date(2024, 6, 15)))
    session.flush()
    _add_resolved_prediction(session, gid2, "game_spread", 8.0, 2.0, 1,
                              confidence_lower=-2.0, confidence_upper=18.0)

    metrics = compute_metrics(session, prediction_type="game_spread")
    assert "mae" in metrics
    # MAE = (|5-3| + |8-2|) / 2 = (2+6)/2 = 4.0
    assert metrics["mae"] == pytest.approx(4.0)
    assert "brier_score" not in metrics


# ---------------------------------------------------------------------------
# Test 5: compute_calibration returns bucket data
# ---------------------------------------------------------------------------

def test_compute_calibration(session):
    """compute_calibration should return bucket data for calibration plot."""
    from hermes.models.metrics import compute_calibration

    game = _seed_game(session)

    # Seed several predictions with various win probabilities
    for i in range(10):
        gid = f"00224001{i:02d}"
        if gid != game.game_id:
            session.add(Game(game_id=gid, home_team_id=1, away_team_id=2,
                             home_score=110, away_score=105, status="Final",
                             game_date=date(2024, 6, 15)))
            session.flush()
        wp = 0.1 * (i + 1)  # 0.1 to 1.0
        actual = 1.0 if i >= 5 else 0.0
        correct = 1 if (wp > 0.5 and actual == 1.0) or (wp <= 0.5 and actual == 0.0) else 0
        _add_resolved_prediction(session, gid, "game_winner", 1.0 if wp > 0.5 else 0.0,
                                  actual, correct, win_probability=wp)

    buckets = compute_calibration(session, bins=5)
    assert isinstance(buckets, list)
    assert len(buckets) > 0
    assert "predicted_avg" in buckets[0]
    assert "actual_rate" in buckets[0]
    assert "count" in buckets[0]


# ---------------------------------------------------------------------------
# Test 6: No resolved predictions returns zero metrics gracefully
# ---------------------------------------------------------------------------

def test_compute_metrics_no_data(session):
    """compute_metrics with no resolved predictions returns zeroed metrics."""
    from hermes.models.metrics import compute_metrics

    metrics = compute_metrics(session, prediction_type="game_winner")
    assert metrics["total_predictions"] == 0
    assert metrics["total_resolved"] == 0
    assert metrics["hit_rate"] == 0.0


# ---------------------------------------------------------------------------
# Test 7: Metrics can be filtered by date range
# ---------------------------------------------------------------------------

def test_compute_metrics_date_filter(session):
    """Metrics should respect start_date/end_date filtering."""
    from hermes.models.metrics import compute_metrics

    game = _seed_game(session)

    _add_resolved_prediction(session, game.game_id, "game_winner", 1.0, 1.0, 1,
                              win_probability=0.8,
                              created_at=datetime(2024, 6, 15, 12, 0))

    gid2 = "0022400102"
    session.add(Game(game_id=gid2, home_team_id=1, away_team_id=2,
                     home_score=110, away_score=105, status="Final",
                     game_date=date(2024, 12, 1)))
    session.flush()
    _add_resolved_prediction(session, gid2, "game_winner", 1.0, 0.0, 0,
                              win_probability=0.6,
                              created_at=datetime(2024, 12, 1, 12, 0))

    # Filter to only June
    metrics = compute_metrics(
        session, prediction_type="game_winner",
        start_date=date(2024, 6, 1), end_date=date(2024, 6, 30),
    )
    assert metrics["total_resolved"] == 1
    assert metrics["hit_rate"] == pytest.approx(1.0)
