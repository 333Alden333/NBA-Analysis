"""Tests for PlayerPropPredictor and PlayerPropsPredictor."""

import math
import pytest
import random

from hermes.models.base_model import PredictionResult
from hermes.models.player_predictor import PlayerPropPredictor, PlayerPropsPredictor


def _make_feature_dict(
    points_avg=20.0,
    rebounds_avg=5.0,
    assists_avg=4.0,
    fg3_pct_avg=0.35,
    matchup_avg_points=20.0,
    matchup_avg_rebounds=5.0,
    matchup_avg_assists=4.0,
    matchup_avg_fg_pct=0.45,
    matchup_diff_points=0.0,
    matchup_diff_rebounds=0.0,
    matchup_diff_assists=0.0,
    matchup_diff_fg_pct=0.0,
    matchup_games_played=5,
    games_available_20=20,
    minutes_avg=30.0,
    true_shooting_pct=0.55,
    usage_rate=0.25,
    team_pace=100.0,
    team_offensive_rating=110.0,
    offensive_rebounds_avg=1.5,
):
    """Build a full feature dict with sensible defaults."""
    return {
        # Points rolling
        "points_avg_5": points_avg + random.uniform(-2, 2),
        "points_avg_10": points_avg + random.uniform(-1, 1),
        "points_avg_20": points_avg,
        # Rebounds rolling
        "rebounds_avg_5": rebounds_avg + random.uniform(-1, 1),
        "rebounds_avg_10": rebounds_avg + random.uniform(-0.5, 0.5),
        "rebounds_avg_20": rebounds_avg,
        # Assists rolling
        "assists_avg_5": assists_avg + random.uniform(-1, 1),
        "assists_avg_10": assists_avg + random.uniform(-0.5, 0.5),
        "assists_avg_20": assists_avg,
        # FG3 pct rolling
        "fg3_pct_avg_5": fg3_pct_avg + random.uniform(-0.05, 0.05),
        "fg3_pct_avg_10": fg3_pct_avg + random.uniform(-0.03, 0.03),
        "fg3_pct_avg_20": fg3_pct_avg,
        # FG pct rolling
        "fg_pct_avg_5": 0.45 + random.uniform(-0.03, 0.03),
        # Minutes
        "minutes_avg_5": minutes_avg + random.uniform(-2, 2),
        "minutes_avg_10": minutes_avg + random.uniform(-1, 1),
        # Advanced
        "true_shooting_pct": true_shooting_pct,
        "usage_rate": usage_rate,
        # Offensive rebounds
        "offensive_rebounds_avg_5": offensive_rebounds_avg + random.uniform(-0.5, 0.5),
        "offensive_rebounds_avg_10": offensive_rebounds_avg,
        # Matchup stats
        "matchup_avg_points": matchup_avg_points,
        "matchup_avg_rebounds": matchup_avg_rebounds,
        "matchup_avg_assists": matchup_avg_assists,
        "matchup_avg_fg_pct": matchup_avg_fg_pct,
        "matchup_diff_points": matchup_diff_points,
        "matchup_diff_rebounds": matchup_diff_rebounds,
        "matchup_diff_assists": matchup_diff_assists,
        "matchup_diff_fg_pct": matchup_diff_fg_pct,
        "matchup_games_played": matchup_games_played,
        # Team features
        "team_pace": team_pace,
        "team_offensive_rating": team_offensive_rating,
        # Games available
        "games_available_20": games_available_20,
    }


