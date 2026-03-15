"""Player data synchronization functions."""

import json
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from sportsprediction.data.adapters.base import NBADataAdapter
from sportsprediction.data.models.player import Player
from sportsprediction.data.models.box_score import BoxScore
from sportsprediction.data.models.sync_log import SyncLog

logger = logging.getLogger(__name__)


def sync_players(
    adapter: NBADataAdapter,
    session: Session,
    player_ids: list[int],
    season: str,
) -> int:
    """Fetch player info and upsert into Player table.

    Returns number of records synced.
    """
    count = 0
    for pid in player_ids:
        try:
            info = adapter.get_player_info(pid)
            player = session.get(Player, pid)
            if player is None:
                player = Player(player_id=pid)
                session.add(player)

            player.full_name = info.get("DISPLAY_FIRST_LAST", "")
            player.first_name = info.get("FIRST_NAME")
            player.last_name = info.get("LAST_NAME")
            player.team_id = info.get("TEAM_ID")
            player.position = info.get("POSITION")
            player.height = info.get("HEIGHT")
            player.weight = float(info["WEIGHT"]) if info.get("WEIGHT") else None
            player.country = info.get("COUNTRY")
            player.season_exp = info.get("SEASON_EXP")
            player.jersey = info.get("JERSEY")
            player.is_active = info.get("ROSTERSTATUS") == "Active"
            player.raw_json = json.dumps(info, default=str)

            count += 1
        except Exception:
            logger.exception("Failed to sync player %s", pid)

    session.commit()

    session.add(SyncLog(
        entity_type="player",
        last_sync_at=datetime.utcnow(),
        records_synced=count,
        season=season,
        status="success",
    ))
    session.commit()

    logger.info("Synced %d players for season %s", count, season)
    return count


def sync_player_game_logs(
    adapter: NBADataAdapter,
    session: Session,
    player_ids: list[int],
    season: str,
) -> int:
    """Fetch player game logs and upsert into BoxScore table.

    Returns number of records synced.
    """
    total = 0
    for pid in player_ids:
        try:
            df = adapter.get_player_game_log(pid, season)
            for _, row in df.iterrows():
                # Use game_id + player_id as logical key
                existing = (
                    session.query(BoxScore)
                    .filter_by(game_id=row["GAME_ID"], player_id=pid)
                    .first()
                )
                if existing:
                    bs = existing
                else:
                    bs = BoxScore(game_id=row["GAME_ID"], player_id=pid)
                    session.add(bs)

                bs.team_id = None  # game log doesn't always have team_id
                bs.minutes = float(row.get("MIN", 0)) if row.get("MIN") is not None else None
                bs.points = int(row["PTS"]) if row.get("PTS") is not None else None
                bs.rebounds = int(row["REB"]) if row.get("REB") is not None else None
                bs.assists = int(row["AST"]) if row.get("AST") is not None else None
                bs.steals = int(row["STL"]) if row.get("STL") is not None else None
                bs.blocks = int(row["BLK"]) if row.get("BLK") is not None else None
                bs.turnovers = int(row["TOV"]) if row.get("TOV") is not None else None
                bs.fgm = int(row["FGM"]) if row.get("FGM") is not None else None
                bs.fga = int(row["FGA"]) if row.get("FGA") is not None else None
                bs.fg3m = int(row["FG3M"]) if row.get("FG3M") is not None else None
                bs.fg3a = int(row["FG3A"]) if row.get("FG3A") is not None else None
                bs.ftm = int(row["FTM"]) if row.get("FTM") is not None else None
                bs.fta = int(row["FTA"]) if row.get("FTA") is not None else None
                bs.plus_minus = float(row["PLUS_MINUS"]) if row.get("PLUS_MINUS") is not None else None
                bs.offensive_rebounds = int(row["OREB"]) if row.get("OREB") is not None else None
                bs.defensive_rebounds = int(row["DREB"]) if row.get("DREB") is not None else None
                bs.personal_fouls = int(row["PF"]) if row.get("PF") is not None else None
                bs.raw_json = row.to_json()
                total += 1

            session.commit()
        except Exception:
            logger.exception("Failed to sync game logs for player %s", pid)
            session.rollback()

    session.add(SyncLog(
        entity_type="player_game_log",
        last_sync_at=datetime.utcnow(),
        records_synced=total,
        season=season,
        status="success",
    ))
    session.commit()

    logger.info("Synced %d game log entries for season %s", total, season)
    return total
