"""Feature query API for Phase 3 consumption.

Provides get_features() which returns all features for a player on a given
date as a flat dict, ready for model input.
"""

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from sportsprediction.data.models import (
    PlayerRollingStats,
    PlayerAdvancedStats,
    MatchupStats,
    TeamFeatures,
    BoxScore,
    Game,
)


def get_features(
    session: Session,
    player_id: int,
    game_date: date,
    game_id: Optional[str] = None,
) -> Optional[dict]:
    """Return all features for a player on a given date as a flat dict.

    JOINs across PlayerRollingStats, PlayerAdvancedStats, MatchupStats.
    Also returns team features for the player's team for that game.

    Args:
        session: SQLAlchemy session.
        player_id: Player to query.
        game_date: Date of the game.
        game_id: Optional specific game ID. If None, finds the game by date.

    Returns:
        Flat dict with all feature columns, or None if no features exist.
    """
    # Resolve game_id if not provided
    if game_id is None:
        # Find the game this player played on this date
        result = (
            session.query(BoxScore.game_id)
            .join(Game, BoxScore.game_id == Game.game_id)
            .filter(
                BoxScore.player_id == player_id,
                Game.game_date == game_date,
            )
            .first()
        )
        if result is None:
            return None
        game_id = result.game_id

    features: dict = {}

    # 1. Rolling stats
    rolling = session.query(PlayerRollingStats).filter_by(
        player_id=player_id, game_id=game_id
    ).first()

    if rolling is None:
        return None  # No features computed yet

    # Extract rolling stat columns (skip metadata columns)
    rolling_skip = {"id", "player_id", "game_id", "game_date"}
    for col in PlayerRollingStats.__table__.columns:
        if col.name not in rolling_skip:
            features[col.name] = getattr(rolling, col.name)

    # 2. Advanced stats
    advanced = session.query(PlayerAdvancedStats).filter_by(
        player_id=player_id, game_id=game_id
    ).first()

    if advanced:
        advanced_skip = {"id", "player_id", "game_id", "game_date"}
        for col in PlayerAdvancedStats.__table__.columns:
            if col.name not in advanced_skip:
                features[col.name] = getattr(advanced, col.name)

    # 3. Matchup stats
    matchup = session.query(MatchupStats).filter_by(
        player_id=player_id, game_id=game_id
    ).first()

    if matchup:
        matchup_skip = {"id", "player_id", "game_id", "game_date", "opponent_team_id"}
        for col in MatchupStats.__table__.columns:
            if col.name not in matchup_skip:
                features[col.name] = getattr(matchup, col.name)

    # 4. Team features (for the player's team in this game)
    box_score = session.query(BoxScore).filter_by(
        player_id=player_id, game_id=game_id
    ).first()

    if box_score:
        team_feat = session.query(TeamFeatures).filter_by(
            team_id=box_score.team_id, game_id=game_id
        ).first()

        if team_feat:
            team_prefix_cols = {
                "pace": "team_pace",
                "offensive_rating": "team_offensive_rating",
                "defensive_rating": "team_defensive_rating",
                "rest_days": "team_rest_days",
                "possessions": "team_possessions",
                "opponent_possessions": "team_opponent_possessions",
                "season_win_pct": "team_season_win_pct",
            }
            for model_col, feature_name in team_prefix_cols.items():
                features[feature_name] = getattr(team_feat, model_col)

    return features
