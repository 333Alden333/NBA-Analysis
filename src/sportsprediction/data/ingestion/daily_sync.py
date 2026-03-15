"""Daily sync orchestrator for incremental NBA data updates."""

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from sportsprediction.data.adapters.base import NBADataAdapter, InjuryDataAdapter
from sportsprediction.data.ingestion.game_sync import (
    sync_game_box_scores,
    sync_play_by_play,
    sync_shot_charts,
)
from sportsprediction.data.ingestion.team_sync import sync_teams, sync_standings
from sportsprediction.data.ingestion.injury_sync import sync_injuries
from sportsprediction.data.models.sync_log import SyncLog
from sportsprediction.config import settings

logger = logging.getLogger(__name__)


def _get_last_sync(session: Session, entity_type: str) -> datetime | None:
    """Get the most recent sync timestamp for an entity type."""
    log = (
        session.query(SyncLog)
        .filter_by(entity_type=entity_type)
        .order_by(SyncLog.last_sync_at.desc())
        .first()
    )
    return log.last_sync_at if log else None


def run_daily_sync(
    nba_adapter: NBADataAdapter,
    injury_adapter: InjuryDataAdapter,
    session: Session,
    season: str | None = None,
    skip_features: bool = False,
) -> dict[str, int]:
    """Run incremental sync for all entity types.

    Checks SyncLog for last sync timestamps and only fetches new data.
    Each entity type is wrapped in try/except so partial failures
    don't block other syncs.

    Args:
        nba_adapter: NBA data adapter.
        injury_adapter: Injury data adapter.
        session: SQLAlchemy session.
        season: NBA season string. Defaults to last in config.seasons.

    Returns:
        Dict mapping entity type to records synced.
    """
    if season is None:
        season = settings.seasons[-1]

    results: dict[str, int] = {}
    errors: list[str] = []

    # 1. Sync teams
    try:
        count = sync_teams(nba_adapter, session, season)
        results["teams"] = count
        logger.info("Synced %d teams", count)
    except Exception:
        logger.exception("Failed to sync teams")
        errors.append("teams")

    # 2. Sync standings
    try:
        count = sync_standings(nba_adapter, session, season)
        results["standings"] = count
        logger.info("Synced standings for %d teams", count)
    except Exception:
        logger.exception("Failed to sync standings")
        errors.append("standings")

    # 3. Sync new games since last sync
    new_game_ids: list = []
    try:
        last_game_sync = _get_last_sync(session, "daily_games")
        df = nba_adapter.get_season_games(season)
        all_game_ids = list(df["GAME_ID"].unique())

        # Filter to games after last sync date
        if last_game_sync is not None:
            df_unique = df.drop_duplicates(subset=["GAME_ID"]).copy()
            df_unique["GAME_DATE"] = df_unique["GAME_DATE"].astype(str)
            new_games = df_unique[
                df_unique["GAME_DATE"] > last_game_sync.strftime("%Y-%m-%d")
            ]
            new_game_ids = list(new_games["GAME_ID"].unique())
        else:
            new_game_ids = all_game_ids

        if new_game_ids:
            sync_game_box_scores(nba_adapter, session, new_game_ids)
            sync_play_by_play(nba_adapter, session, new_game_ids)
            sync_shot_charts(nba_adapter, session, new_game_ids)

        results["games"] = len(new_game_ids)

        # Record game sync timestamp
        session.add(SyncLog(
            entity_type="daily_games",
            last_sync_at=datetime.utcnow(),
            records_synced=len(new_game_ids),
            season=season,
            status="success",
        ))
        session.commit()
        logger.info("Synced %d new games", len(new_game_ids))
    except Exception:
        logger.exception("Failed to sync games")
        errors.append("games")

    # 4. Sync injuries (always fresh -- point-in-time snapshot)
    try:
        sync_injuries(injury_adapter, session)
        results["injuries"] = 1
        logger.info("Synced injury report")
    except Exception:
        logger.exception("Failed to sync injuries")
        errors.append("injuries")

    # 4.5. Compute features for newly synced games
    if not skip_features and new_game_ids:
        try:
            from sportsprediction.data.features.engine import compute_all_features_for_games
            compute_all_features_for_games(session, new_game_ids)
            results["features"] = len(new_game_ids)
            logger.info("Computed features for %d games", len(new_game_ids))
        except Exception:
            logger.exception("Failed to compute features")
            errors.append("features")

    # 5. Summary log
    session.add(SyncLog(
        entity_type="daily_sync",
        last_sync_at=datetime.utcnow(),
        records_synced=sum(results.values()),
        season=season,
        status="success" if not errors else "partial",
    ))
    session.commit()

    synced_types = ", ".join(results.keys()) or "none"
    logger.info(
        "Daily sync complete. Entities updated: %s. New games: %d. Errors: %s",
        synced_types,
        results.get("games", 0),
        ", ".join(errors) if errors else "none",
    )

    return results
