"""Tests for PredictionEngine -- prediction generation and DB storage."""

import json
import os
import tempfile
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

from sportsprediction.data.models.base import Base
from sportsprediction.data.models.game import Game
from sportsprediction.data.models.player import Player
from sportsprediction.data.models.team import Team
from sportsprediction.data.models.box_score import BoxScore
from sportsprediction.data.models.prediction import Prediction, PredictionOutcome
from sportsprediction.models.base_model import PredictionResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _seed_teams(session):
    """Insert two teams for FK constraints."""
    session.add(Team(team_id=1, full_name="Home Hawks"))
    session.add(Team(team_id=2, full_name="Away Eagles"))
    session.flush()


def _seed_game(session, game_id="0022400100", status="Scheduled",
               home_score=None, away_score=None, game_date=None):
    _seed_teams(session)
    g = Game(
        game_id=game_id,
        home_team_id=1,
        away_team_id=2,
        home_score=home_score,
        away_score=away_score,
        status=status,
        game_date=game_date or date.today(),
    )
    session.add(g)
    session.flush()
    return g


def _seed_player(session, player_id=101):
    p = Player(player_id=player_id, full_name="Test Player")
    session.add(p)
    session.flush()
    return p


def _mock_game_result():
    return PredictionResult(
        value=3.5,
        confidence_lower=-8.5,
        confidence_upper=15.5,
        metadata={"win_probability": 0.65, "predicted_winner": "home"},
    )


def _mock_totals_result():
    return PredictionResult(
        value=215.0,
        confidence_lower=200.0,
        confidence_upper=230.0,
        metadata={"interval_pct": 90},
    )


def _mock_player_results():
    return {
        "points": PredictionResult(value=22.0, confidence_lower=15.0, confidence_upper=29.0,
                                   metadata={"stat_type": "points"}),
        "rebounds": PredictionResult(value=8.0, confidence_lower=4.0, confidence_upper=12.0,
                                     metadata={"stat_type": "rebounds"}),
        "assists": PredictionResult(value=5.0, confidence_lower=2.0, confidence_upper=8.0,
                                    metadata={"stat_type": "assists"}),
        "fg3m": PredictionResult(value=2.0, confidence_lower=0.0, confidence_upper=4.0,
                                 metadata={"stat_type": "fg3m"}),
    }


def _make_engine(session, mock_gp=None, mock_tp=None, mock_pp=None):
    """Create a PredictionEngine with mocked model loading."""
    from sportsprediction.models.prediction_engine import PredictionEngine

    engine = PredictionEngine.__new__(PredictionEngine)
    engine._session = session
    engine._models_dir = "/tmp/test_models"
    engine._model_version = "v2026-03-08"
    engine._game_predictor = mock_gp or MagicMock()
    engine._totals_predictor = mock_tp or MagicMock()
    engine._player_props = mock_pp
    return engine


# ---------------------------------------------------------------------------
# Test 1: predict_game stores 3 Prediction rows
# ---------------------------------------------------------------------------

def test_predict_game_stores_three_predictions(session):
    """PredictionEngine.predict_game should store game_winner, game_spread, game_total."""
    game = _seed_game(session)

    mock_gp = MagicMock()
    mock_gp.predict.return_value = _mock_game_result()

    mock_tp = MagicMock()
    mock_tp.predict.return_value = _mock_totals_result()

    # Patch build_game_features to return valid features
    with patch("sportsprediction.models.prediction_engine.GamePredictor") as MockGPClass:
        MockGPClass.build_game_features.return_value = {"home_pace": 100.0, "is_home": 1.0}

        engine = _make_engine(session, mock_gp=mock_gp, mock_tp=mock_tp)
        preds = engine.predict_game(game)

    assert len(preds) == 3
    types = {p.prediction_type for p in preds}
    assert types == {"game_winner", "game_spread", "game_total"}

    # game_winner: predicted_value = 1 (home win), win_probability stored
    winner = [p for p in preds if p.prediction_type == "game_winner"][0]
    assert winner.predicted_value == 1.0
    assert winner.win_probability == pytest.approx(0.65)

    # game_spread: value and CI stored
    spread = [p for p in preds if p.prediction_type == "game_spread"][0]
    assert spread.predicted_value == pytest.approx(3.5)
    assert spread.confidence_lower == pytest.approx(-8.5)
    assert spread.confidence_upper == pytest.approx(15.5)

    # game_total: value and CI stored
    total = [p for p in preds if p.prediction_type == "game_total"][0]
    assert total.predicted_value == pytest.approx(215.0)

    # Check DB persistence
    db_preds = session.query(Prediction).filter_by(game_id=game.game_id).all()
    assert len(db_preds) == 3


