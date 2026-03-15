"""Tests for GamePredictor -- win probability and spread prediction."""

from unittest.mock import MagicMock, patch

import pytest

from sportsprediction.models.game_predictor import GamePredictor
from sportsprediction.models.base_model import PredictionResult


def _make_game_features(
    home_off: float = 110.0,
    away_off: float = 105.0,
    home_def: float = 108.0,
    away_def: float = 110.0,
    home_pace: float = 100.0,
    away_pace: float = 98.0,
    home_rest: float = 1.0,
    away_rest: float = 1.0,
    home_winpct: float = 0.6,
    away_winpct: float = 0.5,
) -> dict:
    """Build a game feature dict with home_/away_/diff_ prefixes."""
    return {
        "home_pace": home_pace,
        "away_pace": away_pace,
        "diff_pace": home_pace - away_pace,
        "home_offensive_rating": home_off,
        "away_offensive_rating": away_off,
        "diff_offensive_rating": home_off - away_off,
        "home_defensive_rating": home_def,
        "away_defensive_rating": away_def,
        "diff_defensive_rating": home_def - away_def,
        "home_rest_days": home_rest,
        "away_rest_days": away_rest,
        "diff_rest_days": home_rest - away_rest,
        "home_season_win_pct": home_winpct,
        "away_season_win_pct": away_winpct,
        "diff_season_win_pct": home_winpct - away_winpct,
        "is_home": 1.0,
    }


def _generate_synthetic_data(n_games: int = 40):
    """Generate synthetic game data with clear home/away patterns.

    First half: home team dominates (positive spread).
    Second half: away team dominates (negative spread).
    """
    features = []
    targets = []

    for i in range(n_games // 2):
        # Home team dominates
        feat = _make_game_features(
            home_off=115.0 + i * 0.2,
            away_off=100.0,
            home_winpct=0.7,
            away_winpct=0.3,
        )
        features.append(feat)
        targets.append(8.0 + i * 0.3)  # Positive spread (home wins)

    for i in range(n_games // 2):
        # Away team dominates
        feat = _make_game_features(
            home_off=100.0,
            away_off=115.0 + i * 0.2,
            home_winpct=0.3,
            away_winpct=0.7,
        )
        features.append(feat)
        targets.append(-8.0 - i * 0.3)  # Negative spread (away wins)

    return features, targets


class TestGamePredictorBuildFeatures:
    """Test build_game_features aggregation."""

    def test_build_game_features_aggregates_home_away(self):
        """build_game_features produces home_/away_/diff_ prefixed dict."""
        mock_session = MagicMock()

        # Mock TeamFeatures rows
        home_tf = MagicMock()
        home_tf.pace = 100.0
        home_tf.offensive_rating = 112.0
        home_tf.defensive_rating = 108.0
        home_tf.rest_days = 2
        home_tf.season_win_pct = 0.65

        away_tf = MagicMock()
        away_tf.pace = 98.0
        away_tf.offensive_rating = 105.0
        away_tf.defensive_rating = 110.0
        away_tf.rest_days = 1
        away_tf.season_win_pct = 0.45

        mock_game = MagicMock()
        mock_game.game_id = "0022400001"
        mock_game.home_team_id = 1
        mock_game.away_team_id = 2

        # Mock session.query chain
        mock_query = MagicMock()
        mock_filter = MagicMock()

        def filter_by_side(**kwargs):
            result = MagicMock()
            if kwargs.get("team_id") == 1:
                result.first.return_value = home_tf
            else:
                result.first.return_value = away_tf
            return result

        mock_session.query.return_value = mock_query
        mock_query.filter_by = filter_by_side

        result = GamePredictor.build_game_features(mock_session, mock_game)

        assert result is not None
        assert result["home_pace"] == 100.0
        assert result["away_pace"] == 98.0
        assert result["diff_pace"] == pytest.approx(2.0)
        assert result["home_offensive_rating"] == 112.0
        assert result["away_offensive_rating"] == 105.0
        assert result["diff_offensive_rating"] == pytest.approx(7.0)
        assert result["is_home"] == 1.0


class TestGamePredictorTrainPredict:
    """Test training and prediction."""

    def test_predict_returns_prediction_result(self):
        """After training, predict() returns PredictionResult with spread and win_probability."""
        gp = GamePredictor()
        features, targets = _generate_synthetic_data(40)
        gp.train(features, targets)

        result = gp.predict(features[0])

        assert isinstance(result, PredictionResult)
        assert isinstance(result.value, float)
        assert "win_probability" in result.metadata
        assert "predicted_winner" in result.metadata

    def test_win_probability_favors_home_when_home_dominates(self):
        """Win probability > 0.5 when features clearly favor home team."""
        gp = GamePredictor()
        features, targets = _generate_synthetic_data(40)
        gp.train(features, targets)

        # Strong home team features
        strong_home = _make_game_features(
            home_off=120.0, away_off=95.0, home_winpct=0.8, away_winpct=0.2
        )
        result = gp.predict(strong_home)
        assert result.metadata["win_probability"] > 0.5
        assert result.metadata["predicted_winner"] == "home"

    def test_win_probability_favors_away_when_away_dominates(self):
        """Win probability < 0.5 when features clearly favor away team."""
        gp = GamePredictor()
        features, targets = _generate_synthetic_data(40)
        gp.train(features, targets)

        # Strong away team features
        strong_away = _make_game_features(
            home_off=95.0, away_off=120.0, home_winpct=0.2, away_winpct=0.8
        )
        result = gp.predict(strong_away)
        assert result.metadata["win_probability"] < 0.5
        assert result.metadata["predicted_winner"] == "away"

    def test_confidence_interval_contains_spread(self):
        """Confidence interval [lower, upper] contains the predicted spread."""
        gp = GamePredictor()
        features, targets = _generate_synthetic_data(40)
        gp.train(features, targets)

        result = gp.predict(features[5])
        assert result.confidence_lower <= result.value <= result.confidence_upper

    def test_get_feature_names(self):
        """get_feature_names() returns the 16 expected feature names."""
        gp = GamePredictor()
        names = gp.get_feature_names()
        assert len(names) == 16
        assert "is_home" in names
        assert "home_pace" in names
        assert "diff_offensive_rating" in names

    def test_handles_missing_features(self):
        """Model handles missing/None features gracefully (fills with 0.0)."""
        gp = GamePredictor()
        features, targets = _generate_synthetic_data(40)
        gp.train(features, targets)

        sparse = {"home_pace": 100.0, "is_home": 1.0}  # Most features missing
        result = gp.predict(sparse)
        assert isinstance(result, PredictionResult)
        assert isinstance(result.value, float)

    def test_handles_none_values(self):
        """Model handles None values in feature dict."""
        gp = GamePredictor()
        features, targets = _generate_synthetic_data(40)
        gp.train(features, targets)

        feat = _make_game_features()
        feat["home_pace"] = None
        feat["diff_pace"] = None
        result = gp.predict(feat)
        assert isinstance(result, PredictionResult)
