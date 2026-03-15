"""Tests for TotalsPredictor -- over/under with quantile regression CI."""

import pytest

from sportsprediction.models.totals_predictor import TotalsPredictor
from sportsprediction.models.base_model import PredictionResult


def _make_game_features(
    home_pace: float = 100.0,
    away_pace: float = 98.0,
    home_off: float = 110.0,
    away_off: float = 108.0,
    home_def: float = 108.0,
    away_def: float = 110.0,
    home_rest: float = 1.0,
    away_rest: float = 1.0,
    home_winpct: float = 0.55,
    away_winpct: float = 0.50,
) -> dict:
    """Build game feature dict."""
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


def _generate_totals_data(n_games: int = 80):
    """Generate synthetic data where pace correlates with total score.

    High pace -> high total. Low pace -> low total.
    Need 80+ samples for GBR to learn.
    """
    import random
    random.seed(42)

    features = []
    targets = []

    for _ in range(n_games // 2):
        # High pace games -> high totals
        hp = random.uniform(102, 108)
        ap = random.uniform(102, 108)
        feat = _make_game_features(
            home_pace=hp,
            away_pace=ap,
            home_off=random.uniform(112, 118),
            away_off=random.uniform(112, 118),
        )
        features.append(feat)
        total = 215 + (hp + ap - 200) * 1.5 + random.uniform(-5, 5)
        targets.append(total)

    for _ in range(n_games // 2):
        # Low pace games -> low totals
        hp = random.uniform(90, 96)
        ap = random.uniform(90, 96)
        feat = _make_game_features(
            home_pace=hp,
            away_pace=ap,
            home_off=random.uniform(100, 106),
            away_off=random.uniform(100, 106),
        )
        features.append(feat)
        total = 195 + (hp + ap - 200) * 1.5 + random.uniform(-5, 5)
        targets.append(total)

    return features, targets


class TestTotalsPredictor:
    """Test TotalsPredictor training and prediction."""

    def test_trains_on_game_features(self):
        """TotalsPredictor trains on feature dicts with total score targets."""
        tp = TotalsPredictor()
        features, targets = _generate_totals_data(80)
        tp.train(features, targets)
        # No exception = success

    def test_predict_returns_prediction_result(self):
        """predict() returns PredictionResult with value from median model."""
        tp = TotalsPredictor()
        features, targets = _generate_totals_data(80)
        tp.train(features, targets)

        result = tp.predict(features[0])
        assert isinstance(result, PredictionResult)
        assert isinstance(result.value, float)
        assert result.metadata.get("interval_pct") == 90

    def test_higher_pace_predicts_higher_totals(self):
        """Directional: higher combined pace should predict higher totals."""
        tp = TotalsPredictor()
        features, targets = _generate_totals_data(80)
        tp.train(features, targets)

        high_pace = _make_game_features(
            home_pace=106.0, away_pace=106.0,
            home_off=116.0, away_off=116.0,
        )
        low_pace = _make_game_features(
            home_pace=92.0, away_pace=92.0,
            home_off=102.0, away_off=102.0,
        )

        high_result = tp.predict(high_pace)
        low_result = tp.predict(low_pace)
        assert high_result.value > low_result.value

    def test_quantile_ordering_preserved(self):
        """confidence_lower < value < confidence_upper."""
        tp = TotalsPredictor()
        features, targets = _generate_totals_data(80)
        tp.train(features, targets)

        result = tp.predict(features[10])
        assert result.confidence_lower < result.value < result.confidence_upper

    def test_confidence_interval_reasonable_width(self):
        """CI width is not 0 and not wider than 100 points."""
        tp = TotalsPredictor()
        features, targets = _generate_totals_data(80)
        tp.train(features, targets)

        result = tp.predict(features[5])
        width = result.confidence_upper - result.confidence_lower
        assert width > 0
        assert width < 100

    def test_cross_validate_returns_scores(self):
        """cross_validate returns dict with mean and scores."""
        tp = TotalsPredictor()
        features, targets = _generate_totals_data(80)

        cv_result = tp.cross_validate(features, targets, cv=3)
        assert "mean" in cv_result
        assert "scores" in cv_result
        assert len(cv_result["scores"]) == 3