def _generate_training_data(n=60, stat_type="points"):
    """Generate n synthetic training samples with correlated targets."""
    random.seed(42)
    features_list = []
    targets = []

    for _ in range(n):
        pts = random.uniform(10, 35)
        reb = random.uniform(2, 12)
        ast = random.uniform(1, 10)
        fg3 = random.uniform(0.25, 0.45)
        matchup_pts = random.uniform(10, 35)
        matchup_reb = random.uniform(2, 12)
        matchup_ast = random.uniform(1, 10)
        matchup_fg_pct = random.uniform(0.40, 0.55)

        feat = _make_feature_dict(
            points_avg=pts,
            rebounds_avg=reb,
            assists_avg=ast,
            fg3_pct_avg=fg3,
            matchup_avg_points=matchup_pts,
            matchup_avg_rebounds=matchup_reb,
            matchup_avg_assists=matchup_ast,
            matchup_avg_fg_pct=matchup_fg_pct,
            matchup_diff_points=matchup_pts - pts,
            matchup_diff_rebounds=matchup_reb - reb,
            matchup_diff_assists=matchup_ast - ast,
            matchup_diff_fg_pct=matchup_fg_pct - 0.45,
            matchup_games_played=random.randint(1, 10),
            games_available_20=20,
        )
        features_list.append(feat)

        # Target correlates with rolling averages + matchup influence
        if stat_type == "points":
            target = pts * 0.7 + matchup_pts * 0.3 + random.uniform(-3, 3)
        elif stat_type == "rebounds":
            target = reb * 0.7 + matchup_reb * 0.3 + random.uniform(-1.5, 1.5)
        elif stat_type == "assists":
            target = ast * 0.7 + matchup_ast * 0.3 + random.uniform(-1.5, 1.5)
        elif stat_type == "fg3m":
            # 3PM correlates with fg3 pct and minutes
            target = fg3 * 20 + random.uniform(-1, 1)  # ~5-9 range
        else:
            target = pts
        targets.append(target)

    return features_list, targets


class TestPlayerPropPredictor:
    """Tests for individual stat predictor."""

    def test_points_predictor_trains_and_predicts(self):
        """Test 1: PlayerPropPredictor('points') trains and predicts with quantile CI."""
        model = PlayerPropPredictor("points")
        features, targets = _generate_training_data(60, "points")
        model.train(features, targets)

        result = model.predict(features[0])
        assert isinstance(result, PredictionResult)
        assert result.confidence_lower <= result.value <= result.confidence_upper
        assert result.metadata["stat_type"] == "points"
        assert result.metadata["interval_pct"] == 90

    def test_rebounds_predictor(self):
        """Test 2: PlayerPropPredictor('rebounds') trains and predicts rebounds."""
        model = PlayerPropPredictor("rebounds")
        features, targets = _generate_training_data(60, "rebounds")
        model.train(features, targets)

        result = model.predict(features[0])
        assert isinstance(result, PredictionResult)
        assert result.confidence_lower <= result.value <= result.confidence_upper
        assert result.metadata["stat_type"] == "rebounds"

    def test_assists_predictor(self):
        """Test 3: PlayerPropPredictor('assists') trains and predicts assists."""
        model = PlayerPropPredictor("assists")
        features, targets = _generate_training_data(60, "assists")
        model.train(features, targets)

        result = model.predict(features[0])
        assert isinstance(result, PredictionResult)
        assert result.metadata["stat_type"] == "assists"

    def test_fg3m_predictor(self):
        """Test 4: PlayerPropPredictor('fg3m') trains and predicts 3PM."""
        model = PlayerPropPredictor("fg3m")
        features, targets = _generate_training_data(60, "fg3m")
        model.train(features, targets)

        result = model.predict(features[0])
        assert isinstance(result, PredictionResult)
        assert result.metadata["stat_type"] == "fg3m"

    def test_matchup_influence_on_points(self):
        """Test 5: High matchup_avg_points leads to higher predicted points."""
        model = PlayerPropPredictor("points")

        # Train with data where matchup correlates with outcome
        random.seed(99)
        features_list = []
        targets = []
        for _ in range(80):
            matchup_pts = random.uniform(15, 35)
            base_pts = 22.0  # Hold base constant
            feat = _make_feature_dict(
                points_avg=base_pts,
                matchup_avg_points=matchup_pts,
                matchup_diff_points=matchup_pts - base_pts,
                matchup_games_played=5,
                games_available_20=20,
            )
            features_list.append(feat)
            # Target strongly correlated with matchup
            targets.append(base_pts * 0.5 + matchup_pts * 0.5 + random.uniform(-2, 2))

        model.train(features_list, targets)

        # Predict with high vs low matchup
        high_matchup = _make_feature_dict(
            points_avg=22.0,
            matchup_avg_points=32.0,
            matchup_diff_points=10.0,
            matchup_games_played=5,
            games_available_20=20,
        )
        low_matchup = _make_feature_dict(
            points_avg=22.0,
            matchup_avg_points=12.0,
            matchup_diff_points=-10.0,
            matchup_games_played=5,
            games_available_20=20,
        )

        pred_high = model.predict(high_matchup)
        pred_low = model.predict(low_matchup)
        assert pred_high.value > pred_low.value, (
            f"High matchup ({pred_high.value}) should exceed low matchup ({pred_low.value})"
        )

    def test_missing_matchup_data(self):
        """Test 6: matchup_games_played=0 or None still produces valid predictions."""
        model = PlayerPropPredictor("points")
        features, targets = _generate_training_data(60, "points")
        model.train(features, targets)

        # Test with matchup_games_played = 0
        feat_zero = _make_feature_dict(
            matchup_games_played=0,
            matchup_avg_points=0,
            matchup_diff_points=0,
            games_available_20=20,
        )
        result_zero = model.predict(feat_zero)
        assert isinstance(result_zero, PredictionResult)
        assert math.isfinite(result_zero.value)

        # Test with matchup_games_played = None
        feat_none = _make_feature_dict(
            matchup_games_played=None,
            matchup_avg_points=None,
            matchup_diff_points=None,
            games_available_20=20,
        )
        result_none = model.predict(feat_none)
        assert isinstance(result_none, PredictionResult)
        assert math.isfinite(result_none.value)

    def test_wider_ci_with_sparse_data(self):
        """Test 8: Confidence intervals widen when games_available_20 is low."""
        model = PlayerPropPredictor("points")
        features, targets = _generate_training_data(60, "points")
        model.train(features, targets)

        feat_full = _make_feature_dict(games_available_20=20, points_avg=22.0)
        feat_sparse = _make_feature_dict(games_available_20=5, points_avg=22.0)

        result_full = model.predict(feat_full)
        result_sparse = model.predict(feat_sparse)

        width_full = result_full.confidence_upper - result_full.confidence_lower
        width_sparse = result_sparse.confidence_upper - result_sparse.confidence_lower
        assert width_sparse > width_full, (
            f"Sparse CI width ({width_sparse}) should exceed full CI width ({width_full})"
        )


