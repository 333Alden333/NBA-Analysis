"""Training pipeline -- build feature/target arrays from historical data and train models."""

import logging
import os
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from sportsprediction.models.game_predictor import GamePredictor
from sportsprediction.models.totals_predictor import TotalsPredictor
from sportsprediction.models.player_predictor import PlayerPropsPredictor

logger = logging.getLogger(__name__)


def build_game_training_data(session: Session, seasons: Optional[list[str]] = None) -> dict:
    """Query completed games and build feature/target arrays for game models.

    Returns:
        dict with keys: game_features, spread_targets, total_targets
    """
    from sportsprediction.data.models.game import Game

    query = session.query(Game).filter(Game.status == "Final")
    if seasons:
        query = query.filter(Game.season.in_(seasons))

    games = query.all()
    game_features = []
    spread_targets = []
    total_targets = []

    for game in games:
        if game.home_score is None or game.away_score is None:
            continue

        features = GamePredictor.build_game_features(session, game)
        if features is None:
            continue

        spread = game.home_score - game.away_score
        total = game.home_score + game.away_score

        game_features.append(features)
        spread_targets.append(float(spread))
        total_targets.append(float(total))

    logger.info("Built game training data: %d samples", len(game_features))
    return {
        "game_features": game_features,
        "spread_targets": spread_targets,
        "total_targets": total_targets,
    }


def build_player_training_data(session: Session, seasons: Optional[list[str]] = None) -> dict:
    """Query box scores for completed games and build player training data.

    Returns:
        dict with keys: features (list of dicts), targets (dict of stat->list)
    """
    from sportsprediction.data.models.game import Game
    from sportsprediction.data.models.box_score import BoxScore
    from sportsprediction.data.features.api import get_features

    query = (
        session.query(BoxScore)
        .join(Game, BoxScore.game_id == Game.game_id)
        .filter(Game.status == "Final")
    )
    if seasons:
        query = query.filter(Game.season.in_(seasons))

    box_scores = query.all()
    features_list = []
    targets = {"points": [], "rebounds": [], "assists": [], "fg3m": []}

    for bs in box_scores:
        game = session.query(Game).filter_by(game_id=bs.game_id).first()
        if game is None or game.game_date is None:
            continue

        feats = get_features(session, bs.player_id, game.game_date, game_id=bs.game_id)
        if feats is None:
            continue

        features_list.append(feats)
        targets["points"].append(float(bs.points or 0))
        targets["rebounds"].append(float(bs.rebounds or 0))
        targets["assists"].append(float(bs.assists or 0))
        targets["fg3m"].append(float(bs.fg3m or 0))

    logger.info("Built player training data: %d samples", len(features_list))
    return {
        "features": features_list,
        "targets": targets,
    }


def train_all_models(
    session: Session,
    seasons: Optional[list[str]] = None,
    models_dir: str = "data/models/",
) -> dict:
    """Train all prediction models and save to disk.

    Returns:
        dict of model name -> model instance
    """
    os.makedirs(models_dir, exist_ok=True)

    model_version = f"v{date.today().isoformat()}"

    # Game models
    game_data = build_game_training_data(session, seasons)
    game_predictor = GamePredictor()
    totals_predictor = TotalsPredictor()

    if game_data["game_features"]:
        game_predictor.train(game_data["game_features"], game_data["spread_targets"])
        totals_predictor.train(game_data["game_features"], game_data["total_targets"])
        game_predictor.save(os.path.join(models_dir, "game_predictor.joblib"))
        totals_predictor.save(os.path.join(models_dir, "totals_predictor.joblib"))
        logger.info("Trained game models on %d samples", len(game_data["game_features"]))
    else:
        logger.warning("No game training data available")

    # Player models
    player_data = build_player_training_data(session, seasons)
    player_props = PlayerPropsPredictor()

    if player_data["features"]:
        player_props.train_all(player_data["features"], player_data["targets"])
        player_props.save(os.path.join(models_dir, "player_props.joblib"))
        logger.info("Trained player models on %d samples", len(player_data["features"]))
    else:
        logger.warning("No player training data available")

    # Write version file
    with open(os.path.join(models_dir, "version.txt"), "w") as f:
        f.write(model_version)

    return {
        "game_predictor": game_predictor,
        "totals_predictor": totals_predictor,
        "player_props": player_props,
        "model_version": model_version,
        "game_samples": len(game_data["game_features"]),
        "player_samples": len(player_data["features"]),
    }
