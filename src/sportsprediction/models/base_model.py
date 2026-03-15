"""Base predictor ABC and PredictionResult dataclass."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

import joblib


@dataclass
class PredictionResult:
    """Result of a single prediction with confidence interval."""

    value: float
    confidence_lower: float
    confidence_upper: float
    metadata: dict = field(default_factory=dict)


class BasePredictor(ABC):
    """Abstract base class for all prediction models.

    Subclasses must implement train(), predict(), and get_feature_names().
    Provides save/load via joblib, cross_validate via sklearn, and
    a static features_to_array helper.
    """

    @abstractmethod
    def train(self, features: list[dict], targets: list[float]) -> None:
        """Train the model on feature dicts and target values."""
        ...

    @abstractmethod
    def predict(self, features: dict) -> PredictionResult:
        """Predict a single outcome from a feature dict."""
        ...

    @abstractmethod
    def get_feature_names(self) -> list[str]:
        """Return the ordered list of feature names the model expects."""
        ...

    def save(self, path: str) -> None:
        """Serialize the model to disk using joblib."""
        joblib.dump(self, path)

    @classmethod
    def load(cls, path: str) -> "BasePredictor":
        """Deserialize a model from disk."""
        return joblib.load(path)

    def cross_validate(
        self,
        features: list[dict],
        targets: list[float],
        cv: int = 5,
    ) -> dict:
        """Run cross-validation using sklearn and return score dict.

        Uses the model's feature_names to convert dicts to arrays.
        Returns dict with 'scores' (array of per-fold scores) and 'mean'.
        """
        from sklearn.model_selection import cross_val_score
        from sklearn.base import BaseEstimator, RegressorMixin
        import numpy as np

        feature_names = self.get_feature_names()
        X = np.array(
            [self.features_to_array(f, feature_names) for f in features]
        )
        y = np.array(targets)

        # Wrap self in a sklearn-compatible estimator for cross_val_score
        class _Wrapper(BaseEstimator, RegressorMixin):
            def __init__(self, predictor):
                self.predictor = predictor

            def fit(self, X, y):
                feat_dicts = [
                    dict(zip(feature_names, row)) for row in X
                ]
                self.predictor.train(feat_dicts, y.tolist())
                return self

            def predict(self, X):
                results = []
                for row in X:
                    feat_dict = dict(zip(feature_names, row))
                    results.append(self.predictor.predict(feat_dict).value)
                return np.array(results)

        wrapper = _Wrapper(self)
        scores = cross_val_score(wrapper, X, y, cv=cv, scoring="r2")
        return {"scores": scores, "mean": float(scores.mean())}

    @staticmethod
    def features_to_array(
        features: dict, feature_names: list[str]
    ) -> list[float]:
        """Convert a feature dict to an ordered float array.

        Missing keys are filled with 0.0. None values are coerced to 0.0.
        """
        result = []
        for name in feature_names:
            val = features.get(name)
            if val is None:
                result.append(0.0)
            else:
                result.append(float(val))
        return result
