"""Tests for BasePredictor abstract class and PredictionResult."""

import pytest
from statistics import mean

from sportsprediction.models.base_model import BasePredictor, PredictionResult


class DummyPredictor(BasePredictor):
    """Module-level DummyPredictor for pickle compatibility in save/load tests."""

    def __init__(self):
        self._mean = 0.0
        self._feature_names = []

    def train(self, features, targets):
        self._mean = mean(targets) if targets else 0.0
        if features:
            self._feature_names = sorted(features[0].keys())

    def predict(self, features):
        return PredictionResult(
            value=self._mean,
            confidence_lower=self._mean - 5.0,
            confidence_upper=self._mean + 5.0,
            metadata={},
        )

    def get_feature_names(self):
        return self._feature_names


class TestPredictionResult:
    """Tests for the PredictionResult dataclass."""

    def test_prediction_result_fields(self):
        """PredictionResult has value, confidence_lower, confidence_upper, metadata."""
        result = PredictionResult(
            value=25.5,
            confidence_lower=18.0,
            confidence_upper=33.0,
            metadata={"model": "dummy"},
        )
        assert result.value == 25.5
        assert result.confidence_lower == 18.0
        assert result.confidence_upper == 33.0
        assert result.metadata == {"model": "dummy"}

    def test_confidence_interval_valid(self):
        """Test 4: Confidence interval upper >= lower."""
        result = PredictionResult(
            value=10.0, confidence_lower=5.0, confidence_upper=15.0, metadata={}
        )
        assert result.confidence_upper >= result.confidence_lower


class TestBasePredictor:
    """Tests for the BasePredictor ABC."""

    def test_subclass_must_implement_abstract_methods(self):
        """Test 1: BasePredictor subclass must implement train(), predict(), get_feature_names()."""
        class IncompletePredictor(BasePredictor):
            pass

        with pytest.raises(TypeError, match="abstract method"):
            IncompletePredictor()

    def test_predict_returns_prediction_result(self):
        """Test 2: predict() returns a PredictionResult."""
        model = DummyPredictor()
        model.train(
            [{"pts": 20.0, "reb": 5.0}],
            [25.0],
        )
        result = model.predict({"pts": 22.0, "reb": 6.0})
        assert isinstance(result, PredictionResult)
        assert result.value == 25.0

    def test_dummy_predictor_train_and_predict(self):
        """Test 3: DummyPredictor trains on features/targets and predicts mean."""
        features = [
            {"pts": 20.0, "reb": 5.0, "ast": 3.0},
            {"pts": 30.0, "reb": 8.0, "ast": 7.0},
            {"pts": 25.0, "reb": 6.0, "ast": 5.0},
        ]
        targets = [20.0, 30.0, 25.0]

        model = DummyPredictor()
        model.train(features, targets)

        result = model.predict({"pts": 22.0, "reb": 7.0, "ast": 4.0})
        assert result.value == 25.0
        assert result.confidence_upper >= result.confidence_lower
        assert model.get_feature_names() == ["ast", "pts", "reb"]

    def test_save_load_roundtrip(self):
        """Test 5: Model can serialize/deserialize via joblib to a bytes buffer."""
        import tempfile
        import os

        model = DummyPredictor()
        model.train([{"a": 1.0, "b": 2.0}], [10.0])

        with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as f:
            path = f.name

        try:
            model.save(path)
            loaded = DummyPredictor.load(path)
            result = loaded.predict({"a": 1.0, "b": 2.0})
            assert result.value == 10.0
            assert loaded.get_feature_names() == ["a", "b"]
        finally:
            os.unlink(path)

    def test_features_to_array(self):
        """Test 6: features_to_array converts dict to ordered float array, fills missing with 0.0."""
        feature_names = ["ast", "pts", "reb"]
        features = {"pts": 25.0, "reb": 8.0}  # missing "ast"

        result = BasePredictor.features_to_array(features, feature_names)
        assert result == [0.0, 25.0, 8.0]

    def test_features_to_array_coerces_none(self):
        """features_to_array coerces None values to 0.0."""
        feature_names = ["a", "b"]
        features = {"a": None, "b": 5.0}

        result = BasePredictor.features_to_array(features, feature_names)
        assert result == [0.0, 5.0]
