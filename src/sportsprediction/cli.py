"""CLI entry points for SportsPrediction."""

import argparse
import logging
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sportsprediction.config import settings
from sportsprediction.data.models.base import Base
from sportsprediction.data.models.sync_log import SyncLog

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="sportspred",
        description="SportsPrediction - NBA analytics and prediction platform",
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
    sync_parser.add_argument(
        "--skip-features", action="store_true",
        dest="skip_features",
        help="Skip feature computation after game sync",
    )

    features_parser = sub.add_parser("features", help="Feature computation commands")
    features_parser.add_argument(
        "--compute", action="store_true",
        help="Compute/backfill all features for historical games",
    )

    # Predict subcommand
    predict_parser = sub.add_parser("predict", help="Prediction commands")
    predict_group = predict_parser.add_mutually_exclusive_group(required=True)
    predict_group.add_argument(
        "--train", action="store_true",
        help="Train all prediction models from historical data",
    )
    predict_group.add_argument(
        "--today", action="store_true",
        help="Generate predictions for today's games",
    )
    predict_group.add_argument(
        "--resolve", action="store_true",
        help="Resolve outcomes for completed games",
    )
    predict_parser.add_argument(
        "--seasons", type=str, default=None,
        help="Comma-separated seasons for training (e.g. 2022-23,2023-24,2024-25)",
    )

    # Metrics subcommand
    metrics_parser = sub.add_parser("metrics", help="View prediction accuracy metrics")
    metrics_parser.add_argument(
        "--type", type=str, default=None, dest="prediction_type",
        help="Filter by prediction type (game_winner, game_spread, game_total, player_*)",
    )
    metrics_parser.add_argument(
        "--start-date", type=str, default=None, dest="start_date",
        help="Start date filter (YYYY-MM-DD)",
    )
    metrics_parser.add_argument(
        "--end-date", type=str, default=None, dest="end_date",
        help="End date filter (YYYY-MM-DD)",
    )

    # Dashboard subcommand
    sub.add_parser("dashboard", help="Launch the Streamlit dashboard")

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


def _handle_predict(session, args):
    """Handle predict subcommand."""
    if args.train:
        from sportsprediction.models.training import train_all_models

        seasons = None
        if args.seasons:
            seasons = [s.strip() for s in args.seasons.split(",")]

        result = train_all_models(session, seasons=seasons)
        print(f"Training complete:")
        print(f"  Model version: {result['model_version']}")
        print(f"  Game samples: {result['game_samples']}")
        print(f"  Player samples: {result['player_samples']}")

    elif args.today:
        from sportsprediction.models.prediction_engine import PredictionEngine

        engine = PredictionEngine(session)
        result = engine.predict_today()
        print(f"Predictions generated for {result['date']}:")
        print(f"  Games predicted: {result['games_predicted']}")
        print(f"  Players predicted: {result['players_predicted']}")

    elif args.resolve:
        from sportsprediction.models.outcome_resolver import resolve_outcomes

        count = resolve_outcomes(session)
        print(f"Resolved {count} prediction outcomes")


def _handle_metrics(session, args):
    """Handle metrics subcommand."""
    from datetime import date as date_type
    from sportsprediction.models.metrics import compute_metrics, format_metrics_report

    start_date = None
    end_date = None
    if args.start_date:
        start_date = date_type.fromisoformat(args.start_date)
    if args.end_date:
        end_date = date_type.fromisoformat(args.end_date)

    metrics = compute_metrics(
        session,
        prediction_type=args.prediction_type,
        start_date=start_date,
        end_date=end_date,
    )
    print(format_metrics_report(metrics))


def main(argv: list[str] | None = None):
    """Main CLI entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    )

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command not in ("sync", "features", "predict", "metrics", "dashboard"):
        parser.print_help()
        sys.exit(1)

    if args.command == "dashboard":
        import subprocess
        app_path = "src/sportsprediction/dashboard/app.py"
        subprocess.run(["streamlit", "run", app_path])
        return

    session = _create_session()

    try:
        if args.command == "predict":
            _handle_predict(session, args)
            return

        if args.command == "metrics":
            _handle_metrics(session, args)
            return

        if args.command == "features":
            if args.compute:
                from sportsprediction.data.features.engine import backfill_features
                results = backfill_features(session)
                print(f"Feature backfill complete: {results}")
            else:
                parser.parse_args(["features", "--help"])
            return

        if args.historical:
            from sportsprediction.data.adapters.nba_api_adapter import NbaApiAdapter
            from sportsprediction.data.ingestion.rate_limiter import RateLimiter
            from sportsprediction.data.ingestion.historical import run_historical_load

            limiter = RateLimiter(
                min_delay=settings.nba_api_min_delay,
                max_delay=settings.nba_api_max_delay,
            )
            adapter = NbaApiAdapter(limiter)
            results = run_historical_load(adapter, session)
            print(f"Historical load complete: {results}")

        elif args.daily:
            from sportsprediction.data.adapters.nba_api_adapter import NbaApiAdapter
            from sportsprediction.data.adapters.injuries_adapter import NbaInjuriesAdapter
            from sportsprediction.data.ingestion.rate_limiter import RateLimiter
            from sportsprediction.data.ingestion.daily_sync import run_daily_sync

            limiter = RateLimiter(
                min_delay=settings.nba_api_min_delay,
                max_delay=settings.nba_api_max_delay,
            )
            nba_adapter = NbaApiAdapter(limiter)
            injury_adapter = NbaInjuriesAdapter()
            results = run_daily_sync(
                nba_adapter, injury_adapter, session,
                skip_features=args.skip_features,
            )
            print(f"Daily sync complete: {results}")

        elif args.status:
            _print_status(session)

        else:
            parser.parse_args(["sync", "--help"])

    finally:
        session.close()
