"""Game winner prediction with probability, spread, and confidence interval."""

from typing import Optional

import numpy as np
from sklearn.linear_model import LogisticRegression, Ridge

from sportsprediction.models.base_model import BasePredictor, PredictionResult


# TeamFeatures columns used for game-level prediction
GAME_FEATURE_COLS = [
    "pace",
    "offensive_rating",
    "defensive_rating",
    "rest_days",
    "season_win_pct",
]


def _build_feature_names() -> list[str]:
    """Generate the 16 feature names: home_X, away_X, diff_X for each col + is_home."""
    names = []
    for col in GAME_FEATURE_COLS:
        names.append(f"home_{col}")
        names.append(f"away_{col}")
        names.append(f"diff_{col}")
    names.append("is_home")
    return names


class GamePredictor(BasePredictor):
    """Predicts game winner (LogisticRegression) and spread (Ridge).

    Uses naturally calibrated LogisticRegression for win probability --
    no CalibratedClassifierCV needed. Ridge regression for point spread
    with residual-std confidence intervals.
    """

    def __init__(self):
        self._classifier: Optional[LogisticRegression] = None
        self._regressor: Optional[Ridge] = None
        self._residual_std: float = 0.0
        self._feature_names: list[str] = _build_feature_names()

    def get_feature_names(self) -> list[str]:
        """Return the 16 feature names used by this model."""
        return list(self._feature_names)

    @classmethod
    def build_game_features(cls, session, game) -> Optional[dict]:
        """Build feature dict from TeamFeatures for a game.

        Queries home and away TeamFeatures rows, builds home_X, away_X,
        diff_X for each GAME_FEATURE_COLS column, plus is_home=1.0.

        Returns None if either team's features are missing.
        """
        from sportsprediction.data.models.team_features import TeamFeatures

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
        """Train classifier (win/loss) and regressor (spread).

        Args:
            features: List of game feature dicts.
            targets: List of spreads (home_score - away_score).
        """
        X = np.array(
            [self.features_to_array(f, self._feature_names) for f in features]
        )
        y = np.array(targets)

        # Binary target: 1 if home wins (spread > 0), 0 otherwise
        y_binary = (y > 0).astype(int)

        # LogisticRegression -- naturally calibrated, no CalibratedClassifierCV
        self._classifier = LogisticRegression(max_iter=1000)
        self._classifier.fit(X, y_binary)

        # Ridge regression for point spread
        self._regressor = Ridge(alpha=1.0)
        self._regressor.fit(X, y)

        # Residual std for confidence interval
        predictions = self._regressor.predict(X)
        residuals = y - predictions
        self._residual_std = float(np.std(residuals))

    def predict(self, features: dict) -> PredictionResult:
        """Predict game outcome.

        Returns PredictionResult where:
            value = predicted spread (positive = home favored)
            confidence_lower/upper = spread +/- 1.96 * residual_std
            metadata = {win_probability, predicted_winner}
        """
        if self._classifier is None or self._regressor is None:
            raise RuntimeError("Model not trained. Call train() first.")

        X = np.array(
            [self.features_to_array(features, self._feature_names)]
        )

        spread = float(self._regressor.predict(X)[0])

        # Win probability from logistic regression
        proba = self._classifier.predict_proba(X)[0]
        # Index 1 = probability of class 1 (home win)
        win_prob = float(proba[1])

        ci_margin = 1.96 * self._residual_std

        return PredictionResult(
            value=spread,
            confidence_lower=spread - ci_margin,
            confidence_upper=spread + ci_margin,
            metadata={
                "win_probability": win_prob,
                "predicted_winner": "home" if win_prob > 0.5 else "away",
            },
        )
