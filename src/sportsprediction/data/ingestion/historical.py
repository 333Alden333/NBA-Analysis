"""Historical data loader with checkpoint/resume support."""

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from sportsprediction.data.adapters.base import NBADataAdapter
from sportsprediction.data.ingestion.game_sync import (
    sync_game_box_scores,
    sync_play_by_play,
    sync_shot_charts,
)
from sportsprediction.data.ingestion.team_sync import sync_teams
from sportsprediction.data.ingestion.player_sync import sync_players
from sportsprediction.data.models.sync_log import SyncLog
from sportsprediction.config import settings

logger = logging.getLogger(__name__)

BATCH_SIZE = 50


def _get_synced_game_ids(session: Session, season: str) -> set[str]:
    """Return set of game IDs already synced for a season."""
    logs = (
        session.query(SyncLog)
        .filter_by(entity_type="historical_game_detail")
        .all()
    )
    # game_id stored in the season field for per-game tracking
    return {log.season for log in logs if log.season}


def run_historical_load(
    adapter: NBADataAdapter,
    session: Session,
    seasons: list[str] | None = None,
) -> dict[str, int]:
    """Load historical NBA data for multiple seasons with checkpoint/resume.

    For each season: syncs teams first (FK dependency), fetches all game IDs,
    deduplicates, checks SyncLog for already-synced games, then processes
    remaining games in batches of 50.

    Args:
        adapter: NBA data adapter instance.
        session: SQLAlchemy session.
        seasons: List of seasons to load. Defaults to config.seasons.

    Returns:
        Dict mapping season to number of games processed.
    """
    if seasons is None:
        seasons = settings.seasons

    results: dict[str, int] = {}

    for season in seasons:
        logger.info("Starting historical load for season %s", season)

        # 1. Sync teams first (FK dependency)
        try:
            sync_teams(adapter, session, season)
        except Exception:
            logger.exception("Failed to sync teams for %s, skipping season", season)
            continue

        # 2. Fetch all game IDs and deduplicate
        df = adapter.get_season_games(season)
        all_game_ids = list(df["GAME_ID"].unique())
        logger.info("Season %s: %d unique games found", season, len(all_game_ids))

        # 3. Check which games already synced (checkpoint)
        synced = _get_synced_game_ids(session, season)
        remaining = [gid for gid in all_game_ids if gid not in synced]
        logger.info(
            "Season %s: %d already synced, %d remaining",
            season, len(synced), len(remaining),
        )

        # 4. Process in batches
        processed = 0
        for i in range(0, len(remaining), BATCH_SIZE):
            batch = remaining[i : i + BATCH_SIZE]
            try:
                sync_game_box_scores(adapter, session, batch)
                sync_play_by_play(adapter, session, batch)
                sync_shot_charts(adapter, session, batch)

                # Record per-batch checkpoint
                session.add(SyncLog(
                    entity_type="historical_game",
                    last_sync_at=datetime.utcnow(),
                    records_synced=len(batch),
                    season=season,
                    status="success",
                ))
                # Record per-game detail for resume
                for gid in batch:
                    session.add(SyncLog(
                        entity_type="historical_game_detail",
                        last_sync_at=datetime.utcnow(),
                        records_synced=1,
                        season=gid,  # store game_id in season field
                        status="success",
                    ))
                session.commit()
                processed += len(batch)
                logger.info(
                    "Season %s: %d/%d games processed",
                    season, processed + len(synced), len(all_game_ids),
                )
            except Exception:
                logger.exception(
                    "Batch failed at offset %d for season %s, skipping batch",
                    i, season,
                )
                continue

        # 5. Summary log for the season
        session.add(SyncLog(
            entity_type="historical_load",
            last_sync_at=datetime.utcnow(),
            records_synced=processed,
            season=season,
            status="success",
        ))
        session.commit()

        results[season] = processed
        logger.info("Season %s complete: %d games loaded", season, processed)

    total = sum(results.values())
    logger.info("Historical load complete: %d total games across %d seasons", total, len(seasons))
    return results
