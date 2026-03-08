"""Injury data synchronization."""

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from hermes.data.adapters.base import InjuryDataAdapter
from hermes.data.models.injury import Injury
from hermes.data.models.sync_log import SyncLog

logger = logging.getLogger(__name__)


def sync_injuries(adapter: InjuryDataAdapter, session: Session) -> None:
    """Sync current injury report into the database.

    Injuries are a point-in-time snapshot: old records are deleted
    and replaced with the current report.
    """
    try:
        df = adapter.get_current_injuries()

        # Delete all existing injury rows (point-in-time snapshot)
        session.query(Injury).delete()

        records = []
        if not df.empty:
            for _, row in df.iterrows():
                records.append(
                    Injury(
                        player_name=row.get("Player Name"),
                        team=row.get("Team"),
                        game_date=row.get("Game Date"),
                        game_time=row.get("Game Time"),
                        matchup=row.get("Matchup"),
                        status=row.get("Current Status"),
                        reason=row.get("Reason"),
                        updated_at=datetime.utcnow(),
                        raw_json=row.to_json(),
                    )
                )
            session.add_all(records)

        session.add(
            SyncLog(
                entity_type="injuries",
                last_sync_at=datetime.utcnow(),
                records_synced=len(records),
                status="success",
            )
        )
        session.commit()
        logger.info("Injury sync complete: %d records", len(records))

    except Exception as e:
        logger.error("Injury sync failed: %s", e)
        session.rollback()
        session.add(
            SyncLog(
                entity_type="injuries",
                last_sync_at=datetime.utcnow(),
                records_synced=0,
                status="failed",
            )
        )
        session.commit()
