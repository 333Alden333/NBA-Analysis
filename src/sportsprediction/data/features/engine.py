"""Feature computation orchestrator -- coordinates all four feature types.

Provides compute_all_features_for_games() for post-sync hooks and
backfill_features() for historical re-computation with checkpoint/resume.
"""

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from sportsprediction.data.features.rolling import compute_rolling_stats_for_games
from sportsprediction.data.features.advanced import compute_advanced_stats_for_games
from sportsprediction.data.features.matchup import compute_matchup_stats_for_games
from sportsprediction.data.features.team import compute_team_features_for_games
from sportsprediction.data.models import Game, SyncLog
from sportsprediction.config import settings

logger = logging.getLogger(__name__)

BACKFILL_BATCH_SIZE = 50


def compute_all_features_for_games(session: Session, game_ids: list) -> None:
    """Compute all four feature types for players/teams in the given games.

    Execution order: rolling -> advanced -> matchup -> team.
    Each module handles its own upsert logic internally.

    Args:
        session: SQLAlchemy session.
        game_ids: List of game IDs to compute features for.
    """
    if not game_ids:
        return

    logger.info("Computing features for %d games", len(game_ids))

    # 1. Rolling stats for all players in these games
    compute_rolling_stats_for_games(session, game_ids)
    logger.debug("Rolling stats complete for %d games", len(game_ids))

    # 2. Advanced stats for all players
    compute_advanced_stats_for_games(session, game_ids)
    logger.debug("Advanced stats complete for %d games", len(game_ids))

    # 3. Matchup stats for all players
    compute_matchup_stats_for_games(session, game_ids)
    logger.debug("Matchup stats complete for %d games", len(game_ids))

    # 4. Team features for all teams
    compute_team_features_for_games(session, game_ids)
    logger.debug("Team features complete for %d games", len(game_ids))

    session.commit()
    logger.info("Feature computation complete for %d games", len(game_ids))


def backfill_features(session: Session, seasons: list[str] | None = None) -> dict[str, int]:
    """Backfill features for all historical games, with checkpoint/resume.

    Processes games by season, ordered by date, in batches of 50.
    Uses SyncLog with entity_type='feature_backfill' for checkpoint/resume.

    Args:
        session: SQLAlchemy session.
        seasons: List of season strings. Defaults to config.seasons.

    Returns:
        Dict with 'games_processed' and 'games_skipped' counts.
    """
    if seasons is None:
        seasons = settings.seasons

    total_processed = 0
    total_skipped = 0

    for season in seasons:
        logger.info("Backfilling features for season %s", season)

        # Get already-processed game IDs for this season
        processed_logs = (
            session.query(SyncLog)
            .filter_by(entity_type="feature_backfill", season=season)
            .all()
        )
        # Game IDs stored in status field as comma-separated for batch tracking
        processed_game_ids: set[str] = set()
        for log in processed_logs:
            if log.status and log.status.startswith("batch:"):
                # Extract game IDs from "batch:id1,id2,id3"
                ids_str = log.status[len("batch:"):]
                processed_game_ids.update(ids_str.split(","))

        # Get all games for this season, ordered by date
        all_games = (
            session.query(Game.game_id)
            .filter(Game.season == season)
            .order_by(Game.game_date.asc())
            .all()
        )
        all_game_ids = [g.game_id for g in all_games]

        # Filter out already-processed games
        remaining = [gid for gid in all_game_ids if gid not in processed_game_ids]
        total_skipped += len(all_game_ids) - len(remaining)

        logger.info(
            "Season %s: %d total games, %d remaining",
            season, len(all_game_ids), len(remaining),
        )

        # Process in batches
        for i in range(0, len(remaining), BACKFILL_BATCH_SIZE):
            batch = remaining[i:i + BACKFILL_BATCH_SIZE]

            compute_all_features_for_games(session, batch)

            # Record checkpoint
            session.add(SyncLog(
                entity_type="feature_backfill",
                last_sync_at=datetime.utcnow(),
                records_synced=len(batch),
                season=season,
                status=f"batch:{','.join(batch)}",
            ))
            session.commit()

            total_processed += len(batch)
            logger.info(
                "Backfill progress: %d/%d games for season %s",
                min(i + BACKFILL_BATCH_SIZE, len(remaining)),
                len(remaining),
                season,
            )

    logger.info(
        "Feature backfill complete. Processed: %d, Skipped (already done): %d",
        total_processed, total_skipped,
    )

    return {
        "games_processed": total_processed,
        "games_skipped": total_skipped,
    }
