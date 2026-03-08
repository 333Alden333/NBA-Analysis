"""Over/under total prediction with quantile regression confidence interval."""

from typing import Optional

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor

from hermes.models.base_model import BasePredictor, PredictionResult
from hermes.models.game_predictor import GAME_FEATURE_COLS, _build_feature_names


class TotalsPredictor(BasePredictor):
    """Predicts game totals using quantile regression.

    Uses three GradientBoostingRegressors with quantile loss for
    native 90% prediction intervals WITHOUT normality assumption:
        - lower (5th percentile)
        - median (50th percentile)
        - upper (95th percentile)
    """

    # GBR hyperparameters per research findings
    _GBR_PARAMS = dict(
        loss="quantile",
        learning_rate=0.05,
        n_estimators=200,
        max_depth=2,
        min_samples_leaf=9,
        min_samples_split=9,
    )

    def __init__(self):
        self._model_lower: Optional[GradientBoostingRegressor] = None
        self._model_median: Optional[GradientBoostingRegressor] = None
        self._model_upper: Optional[GradientBoostingRegressor] = None
        self._feature_names: list[str] = _build_feature_names()

    def get_feature_names(self) -> list[str]:
        """Return the 16 feature names used by this model."""
        return list(self._feature_names)

    @classmethod
    def build_game_features(cls, session, game) -> Optional[dict]:
        """Build feature dict from TeamFeatures for a game.

        Same aggregation as GamePredictor: home_X, away_X, diff_X + is_home.
        Returns None if either team's features are missing.
        """
        from hermes.data.models.team_features import TeamFeatures

        home_tf = session.query(TeamFeatures).filter_by(
            game_id=game.game_id, team_id=game.home_team_id
        ).first()
        away_tf = session.query(TeamFeatures).filter_by(
            game_id=game.game_id, team_id=game.away_team_id
        ).first()

        if home_tf is None or away_tf is None:
            return None

        features = {}
        for col in GAME_FEATURE_COLS:
            home_val = getattr(home_tf, col, None)
            away_val = getattr(away_tf, col, None)
            h = float(home_val) if home_val is not None else 0.0
            a = float(away_val) if away_val is not None else 0.0
            features[f"home_{col}"] = h
            features[f"away_{col}"] = a
            features[f"diff_{col}"] = h - a

        features["is_home"] = 1.0
        return features

    def train(self, features: list[dict], targets: list[float]) -> None:
        """Train three quantile GBR models (5th, 50th, 95th percentiles).

        Args:
            features: List of game feature dicts.
            targets: List of total scores (home + away).
        """
        X = np.array(
            [self.features_to_array(f, self._feature_names) for f in features]
        )
        y = np.array(targets)

        self._model_lower = GradientBoostingRegressor(
            alpha=0.05, **self._GBR_PARAMS
        )
        self._model_median = GradientBoostingRegressor(
            alpha=0.5, **self._GBR_PARAMS
        )
        self._model_upper = GradientBoostingRegressor(
            alpha=0.95, **self._GBR_PARAMS
        )

        self._model_lower.fit(X, y)
        self._model_median.fit(X, y)
        self._model_upper.fit(X, y)

    def predict(self, features: dict) -> PredictionResult:
        """Predict game total with quantile regression CI.

        Returns PredictionResult where:
            value = median model prediction (50th percentile)
            confidence_lower = lower model (5th percentile)
            confidence_upper = upper model (95th percentile)
            metadata = {interval_pct: 90}
        """
        if self._model_median is None:
            raise RuntimeError("Model not trained. Call train() first.")

        X = np.array(
            [self.features_to_array(features, self._feature_names)]
        )

        lower = float(self._model_lower.predict(X)[0])
        median = float(self._model_median.predict(X)[0])
        upper = float(self._model_upper.predict(X)[0])

        # Ensure quantile ordering (can rarely cross with small data)
        if lower > median:
            lower = median
        if upper < median:
            upper = median

        return PredictionResult(
            value=median,
            confidence_lower=lower,
            confidence_upper=upper,
            metadata={"interval_pct": 90},
        )
