"""Player prop prediction models with matchup context and quantile regression CIs."""

import math
from typing import Optional

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor

from hermes.models.base_model import BasePredictor, PredictionResult


# Feature sets per stat type -- only features that ACTUALLY exist in the feature dict.
# No matchup_avg_fg3m or matchup_diff_fg3m (they don't exist in MatchupStats).
PLAYER_FEATURES: dict[str, list[str]] = {
    "points": [
        "points_avg_5", "points_avg_10", "points_avg_20",
        "true_shooting_pct", "usage_rate",
        "minutes_avg_5", "minutes_avg_10",
        "matchup_avg_points", "matchup_diff_points", "matchup_games_played",
        "team_pace", "team_offensive_rating",
        "games_available_20",
    ],
    "rebounds": [
        "rebounds_avg_5", "rebounds_avg_10", "rebounds_avg_20",
        "offensive_rebounds_avg_5", "offensive_rebounds_avg_10",
        "minutes_avg_5", "minutes_avg_10",
        "matchup_avg_rebounds", "matchup_diff_rebounds", "matchup_games_played",
        "team_pace",
        "games_available_20",
    ],
    "assists": [
        "assists_avg_5", "assists_avg_10", "assists_avg_20",
        "usage_rate",
        "minutes_avg_5", "minutes_avg_10",
        "matchup_avg_assists", "matchup_diff_assists", "matchup_games_played",
        "team_pace", "team_offensive_rating",
        "games_available_20",
    ],
    "fg3m": [
        "fg3_pct_avg_5", "fg3_pct_avg_10", "fg3_pct_avg_20",
        "fg_pct_avg_5",
        "minutes_avg_5", "minutes_avg_10",
        "matchup_avg_fg_pct", "matchup_diff_fg_pct", "matchup_games_played",
        "team_pace",
        "games_available_20",
    ],
}

# Keys that are matchup-specific (zeroed when no matchup data)
_MATCHUP_KEYS = {
    "matchup_avg_points", "matchup_avg_rebounds", "matchup_avg_assists",
    "matchup_avg_fg_pct", "matchup_diff_points", "matchup_diff_rebounds",
    "matchup_diff_assists", "matchup_diff_fg_pct", "matchup_avg_plus_minus",
    "matchup_diff_plus_minus", "matchup_games_played",
}

# Shared GBR hyperparameters
_GBR_PARAMS = {
    "learning_rate": 0.05,
    "n_estimators": 200,
    "max_depth": 2,
    "min_samples_leaf": 9,
    "min_samples_split": 9,
}


class PlayerPropPredictor(BasePredictor):
    """Predicts a single player stat (points, rebounds, assists, or fg3m).

    Uses three GradientBoostingRegressors with quantile loss for
    lower (5th percentile), median (50th), and upper (95th) predictions.
    Incorporates matchup-specific history when available.
    """

    def __init__(self, stat_type: str) -> None:
        if stat_type not in PLAYER_FEATURES:
            raise ValueError(
                f"Unknown stat_type '{stat_type}'. "
                f"Must be one of: {list(PLAYER_FEATURES.keys())}"
            )
        self.stat_type = stat_type
        self._feature_names = PLAYER_FEATURES[stat_type]
        self._model_lower: Optional[GradientBoostingRegressor] = None
        self._model_median: Optional[GradientBoostingRegressor] = None
        self._model_upper: Optional[GradientBoostingRegressor] = None

    def get_feature_names(self) -> list[str]:
        return list(self._feature_names)

    def train(self, features: list[dict], targets: list[float]) -> None:
        """Train three quantile regressors (5th, 50th, 95th percentile)."""
        X = np.array(
            [self.features_to_array(f, self._feature_names) for f in features]
        )
        y = np.array(targets)

        self._model_lower = GradientBoostingRegressor(
            loss="quantile", alpha=0.05, **_GBR_PARAMS
        )
        self._model_median = GradientBoostingRegressor(
            loss="quantile", alpha=0.5, **_GBR_PARAMS
        )
        self._model_upper = GradientBoostingRegressor(
            loss="quantile", alpha=0.95, **_GBR_PARAMS
        )

        self._model_lower.fit(X, y)
        self._model_median.fit(X, y)
        self._model_upper.fit(X, y)

    def predict(self, features: dict) -> PredictionResult:
        """Predict stat value with quantile confidence interval.

        Handles missing matchup data by zeroing matchup features.
        Widens CI when games_available_20 < 10 (sparse data adjustment).
        """
        if self._model_median is None:
            raise RuntimeError("Model not trained. Call train() first.")

        # Zero out matchup features if no matchup history
        processed = dict(features)
        matchup_games = features.get("matchup_games_played")
        if matchup_games is None or matchup_games == 0:
            for key in _MATCHUP_KEYS:
                if key in processed:
                    processed[key] = 0.0

        X = np.array(
            [self.features_to_array(processed, self._feature_names)]
        )

        median_val = float(self._model_median.predict(X)[0])
        lower_val = float(self._model_lower.predict(X)[0])
        upper_val = float(self._model_upper.predict(X)[0])

        # Sparse data CI widening: sqrt(20 / games_available_20) multiplier
        games_avail = features.get("games_available_20")
        if games_avail is not None and 0 < games_avail < 10:
            width = upper_val - lower_val
            multiplier = math.sqrt(20.0 / games_avail)
            center = median_val
            half_new_width = (width * multiplier) / 2.0
            lower_val = center - half_new_width
            upper_val = center + half_new_width

        # Ensure ordering: lower <= median <= upper
        lower_val = min(lower_val, median_val)
        upper_val = max(upper_val, median_val)

        return PredictionResult(
            value=median_val,
            confidence_lower=lower_val,
            confidence_upper=upper_val,
            metadata={
                "stat_type": self.stat_type,
                "matchup_games": features.get("matchup_games_played", 0) or 0,
                "interval_pct": 90,
            },
        )


class PlayerPropsPredictor:
    """Wrapper that holds all four stat-type predictors.

    Provides train_all/predict_all for batch operations, and
    save/load for serializing all models together.
    """

    STAT_TYPES = ["points", "rebounds", "assists", "fg3m"]

    def __init__(self) -> None:
        self.predictors: dict[str, PlayerPropPredictor] = {
            stat: PlayerPropPredictor(stat) for stat in self.STAT_TYPES
        }

    def train_all(
        self,
        features_list: list[dict],
        targets_dict: dict[str, list[float]],
    ) -> None:
        """Train all four stat predictors.

        Args:
            features_list: List of feature dicts (shared across all stats).
            targets_dict: Maps stat_type to list of target values.
        """
        for stat in self.STAT_TYPES:
            if stat in targets_dict:
                self.predictors[stat].train(features_list, targets_dict[stat])

    def predict_all(self, features: dict) -> dict[str, PredictionResult]:
        """Run all four predictors on the same feature dict."""
        return {
            stat: predictor.predict(features)
            for stat, predictor in self.predictors.items()
        }

    def save(self, path: str) -> None:
        """Serialize all four models to disk."""
        joblib.dump(self, path)

    @classmethod
    def load(cls, path: str) -> "PlayerPropsPredictor":
        """Deserialize from disk."""
        return joblib.load(path)
