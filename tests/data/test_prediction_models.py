"""Tests for Prediction and PredictionOutcome models."""

import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError


class TestPredictionModel:
    """Tests for the Prediction model."""

    def test_create_prediction_with_all_fields(self, session):
        """Test 1: Prediction model can be created with all required fields."""
        from hermes.data.models.prediction import Prediction
        from hermes.data.models import Game, Team, Player

        # Create prerequisite records
        team = Team(team_id=1, full_name="Test Team", abbreviation="TST")
        session.add(team)
        session.flush()

        player = Player(player_id=201, full_name="Test Player", team_id=1)
        session.add(player)
        session.flush()

        game = Game(game_id="0022400001", home_team_id=1, away_team_id=1)
        session.add(game)
        session.flush()

        pred = Prediction(
            game_id="0022400001",
            prediction_type="player_points",
            player_id=201,
            predicted_value=25.5,
            confidence_lower=18.0,
            confidence_upper=33.0,
            model_version="v0.1.0",
        )
        session.add(pred)
        session.flush()

        assert pred.id is not None
        assert pred.game_id == "0022400001"
        assert pred.prediction_type == "player_points"
        assert pred.predicted_value == 25.5
        assert pred.confidence_lower == 18.0
        assert pred.confidence_upper == 33.0
        assert pred.model_version == "v0.1.0"
        assert pred.created_at is not None

    def test_create_prediction_outcome(self, session):
        """Test 2: PredictionOutcome links to Prediction via FK."""
        from hermes.data.models.prediction import Prediction, PredictionOutcome
        from hermes.data.models import Game, Team

        team = Team(team_id=1, full_name="Test Team", abbreviation="TST")
        session.add(team)
        session.flush()

        game = Game(game_id="0022400001", home_team_id=1, away_team_id=1)
        session.add(game)
        session.flush()

        pred = Prediction(
            game_id="0022400001",
            prediction_type="game_winner",
            predicted_value=1.0,
            win_probability=0.72,
            model_version="v0.1.0",
        )
        session.add(pred)
        session.flush()

        outcome = PredictionOutcome(
            prediction_id=pred.id,
            actual_value=1.0,
            is_correct=1,
            resolved_at=datetime(2026, 3, 8, 22, 0, 0),
        )
        session.add(outcome)
        session.flush()

        assert outcome.id is not None
        assert outcome.prediction_id == pred.id
        assert outcome.actual_value == 1.0
        assert outcome.is_correct == 1

    def test_prediction_type_values(self, session):
        """Test 3: prediction_type covers all required types."""
        from hermes.data.models.prediction import Prediction
        from hermes.data.models import Game, Team, Player

        team = Team(team_id=1, full_name="Test Team", abbreviation="TST")
        session.add(team)
        session.flush()

        player = Player(player_id=201, full_name="Test Player", team_id=1)
        session.add(player)
        session.flush()

        game = Game(game_id="0022400001", home_team_id=1, away_team_id=1)
        session.add(game)
        session.flush()

        valid_types = [
            "game_winner", "game_spread", "game_total",
            "player_points", "player_rebounds", "player_assists", "player_3pm",
        ]

        for i, pred_type in enumerate(valid_types):
            player_id = 201 if pred_type.startswith("player_") else None
            pred = Prediction(
                game_id="0022400001",
                prediction_type=pred_type,
                player_id=player_id,
                predicted_value=float(i),
                model_version=f"v0.{i}.0",
                confidence_lower=0.0,
                confidence_upper=100.0,
            )
            session.add(pred)

        session.flush()

        from hermes.data.models.prediction import Prediction as P
        preds = session.query(P).all()
        stored_types = {p.prediction_type for p in preds}
        assert stored_types == set(valid_types)

    def test_unique_constraint_prevents_duplicates(self, session):
        """Test 4: Unique constraint on (game_id, prediction_type, player_id, model_version)."""
        from hermes.data.models.prediction import Prediction
        from hermes.data.models import Game, Team, Player

        team = Team(team_id=1, full_name="Test Team", abbreviation="TST")
        session.add(team)
        session.flush()

        player = Player(player_id=201, full_name="Test Player", team_id=1)
        session.add(player)
        session.flush()

        game = Game(game_id="0022400001", home_team_id=1, away_team_id=1)
        session.add(game)
        session.flush()

        pred1 = Prediction(
            game_id="0022400001",
            prediction_type="player_points",
            player_id=201,
            predicted_value=25.5,
            model_version="v0.1.0",
        )
        session.add(pred1)
        session.flush()

        pred2 = Prediction(
            game_id="0022400001",
            prediction_type="player_points",
            player_id=201,
            predicted_value=30.0,
            model_version="v0.1.0",
        )
        session.add(pred2)

        with pytest.raises(IntegrityError):
            session.flush()
