"""Outcome resolver -- backfills actual outcomes from completed games."""

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from hermes.data.models.game import Game
from hermes.data.models.box_score import BoxScore
from hermes.data.models.prediction import Prediction, PredictionOutcome

logger = logging.getLogger(__name__)

# Prediction type -> BoxScore stat column mapping
_PLAYER_STAT_MAP = {
    "player_points": "points",
    "player_rebounds": "rebounds",
    "player_assists": "assists",
    "player_3pm": "fg3m",
}


def resolve_outcomes(session: Session) -> int:
    """Resolve unresolved predictions by backfilling actual outcomes.

    Finds predictions that have no PredictionOutcome row, checks if the
    game is Final with non-null scores, and creates outcome rows.

    Returns:
        Count of newly resolved predictions.
    """
    # Find unresolved predictions (no PredictionOutcome yet)
    unresolved = (
        session.query(Prediction)
        .outerjoin(PredictionOutcome, Prediction.id == PredictionOutcome.prediction_id)
        .filter(PredictionOutcome.id.is_(None))
        .all()
    )

    resolved_count = 0

    for pred in unresolved:
        game = session.query(Game).filter_by(game_id=pred.game_id).first()
        if game is None:
            continue

        # Must be Final with non-null scores
        if game.status != "Final":
            continue
        if game.home_score is None or game.away_score is None:
            continue

        actual_value = None
        is_correct = None

        if pred.prediction_type == "game_winner":
            actual_value = 1.0 if game.home_score > game.away_score else 0.0
            is_correct = 1 if actual_value == round(pred.predicted_value) else 0

        elif pred.prediction_type == "game_spread":
            actual_value = float(game.home_score - game.away_score)
            # Correct if sign matches (both positive or both negative/zero)
            pred_sign = 1 if pred.predicted_value > 0 else (-1 if pred.predicted_value < 0 else 0)
            actual_sign = 1 if actual_value > 0 else (-1 if actual_value < 0 else 0)
            is_correct = 1 if pred_sign == actual_sign else 0

        elif pred.prediction_type == "game_total":
            actual_value = float(game.home_score + game.away_score)
            if pred.confidence_lower is not None and pred.confidence_upper is not None:
                is_correct = 1 if pred.confidence_lower <= actual_value <= pred.confidence_upper else 0
            else:
                is_correct = None

        elif pred.prediction_type in _PLAYER_STAT_MAP:
            stat_col = _PLAYER_STAT_MAP[pred.prediction_type]
            if pred.player_id is None:
                continue

            bs = (
                session.query(BoxScore)
                .filter_by(game_id=pred.game_id, player_id=pred.player_id)
                .first()
            )
            if bs is None:
                continue

            actual_value = float(getattr(bs, stat_col) or 0)
            if pred.confidence_lower is not None and pred.confidence_upper is not None:
                is_correct = 1 if pred.confidence_lower <= actual_value <= pred.confidence_upper else 0
            else:
                is_correct = None

        else:
            logger.warning("Unknown prediction type: %s", pred.prediction_type)
            continue

        if actual_value is not None:
            outcome = PredictionOutcome(
                prediction_id=pred.id,
                actual_value=actual_value,
                is_correct=is_correct,
                resolved_at=datetime.utcnow(),
            )
            session.add(outcome)
            resolved_count += 1

    session.commit()
    logger.info("Resolved %d predictions", resolved_count)
    return resolved_count
