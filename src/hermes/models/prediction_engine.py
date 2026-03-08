"""PredictionEngine -- orchestrates prediction generation and DB storage."""

import json
import logging
import os
from datetime import date

from sqlalchemy.orm import Session

from hermes.data.models.prediction import Prediction
from hermes.data.features.api import get_features
from hermes.models.base_model import PredictionResult
from hermes.models.game_predictor import GamePredictor
from hermes.models.totals_predictor import TotalsPredictor
from hermes.models.player_predictor import PlayerPropsPredictor

logger = logging.getLogger(__name__)


class PredictionEngine:
    """Orchestrates prediction generation for games and stores results to DB."""

    def __init__(self, session: Session, models_dir: str = "data/models/"):
        self._session = session
        self._models_dir = models_dir

        # Load model version
        version_path = os.path.join(models_dir, "version.txt")
        if os.path.exists(version_path):
            with open(version_path) as f:
                self._model_version = f.read().strip()
        else:
            self._model_version = f"v{date.today().isoformat()}"

        # Load models
        gp_path = os.path.join(models_dir, "game_predictor.joblib")
        tp_path = os.path.join(models_dir, "totals_predictor.joblib")
        pp_path = os.path.join(models_dir, "player_props.joblib")

        if not os.path.exists(gp_path):
            raise FileNotFoundError(
                f"Game predictor model not found at {gp_path}. "
                "Run `hermes predict --train` first."
            )

        self._game_predictor = GamePredictor.load(gp_path)
        self._totals_predictor = TotalsPredictor.load(tp_path)
        self._player_props = PlayerPropsPredictor.load(pp_path) if os.path.exists(pp_path) else None

    def predict_game(self, game) -> list:
        """Generate game_winner, game_spread, game_total predictions and store to DB."""
        features = GamePredictor.build_game_features(self._session, game)
        if features is None:
            logger.warning("No features for game %s, skipping", game.game_id)
            return []

        game_result = self._game_predictor.predict(features)
        totals_result = self._totals_predictor.predict(features)

        predictions = []

        # game_winner: 1 = home win, 0 = away win
        win_prob = game_result.metadata.get("win_probability", 0.5)
        predicted_winner = 1.0 if win_prob > 0.5 else 0.0

        winner_pred = Prediction(
            game_id=game.game_id,
            prediction_type="game_winner",
            predicted_value=predicted_winner,
            win_probability=win_prob,
            confidence_lower=None,
            confidence_upper=None,
            model_version=self._model_version,
            metadata_json=json.dumps(game_result.metadata),
        )
        self._session.add(winner_pred)
        predictions.append(winner_pred)

        # game_spread
        spread_pred = Prediction(
            game_id=game.game_id,
            prediction_type="game_spread",
            predicted_value=game_result.value,
            confidence_lower=game_result.confidence_lower,
            confidence_upper=game_result.confidence_upper,
            model_version=self._model_version,
            metadata_json=json.dumps(game_result.metadata),
        )
        self._session.add(spread_pred)
        predictions.append(spread_pred)

        # game_total
        total_pred = Prediction(
            game_id=game.game_id,
            prediction_type="game_total",
            predicted_value=totals_result.value,
            confidence_lower=totals_result.confidence_lower,
            confidence_upper=totals_result.confidence_upper,
            model_version=self._model_version,
            metadata_json=json.dumps(totals_result.metadata),
        )
        self._session.add(total_pred)
        predictions.append(total_pred)

        self._session.flush()
        return predictions

    def predict_player_props(self, game, player_id: int) -> list:
        """Generate player prop predictions and store to DB."""
        if self._player_props is None:
            logger.warning("Player props model not loaded, skipping")
            return []

        features = get_features(
            self._session, player_id, game.game_date, game_id=game.game_id
        )
        if features is None:
            logger.debug("No features for player %s game %s", player_id, game.game_id)
            return []

        results = self._player_props.predict_all(features)

        type_map = {
            "points": "player_points",
            "rebounds": "player_rebounds",
            "assists": "player_assists",
            "fg3m": "player_3pm",
        }

        predictions = []
        for stat_type, result in results.items():
            pred_type = type_map.get(stat_type, f"player_{stat_type}")
            pred = Prediction(
                game_id=game.game_id,
                prediction_type=pred_type,
                player_id=player_id,
                predicted_value=result.value,
                confidence_lower=result.confidence_lower,
                confidence_upper=result.confidence_upper,
                model_version=self._model_version,
                metadata_json=json.dumps(result.metadata),
            )
            self._session.add(pred)
            predictions.append(pred)

        self._session.flush()
        return predictions

    def predict_today(self) -> dict:
        """Find today's games and generate predictions for all.

        Returns summary dict with counts.
        """
        from hermes.data.models.game import Game
        from hermes.data.models.box_score import BoxScore

        today = date.today()
        games = (
            self._session.query(Game)
            .filter(Game.game_date == today, Game.status != "Final")
            .all()
        )

        game_count = 0
        player_count = 0

        for game in games:
            game_preds = self.predict_game(game)
            if game_preds:
                game_count += 1

            # Find players via recent box scores for this game's teams
            player_ids = set()
            for team_id in [game.home_team_id, game.away_team_id]:
                recent = (
                    self._session.query(BoxScore.player_id)
                    .filter_by(team_id=team_id)
                    .distinct()
                    .all()
                )
                for (pid,) in recent:
                    player_ids.add(pid)

            for pid in player_ids:
                props = self.predict_player_props(game, pid)
                if props:
                    player_count += 1

        self._session.commit()

        return {
            "games_predicted": game_count,
            "players_predicted": player_count,
            "date": str(today),
        }
