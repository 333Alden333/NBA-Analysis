"""CLI entry points for Hermes Analysis."""

import argparse
import logging
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from hermes.config import settings
from hermes.data.models.base import Base
from hermes.data.models.sync_log import SyncLog

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="hermes",
        description="Hermes Analysis - NBA analytics and prediction platform",
    )
    sub = parser.add_subparsers(dest="command")

    sync_parser = sub.add_parser("sync", help="Data synchronization commands")
    sync_parser.add_argument(
        "--historical", action="store_true",
        help="Load historical data for all configured seasons",
    )
    sync_parser.add_argument(
        "--daily", action="store_true",
        help="Run incremental daily sync",
    )
    sync_parser.add_argument(
        "--status", action="store_true",
        help="Print sync status summary",
    )

    return parser


def _create_session():
    """Create a database engine and session."""
    engine = create_engine(f"sqlite:///{settings.db_path}")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def _print_status(session):
    """Print SyncLog summary."""
    from sqlalchemy import func

    rows = (
        session.query(
            SyncLog.entity_type,
            func.max(SyncLog.last_sync_at).label("last_sync"),
            func.sum(SyncLog.records_synced).label("total_records"),
        )
        .group_by(SyncLog.entity_type)
        .all()
    )

    if not rows:
        print("No sync history found. Run --historical or --daily first.")
        return

    print(f"{'Entity Type':<25} {'Last Sync':<25} {'Total Records':<15}")
    print("-" * 65)
    for row in rows:
        print(f"{row.entity_type:<25} {str(row.last_sync):<25} {row.total_records:<15}")


def main(argv: list[str] | None = None):
    """Main CLI entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    )

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command != "sync":
        parser.print_help()
        sys.exit(1)

    session = _create_session()

    try:
        if args.historical:
            from hermes.data.adapters.nba_api_adapter import NbaApiAdapter
            from hermes.data.ingestion.rate_limiter import RateLimiter
            from hermes.data.ingestion.historical import run_historical_load

            limiter = RateLimiter(
                min_delay=settings.nba_api_min_delay,
                max_delay=settings.nba_api_max_delay,
            )
            adapter = NbaApiAdapter(limiter)
            results = run_historical_load(adapter, session)
            print(f"Historical load complete: {results}")

        elif args.daily:
            from hermes.data.adapters.nba_api_adapter import NbaApiAdapter
            from hermes.data.adapters.injuries_adapter import NbaInjuriesAdapter
            from hermes.data.ingestion.rate_limiter import RateLimiter
            from hermes.data.ingestion.daily_sync import run_daily_sync

            limiter = RateLimiter(
                min_delay=settings.nba_api_min_delay,
                max_delay=settings.nba_api_max_delay,
            )
            nba_adapter = NbaApiAdapter(limiter)
            injury_adapter = NbaInjuriesAdapter()
            results = run_daily_sync(nba_adapter, injury_adapter, session)
            print(f"Daily sync complete: {results}")

        elif args.status:
            _print_status(session)

        else:
            parser.parse_args(["sync", "--help"])

    finally:
        session.close()
