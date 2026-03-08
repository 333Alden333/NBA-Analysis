"""Team data synchronization functions."""

import json
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from hermes.data.adapters.base import NBADataAdapter
from hermes.data.models.team import Team
from hermes.data.models.sync_log import SyncLog

logger = logging.getLogger(__name__)


def sync_teams(
    adapter: NBADataAdapter,
    session: Session,
    season: str,
) -> int:
    """Fetch standings and upsert Team rows.

    Returns number of records synced.
    """
    df = adapter.get_league_standings(season)
    count = 0

    for _, row in df.iterrows():
        tid = int(row["TeamID"])
        team = session.get(Team, tid)
        if team is None:
            team = Team(team_id=tid)
            session.add(team)

        team.full_name = f"{row.get('TeamCity', '')} {row.get('TeamName', '')}".strip()
        team.abbreviation = row.get("TeamAbbreviation")
        team.city = row.get("TeamCity")
        team.conference = row.get("Conference")
        team.division = row.get("Division")
        team.raw_json = row.to_json()
        count += 1

    session.commit()

    session.add(SyncLog(
        entity_type="team",
        last_sync_at=datetime.utcnow(),
        records_synced=count,
        season=season,
        status="success",
    ))
    session.commit()

    logger.info("Synced %d teams for season %s", count, season)
    return count


def sync_standings(
    adapter: NBADataAdapter,
    session: Session,
    season: str,
) -> int:
    """Update Team records with W/L/conference rank from standings.

    Returns number of records updated.
    """
    df = adapter.get_league_standings(season)
    count = 0

    for _, row in df.iterrows():
        tid = int(row["TeamID"])
        team = session.get(Team, tid)
        if team is None:
            logger.warning("Team %s not found, skipping standings update", tid)
            continue

        team.conference = row.get("Conference")
        team.division = row.get("Division")
        team.raw_json = row.to_json()
        count += 1

    session.commit()

    session.add(SyncLog(
        entity_type="standings",
        last_sync_at=datetime.utcnow(),
        records_synced=count,
        season=season,
        status="success",
    ))
    session.commit()

    logger.info("Updated standings for %d teams, season %s", count, season)
    return count
