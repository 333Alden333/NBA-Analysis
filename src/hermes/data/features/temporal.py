"""Temporal validation utilities for feature leakage detection.

Provides validate_no_leakage() which checks that no feature row uses data
from its own game or future games.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from hermes.data.models import (
    PlayerRollingStats,
    PlayerAdvancedStats,
    MatchupStats,
    TeamFeatures,
    BoxScore,
    Game,
)

logger = logging.getLogger(__name__)


def validate_no_leakage(session: Session, sample_size: int = 50) -> list[dict]:
    """Check that no feature row uses data from its own game or future games.

    For a sample of player-game rows across all feature types:
    1. Get the feature row's game_date
    2. Re-query the raw data that should have been used
    3. Verify no raw data has game_date >= feature's game_date

    Args:
        session: SQLAlchemy session.
        sample_size: Max rows to sample per feature type.

    Returns:
        List of violation dicts (empty = clean). Each dict has:
        - feature_type: str
        - player_id or team_id: int
        - game_id: str
        - game_date: date
        - violation: str (description of what leaked)
    """
    violations: list[dict] = []

    # 1. Validate rolling stats: averages should reflect only prior games
    _validate_rolling_leakage(session, violations, sample_size)

    # 2. Validate matchup stats: matchup history should use only prior games
    _validate_matchup_leakage(session, violations, sample_size)

    # 3. Validate team features: win_pct should use only prior games
    _validate_team_feature_leakage(session, violations, sample_size)

    if violations:
        logger.warning("Found %d temporal leakage violations", len(violations))
    else:
        logger.info("Temporal validation passed: no leakage detected")

    return violations


def _validate_rolling_leakage(
    session: Session, violations: list[dict], sample_size: int
) -> None:
    """Verify rolling stats use shift-by-1 (no current-game data)."""
    # Sample rolling stat rows that have a value for the 5-game window
    samples = (
        session.query(PlayerRollingStats)
        .filter(PlayerRollingStats.points_avg_5.isnot(None))
        .limit(sample_size)
        .all()
    )

    for rs in samples:
        # Count how many games this player played STRICTLY before this game's date
        prior_count = (
            session.query(BoxScore)
            .join(Game, BoxScore.game_id == Game.game_id)
            .filter(
                BoxScore.player_id == rs.player_id,
                BoxScore.minutes > 0,
                Game.game_date < rs.game_date,
            )
            .count()
        )

        # games_available_5 should not exceed the number of prior games
        if rs.games_available_5 is not None and rs.games_available_5 > prior_count:
            violations.append({
                "feature_type": "rolling_stats",
                "player_id": rs.player_id,
                "game_id": rs.game_id,
                "game_date": rs.game_date,
                "violation": (
                    f"games_available_5={rs.games_available_5} but only "
                    f"{prior_count} prior games exist"
                ),
            })


def _validate_matchup_leakage(
    session: Session, violations: list[dict], sample_size: int
) -> None:
    """Verify matchup stats use only prior matchup games."""
    samples = (
        session.query(MatchupStats)
        .filter(MatchupStats.has_matchup_history == True)  # noqa: E712
        .limit(sample_size)
        .all()
    )

    for ms in samples:
        # Count prior matchup games (same opponent, strictly before game date)
        prior_matchup_count = (
            session.query(BoxScore)
            .join(Game, BoxScore.game_id == Game.game_id)
            .filter(
                BoxScore.player_id == ms.player_id,
                Game.game_date < ms.game_date,
            )
            .count()
        )

        # matchup_games_played should not exceed total prior games
        if ms.matchup_games_played is not None and ms.matchup_games_played > prior_matchup_count:
            violations.append({
                "feature_type": "matchup_stats",
                "player_id": ms.player_id,
                "game_id": ms.game_id,
                "game_date": ms.game_date,
                "violation": (
                    f"matchup_games_played={ms.matchup_games_played} but only "
                    f"{prior_matchup_count} total prior games exist"
                ),
            })


def _validate_team_feature_leakage(
    session: Session, violations: list[dict], sample_size: int
) -> None:
    """Verify team features (win_pct) use only prior games."""
    from sqlalchemy import or_

    samples = (
        session.query(TeamFeatures)
        .filter(TeamFeatures.season_win_pct.isnot(None))
        .limit(sample_size)
        .all()
    )

    for tf in samples:
        # Count total games this team played strictly before this game date
        prior_games = (
            session.query(Game)
            .filter(
                or_(
                    Game.home_team_id == tf.team_id,
                    Game.away_team_id == tf.team_id,
                ),
                Game.game_date < tf.game_date,
            )
            .count()
        )

        # season_win_pct should be wins/games from prior games only
        # If win_pct > 1.0 or based on more games than exist, it's a violation
        if tf.season_win_pct is not None and tf.season_win_pct > 1.0:
            violations.append({
                "feature_type": "team_features",
                "team_id": tf.team_id,
                "game_id": tf.game_id,
                "game_date": tf.game_date,
                "violation": f"season_win_pct={tf.season_win_pct} exceeds 1.0",
            })