# ---------------------------------------------------------------------------
# Test 2: predict_player_props stores 4 Prediction rows
# ---------------------------------------------------------------------------

def test_predict_player_props_stores_four_predictions(session):
    """predict_player_props should store player_points/rebounds/assists/3pm."""
    game = _seed_game(session)
    player = _seed_player(session)

    mock_pp = MagicMock()
    mock_pp.predict_all.return_value = _mock_player_results()

    with patch("sportsprediction.models.prediction_engine.get_features", return_value={"points_avg_5": 20.0}):
        engine = _make_engine(session, mock_pp=mock_pp)
        preds = engine.predict_player_props(game, player.player_id)

    assert len(preds) == 4
    types = {p.prediction_type for p in preds}
    assert types == {"player_points", "player_rebounds", "player_assists", "player_3pm"}

    pts = [p for p in preds if p.prediction_type == "player_points"][0]
    assert pts.predicted_value == pytest.approx(22.0)
    assert pts.player_id == player.player_id


# ---------------------------------------------------------------------------
# Test: predict_player_props returns empty when no features
# ---------------------------------------------------------------------------

def test_predict_player_props_no_features_returns_empty(session):
    """predict_player_props should return [] when get_features returns None."""
    game = _seed_game(session)
    player = _seed_player(session)

    mock_pp = MagicMock()

    with patch("sportsprediction.models.prediction_engine.get_features", return_value=None):
        engine = _make_engine(session, mock_pp=mock_pp)
        preds = engine.predict_player_props(game, player.player_id)

    assert preds == []
    mock_pp.predict_all.assert_not_called()


# ---------------------------------------------------------------------------
# Test 8: train_all_models builds training data and returns models
# ---------------------------------------------------------------------------

def test_train_all_models(session):
    """train_all_models should train and save model instances."""
    from sportsprediction.models.training import train_all_models

    with patch("sportsprediction.models.training.build_game_training_data") as mock_game_data, \
         patch("sportsprediction.models.training.build_player_training_data") as mock_player_data, \
         patch("sportsprediction.models.training.GamePredictor") as MockGP, \
         patch("sportsprediction.models.training.TotalsPredictor") as MockTP, \
         patch("sportsprediction.models.training.PlayerPropsPredictor") as MockPP:

        mock_game_data.return_value = {
            "game_features": [{"home_pace": 100}] * 30,
            "spread_targets": [5.0] * 30,
            "total_targets": [210.0] * 30,
        }
        mock_player_data.return_value = {
            "features": [{"points_avg_5": 20}] * 30,
            "targets": {"points": [20.0] * 30, "rebounds": [8.0] * 30,
                        "assists": [5.0] * 30, "fg3m": [2.0] * 30},
        }

        mock_gp_inst = MagicMock()
        MockGP.return_value = mock_gp_inst
        mock_tp_inst = MagicMock()
        MockTP.return_value = mock_tp_inst
        mock_pp_inst = MagicMock()
        MockPP.return_value = mock_pp_inst

        with tempfile.TemporaryDirectory() as tmpdir:
            result = train_all_models(session, models_dir=tmpdir)
            # Check version file was written
            assert os.path.exists(os.path.join(tmpdir, "version.txt"))

        assert "game_predictor" in result
        assert "totals_predictor" in result
        assert "player_props" in result
        mock_gp_inst.train.assert_called_once()
        mock_tp_inst.train.assert_called_once()
        mock_pp_inst.train_all.assert_called_once()
