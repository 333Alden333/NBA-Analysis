"""Game data synchronization functions."""

import json
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from hermes.data.adapters.base import NBADataAdapter
from hermes.data.models.game import Game
from hermes.data.models.box_score import BoxScore
from hermes.data.models.play_by_play import PlayByPlay
from hermes.data.models.shot_chart import ShotChart
from hermes.data.models.sync_log import SyncLog

logger = logging.getLogger(__name__)


def sync_game_box_scores(
    adapter: NBADataAdapter,
    session: Session,
    game_ids: list[str],
) -> int:
    """Fetch box scores for games and store to BoxScore table.

    Handles individual game failures gracefully.
    Returns total records synced.
    """
    total = 0
    for i, gid in enumerate(game_ids):
        try:
            logger.info("Syncing box score %d/%d: %s", i + 1, len(game_ids), gid)
            data = adapter.get_game_box_score(gid)
            player_stats = data.get("PlayerStats")
            if player_stats is None or player_stats.empty:
                continue

            for _, row in player_stats.iterrows():
                pid = int(row.get("personId", 0))
                existing = (
                    session.query(BoxScore)
                    .filter_by(game_id=gid, player_id=pid)
                    .first()
                )
                if existing:
                    bs = existing
                else:
                    bs = BoxScore(game_id=gid, player_id=pid)
                    session.add(bs)

                bs.team_id = int(row["teamId"]) if row.get("teamId") else None
                bs.points = int(row["points"]) if row.get("points") is not None else None
                bs.rebounds = int(row["reboundsTotal"]) if row.get("reboundsTotal") is not None else None
                bs.assists = int(row["assists"]) if row.get("assists") is not None else None
                bs.steals = int(row["steals"]) if row.get("steals") is not None else None
                bs.blocks = int(row["blocks"]) if row.get("blocks") is not None else None
                bs.turnovers = int(row["turnovers"]) if row.get("turnovers") is not None else None
                bs.fgm = int(row["fieldGoalsMade"]) if row.get("fieldGoalsMade") is not None else None
                bs.fga = int(row["fieldGoalsAttempted"]) if row.get("fieldGoalsAttempted") is not None else None
                bs.fg3m = int(row["threePointersMade"]) if row.get("threePointersMade") is not None else None
                bs.fg3a = int(row["threePointersAttempted"]) if row.get("threePointersAttempted") is not None else None
                bs.ftm = int(row["freeThrowsMade"]) if row.get("freeThrowsMade") is not None else None
                bs.fta = int(row["freeThrowsAttempted"]) if row.get("freeThrowsAttempted") is not None else None
                bs.plus_minus = float(row["plusMinusPoints"]) if row.get("plusMinusPoints") is not None else None
                bs.offensive_rebounds = int(row["reboundsOffensive"]) if row.get("reboundsOffensive") is not None else None
                bs.defensive_rebounds = int(row["reboundsDefensive"]) if row.get("reboundsDefensive") is not None else None
                bs.personal_fouls = int(row["foulsPersonal"]) if row.get("foulsPersonal") is not None else None
                bs.raw_json = row.to_json()
                total += 1

            session.commit()
        except Exception:
            logger.exception("Failed to sync box score for game %s", gid)
            session.rollback()

    session.add(SyncLog(
        entity_type="box_score",
        last_sync_at=datetime.utcnow(),
        records_synced=total,
        season=None,
        status="success",
    ))
    session.commit()

    logger.info("Synced %d box score entries across %d games", total, len(game_ids))
    return total


def sync_play_by_play(
    adapter: NBADataAdapter,
    session: Session,
    game_ids: list[str],
) -> int:
    """Fetch play-by-play data for games and store to PlayByPlay table.

    Returns total records synced.
    """
    total = 0
    for i, gid in enumerate(game_ids):
        try:
            logger.info("Syncing PBP %d/%d: %s", i + 1, len(game_ids), gid)
            df = adapter.get_play_by_play(gid)
            if df.empty:
                continue

            for _, row in df.iterrows():
                pbp = PlayByPlay(
                    game_id=gid,
                    event_num=int(row.get("actionNumber", 0)),
                    period=int(row.get("period", 0)),
                    clock=str(row.get("clock", "")),
                    event_type=str(row.get("actionType", "")),
                    description=str(row.get("description", "")),
                    player1_id=int(row["personId"]) if row.get("personId") else None,
                    team_id=int(row["teamId"]) if row.get("teamId") else None,
                    score_home=str(row.get("scoreHome", "")),
                    score_away=str(row.get("scoreAway", "")),
                    raw_json=row.to_json(),
                )
                session.add(pbp)
                total += 1

            session.commit()
        except Exception:
            logger.exception("Failed to sync PBP for game %s", gid)
            session.rollback()

    session.add(SyncLog(
        entity_type="play_by_play",
        last_sync_at=datetime.utcnow(),
        records_synced=total,
        season=None,
        status="success",
    ))
    session.commit()

    logger.info("Synced %d PBP entries across %d games", total, len(game_ids))
    return total


def sync_shot_charts(
    adapter: NBADataAdapter,
    session: Session,
    game_ids: list[str],
) -> int:
    """Fetch shot chart data for games and store to ShotChart table.

    Returns total records synced.
    """
    total = 0
    for i, gid in enumerate(game_ids):
        try:
            logger.info("Syncing shots %d/%d: %s", i + 1, len(game_ids), gid)
            df = adapter.get_shot_chart(gid)
            if df.empty:
                continue

            for _, row in df.iterrows():
                shot = ShotChart(
                    game_id=gid,
                    player_id=int(row["PLAYER_ID"]),
                    team_id=int(row["TEAM_ID"]) if row.get("TEAM_ID") else None,
                    period=int(row.get("PERIOD", 0)),
                    minutes_remaining=int(row.get("MINUTES_REMAINING", 0)),
                    seconds_remaining=int(row.get("SECONDS_REMAINING", 0)),
                    shot_type=str(row.get("SHOT_TYPE", "")),
                    action_type=str(row.get("ACTION_TYPE", "")),
                    shot_zone_basic=str(row.get("SHOT_ZONE_BASIC", "")),
                    shot_zone_area=str(row.get("SHOT_ZONE_AREA", "")),
                    shot_zone_range=str(row.get("SHOT_ZONE_RANGE", "")),
                    shot_distance=int(row.get("SHOT_DISTANCE", 0)),
                    loc_x=int(row.get("LOC_X", 0)),
                    loc_y=int(row.get("LOC_Y", 0)),
                    shot_made=bool(row.get("SHOT_MADE_FLAG", 0)),
                    raw_json=row.to_json(),
                )
                session.add(shot)
                total += 1

            session.commit()
        except Exception:
            logger.exception("Failed to sync shot chart for game %s", gid)
            session.rollback()

    session.add(SyncLog(
        entity_type="shot_chart",
        last_sync_at=datetime.utcnow(),
        records_synced=total,
        season=None,
        status="success",
    ))
    session.commit()

    logger.info("Synced %d shot entries across %d games", total, len(game_ids))
    return total
