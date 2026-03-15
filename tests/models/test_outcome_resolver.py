"""Tests for outcome resolver -- backfilling actuals from completed games."""

from datetime import date, datetime

import pytest

from sportsprediction.data.models.base import Base
from sportsprediction.data.models.game import Game
from sportsprediction.data.models.player import Player
from sportsprediction.data.models.team import Team
from sportsprediction.data.models.box_score import BoxScore
from sportsprediction.data.models.prediction import Prediction, PredictionOutcome


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _seed_teams(session):
    session.add(Team(team_id=1, full_name="Home Hawks"))
    session.add(Team(team_id=2, full_name="Away Eagles"))
    session.flush()


def _seed_final_game(session, game_id="0022400100", home_score=110, away_score=105):
    _seed_teams(session)
    g = Game(
        game_id=game_id, home_team_id=1, away_team_id=2,
        home_score=home_score, away_score=away_score,
        status="Final", game_date=date.today(),
    )
    session.add(g)
    session.flush()
    return g


def _seed_prediction(session, game_id, pred_type, predicted_value,
                     win_probability=None, player_id=None,
                     confidence_lower=None, confidence_upper=None):
    p = Prediction(
        game_id=game_id,
        prediction_type=pred_type,
        predicted_value=predicted_value,
        win_probability=win_probability,
        player_id=player_id,
        confidence_lower=confidence_lower,
        confidence_upper=confidence_upper,
        model_version="v2026-03-08",
    )
    session.add(p)
    session.flush()
    return p


# ---------------------------------------------------------------------------
# Test 3: resolve_outcomes creates PredictionOutcome rows
# ---------------------------------------------------------------------------

def test_resolve_outcomes_creates_outcome_rows(session):
    """resolve_outcomes should create PredictionOutcome with actual values."""
    from sportsprediction.models.outcome_resolver import resolve_outcomes

    game = _seed_final_game(session, home_score=110, away_score=105)
    _seed_prediction(session, game.game_id, "game_winner", 1.0, win_probability=0.65)
    _seed_prediction(session, game.game_id, "game_spread", 3.5,
                     confidence_lower=-8.5, confidence_upper=15.5)
    _seed_prediction(session, game.game_id, "game_total", 215.0,
                     confidence_lower=200.0, confidence_upper=230.0)

    count = resolve_outcomes(session)
    assert count == 3

    outcomes = session.query(PredictionOutcome).all()
    assert len(outcomes) == 3


# ---------------------------------------------------------------------------
# Test 4: is_correct for game_winner
# ---------------------------------------------------------------------------

def test_game_winner_is_correct(session):
    """is_correct=1 if predicted winner matches actual winner."""
    from sportsprediction.models.outcome_resolver import resolve_outcomes

    # Home wins 110-105, predicted home win (value=1)
    game = _seed_final_game(session, home_score=110, away_score=105)
    pred = _seed_prediction(session, game.game_id, "game_winner", 1.0, win_probability=0.65)

    resolve_outcomes(session)

    outcome = session.query(PredictionOutcome).filter_by(prediction_id=pred.id).first()
    assert outcome is not None
    assert outcome.actual_value == 1.0  # home won
    assert outcome.is_correct == 1


def test_game_winner_is_incorrect(session):
    """is_correct=0 if predicted winner does NOT match actual."""
    from sportsprediction.models.outcome_resolver import resolve_outcomes

    # Away wins 100-110, but predicted home win (value=1)
    game = _seed_final_game(session, home_score=100, away_score=110)
    pred = _seed_prediction(session, game.game_id, "game_winner", 1.0, win_probability=0.65)

    resolve_outcomes(session)

    outcome = session.query(PredictionOutcome).filter_by(prediction_id=pred.id).first()
    assert outcome.actual_value == 0.0  # away won
    assert outcome.is_correct == 0


# ---------------------------------------------------------------------------
# Test 5: is_correct for player props (within CI)
# ---------------------------------------------------------------------------

def test_player_prop_within_ci_is_correct(session):
    """is_correct=1 if actual stat is within confidence interval."""
    from sportsprediction.models.outcome_resolver import resolve_outcomes

    game = _seed_final_game(session)
    player = Player(player_id=101, full_name="Test Player")
    session.add(player)
    session.flush()

    bs = BoxScore(game_id=game.game_id, player_id=101, team_id=1, points=22)
    session.add(bs)
    session.flush()

    pred = _seed_prediction(
        session, game.game_id, "player_points", 20.0,
        player_id=101, confidence_lower=15.0, confidence_upper=25.0,
    )

    resolve_outcomes(session)

    outcome = session.query(PredictionOutcome).filter_by(prediction_id=pred.id).first()
    assert outcome.actual_value == 22.0
    assert outcome.is_correct == 1


def test_player_prop_outside_ci_is_incorrect(session):
    """is_correct=0 if actual stat is outside confidence interval."""
    from sportsprediction.models.outcome_resolver import resolve_outcomes

    game = _seed_final_game(session)
    player = Player(player_id=102, full_name="Another Player")
    session.add(player)
    session.flush()

    bs = BoxScore(game_id=game.game_id, player_id=102, team_id=1, points=35)
    session.add(bs)
    session.flush()

    pred = _seed_prediction(
        session, game.game_id, "player_points", 20.0,
        player_id=102, confidence_lower=15.0, confidence_upper=25.0,
    )

    resolve_outcomes(session)

    outcome = session.query(PredictionOutcome).filter_by(prediction_id=pred.id).first()
    assert outcome.actual_value == 35.0
    assert outcome.is_correct == 0


# ---------------------------------------------------------------------------
# Test 6: resolve_outcomes skips already-resolved and non-Final
# ---------------------------------------------------------------------------

def test_resolve_skips_already_resolved(session):
    """Already-resolved predictions should not be re-processed."""
    from sportsprediction.models.outcome_resolver import resolve_outcomes

    game = _seed_final_game(session)
    pred = _seed_prediction(session, game.game_id, "game_winner", 1.0, win_probability=0.65)

    # First resolve
    count1 = resolve_outcomes(session)
    assert count1 == 1

    # Second resolve should find nothing new
    count2 = resolve_outcomes(session)
    assert count2 == 0


def test_resolve_skips_non_final_games(session):
    """Predictions for games not yet Final should be skipped."""
    from sportsprediction.models.outcome_resolver import resolve_outcomes

    _seed_teams(session)
    g = Game(
        game_id="0022400200", home_team_id=1, away_team_id=2,
        home_score=None, away_score=None,
        status="Scheduled", game_date=date.today(),
    )
    session.add(g)
    session.flush()

    _seed_prediction(session, g.game_id, "game_winner", 1.0, win_probability=0.65)

    count = resolve_outcomes(session)
    assert count == 0


# ---------------------------------------------------------------------------
# Test 7: resolve_outcomes skips games with null scores
# ---------------------------------------------------------------------------

def test_resolve_skips_null_scores(session):
    """Games with status=Final but null scores should be skipped."""
    from sportsprediction.models.outcome_resolver import resolve_outcomes

    _seed_teams(session)
    g = Game(
        game_id="0022400300", home_team_id=1, away_team_id=2,
        home_score=None, away_score=None,
        status="Final", game_date=date.today(),
    )
    session.add(g)
    session.flush()

    _seed_prediction(session, g.game_id, "game_winner", 1.0, win_probability=0.65)

    count = resolve_outcomes(session)
    assert count == 0
