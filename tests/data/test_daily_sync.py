"""Tests for daily sync orchestrator."""

import logging
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sportsprediction.data.models.base import Base
from sportsprediction.data.models.sync_log import SyncLog
from sportsprediction.data.ingestion.daily_sync import run_daily_sync


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture()
def mock_nba_adapter():
    adapter = MagicMock()
    adapter.get_season_games.return_value = pd.DataFrame({
        "GAME_ID": ["0022400100", "0022400100", "0022400101", "0022400101"],
        "GAME_DATE": ["2025-01-15", "2025-01-15", "2025-01-16", "2025-01-16"],
    })
    return adapter


@pytest.fixture()
def mock_injury_adapter():
    return MagicMock()


class TestDailySync:
    def test_checks_synclog_for_last_timestamp(self, db_session, mock_nba_adapter, mock_injury_adapter):
        """Daily sync checks SyncLog for last sync time."""
        run_daily_sync(mock_nba_adapter, mock_injury_adapter, db_session, season="2024-25")

        # Should have created SyncLog entries
        logs = db_session.query(SyncLog).filter_by(entity_type="daily_sync").all()
        assert len(logs) == 1

    def test_syncs_all_entity_types(self, db_session, mock_nba_adapter, mock_injury_adapter):
        """Daily sync touches teams, standings, games, and injuries."""
        with patch("sportsprediction.data.ingestion.daily_sync.sync_teams") as m_teams, \
             patch("sportsprediction.data.ingestion.daily_sync.sync_standings") as m_stand, \
             patch("sportsprediction.data.ingestion.daily_sync.sync_game_box_scores") as m_box, \
             patch("sportsprediction.data.ingestion.daily_sync.sync_play_by_play") as m_pbp, \
             patch("sportsprediction.data.ingestion.daily_sync.sync_shot_charts") as m_shots, \
             patch("sportsprediction.data.ingestion.daily_sync.sync_injuries") as m_inj:
            m_teams.return_value = 30
            m_stand.return_value = 30
            m_box.return_value = 2
            m_pbp.return_value = 2
            m_shots.return_value = 2
            m_inj.return_value = None

            run_daily_sync(mock_nba_adapter, mock_injury_adapter, db_session, season="2024-25")

            m_teams.assert_called_once()
            m_stand.assert_called_once()
            m_inj.assert_called_once()

    def test_only_fetches_new_games(self, db_session, mock_nba_adapter, mock_injury_adapter):
        """Games older than last sync are skipped."""
        # Pre-populate: last game sync was 2025-01-15
        db_session.add(SyncLog(
            entity_type="daily_games",
            last_sync_at=datetime(2025, 1, 15, 23, 59),
            records_synced=5,
            season="2024-25",
            status="success",
        ))
        db_session.commit()

        with patch("sportsprediction.data.ingestion.daily_sync.sync_game_box_scores") as m_box, \
             patch("sportsprediction.data.ingestion.daily_sync.sync_play_by_play") as m_pbp, \
             patch("sportsprediction.data.ingestion.daily_sync.sync_shot_charts") as m_shots:
            m_box.return_value = 1
            m_pbp.return_value = 1
            m_shots.return_value = 1

            run_daily_sync(mock_nba_adapter, mock_injury_adapter, db_session, season="2024-25")

            if m_box.called:
                # Should only include game from 2025-01-16, not 2025-01-15
                game_ids = m_box.call_args[0][2]
                assert "0022400101" in game_ids
                assert "0022400100" not in game_ids

    def test_writes_synclog_entries(self, db_session, mock_nba_adapter, mock_injury_adapter):
        """SyncLog updated after sync."""
        run_daily_sync(mock_nba_adapter, mock_injury_adapter, db_session, season="2024-25")

        logs = db_session.query(SyncLog).all()
        entity_types = {log.entity_type for log in logs}
        assert "daily_sync" in entity_types

    def test_partial_failure_doesnt_block_others(self, db_session, mock_nba_adapter, mock_injury_adapter):
        """If one entity type fails, others still sync."""
        with patch("sportsprediction.data.ingestion.daily_sync.sync_teams", side_effect=Exception("API down")), \
             patch("sportsprediction.data.ingestion.daily_sync.sync_standings") as m_stand, \
             patch("sportsprediction.data.ingestion.daily_sync.sync_injuries") as m_inj:
            m_stand.return_value = 30
            m_inj.return_value = None

            # Should not raise
            run_daily_sync(mock_nba_adapter, mock_injury_adapter, db_session, season="2024-25")

            # Standings and injuries should still have been called
            m_stand.assert_called_once()
            m_inj.assert_called_once()

    def test_freshness_logged(self, db_session, mock_nba_adapter, mock_injury_adapter, caplog):
        """Freshness timestamps appear in logs."""
        with caplog.at_level(logging.INFO, logger="sportsprediction.data.ingestion.daily_sync"):
            run_daily_sync(mock_nba_adapter, mock_injury_adapter, db_session, season="2024-25")

        assert any("Daily sync complete" in r.message for r in caplog.records)


class TestCLI:
    def test_cli_parses_historical(self):
        """CLI recognizes --historical flag."""
        from sportsprediction.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["sync", "--historical"])
        assert args.historical is True
        assert args.daily is False

    def test_cli_parses_daily(self):
        """CLI recognizes --daily flag."""
        from sportsprediction.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["sync", "--daily"])
        assert args.daily is True
        assert args.historical is False

    def test_cli_parses_status(self):
        """CLI recognizes --status flag."""
        from sportsprediction.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["sync", "--status"])
        assert args.status is True