class TestPlayerPropsPredictor:
    """Tests for the multi-stat wrapper."""

    def test_predict_all_returns_all_stats(self):
        """Test 7: predict_all returns dict of {stat_name: PredictionResult} for all 4 stats."""
        multi = PlayerPropsPredictor()

        # Train each stat type
        for stat in ["points", "rebounds", "assists", "fg3m"]:
            features, targets = _generate_training_data(60, stat)
            multi.predictors[stat].train(features, targets)

        feat = _make_feature_dict()
        results = multi.predict_all(feat)

        assert set(results.keys()) == {"points", "rebounds", "assists", "fg3m"}
        for stat_name, result in results.items():
            assert isinstance(result, PredictionResult)
            assert result.metadata["stat_type"] == stat_name

    def test_train_all(self):
        """train_all trains all 4 predictors from a single targets_dict."""
        multi = PlayerPropsPredictor()

        targets_dict = {}
        all_features = []
        for stat in ["points", "rebounds", "assists", "fg3m"]:
            features, targets = _generate_training_data(60, stat)
            targets_dict[stat] = targets
            if not all_features:
                all_features = features

        multi.train_all(all_features, targets_dict)

        feat = _make_feature_dict()
        results = multi.predict_all(feat)
        assert len(results) == 4
        for result in results.values():
            assert isinstance(result, PredictionResult)

    def test_save_load_roundtrip(self):
        """save/load preserves all 4 trained models."""
        import tempfile
        import os

        multi = PlayerPropsPredictor()
        for stat in ["points", "rebounds", "assists", "fg3m"]:
            features, targets = _generate_training_data(60, stat)
            multi.predictors[stat].train(features, targets)

        with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as f:
            path = f.name

        try:
            multi.save(path)
            loaded = PlayerPropsPredictor.load(path)

            feat = _make_feature_dict()
            orig_results = multi.predict_all(feat)
            loaded_results = loaded.predict_all(feat)

            for stat in ["points", "rebounds", "assists", "fg3m"]:
                assert abs(orig_results[stat].value - loaded_results[stat].value) < 0.01
        finally:
            os.unlink(path)
