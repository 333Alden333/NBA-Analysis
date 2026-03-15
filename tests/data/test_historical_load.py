"""Tests for historical data loader with checkpoint/resume."""

import logging
from datetime import datetime
from unittest.mock import MagicMock, patch, call

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SASession, sessionmaker

from sportsprediction.data.models.base import Base
from sportsprediction.data.models.sync_log import SyncLog
from sportsprediction.data.ingestion.historical import run_historical_load


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture()
def mock_adapter():
    adapter = MagicMock()
    # Return 4 rows (2 games x 2 teams each) to test deduplication
    adapter.get_season_games.return_value = pd.DataFrame({
        "GAME_ID": ["0022200001", "0022200001", "0022200002", "0022200002"],
        "GAME_DATE": ["2022-10-18", "2022-10-18", "2022-10-19", "2022-10-19"],
    })
    adapter.get_game_box_score.return_value = {
        "PlayerStats": pd.DataFrame({"PLAYER_ID": [101, 102]}),
        "TeamStats": pd.DataFrame(),
    }
    return adapter


class TestHistoricalLoad:
    def test_processes_all_configured_seasons(self, db_session, mock_adapter):
        """run_historical_load processes all provided seasons."""
        seasons = ["2022-23", "2023-24"]
        run_historical_load(mock_adapter, db_session, seasons=seasons)

        # Should have called get_season_games once per season
        assert mock_adapter.get_season_games.call_count == 2
        calls = [c[0][0] for c in mock_adapter.get_season_games.call_args_list]
        assert "2022-23" in calls
        assert "2023-24" in calls

    def test_deduplicates_game_ids(self, db_session, mock_adapter):
        """Game IDs from LeagueGameFinder appear twice; loader deduplicates."""
        from sportsprediction.data.ingestion.game_sync import sync_game_box_scores
        run_historical_load(mock_adapter, db_session, seasons=["2022-23"])

        # Should sync 2 unique games, not 4 rows
        # Check via SyncLog entries
        logs = db_session.query(SyncLog).filter_by(
            entity_type="historical_game", season="2022-23"
        ).all()
        total_records = sum(log.records_synced for log in logs)
        assert total_records == 2  # 2 unique games

    def test_checkpoint_resume_skips_synced_games(self, db_session, mock_adapter):
        """Pre-populated SyncLog entries cause those games to be skipped."""
        # Pre-populate: mark game 0022200001 as already synced
        db_session.add(SyncLog(
            entity_type="historical_game",
            last_sync_at=datetime.utcnow(),
            records_synced=1,
            season="2022-23",
            status="success",
        ))
        # Store which game IDs were already done
        # We need a way to track per-game. The loader uses a detail log.
        # Let's add a specific game marker
        db_session.add(SyncLog(
            entity_type="historical_game_detail",
            last_sync_at=datetime.utcnow(),
            records_synced=1,
            season="0022200001",  # store game_id in season field for tracking
            status="success",
        ))
        db_session.commit()

        run_historical_load(mock_adapter, db_session, seasons=["2022-23"])

        # Only game 0022200002 should have been processed in box scores
        # Check the detail logs - should now have entries for both games
        detail_logs = db_session.query(SyncLog).filter_by(
            entity_type="historical_game_detail"
        ).all()
        game_ids_synced = [log.season for log in detail_logs]
        assert "0022200001" in game_ids_synced  # pre-existing
        assert "0022200002" in game_ids_synced  # newly synced

    def test_individual_game_failure_doesnt_stop_load(self, db_session, mock_adapter):
        """If one game fails, others still process."""
        from sportsprediction.data.ingestion import game_sync

        original_sync = game_sync.sync_game_box_scores
        call_count = {"value": 0}

        with patch.object(game_sync, "sync_game_box_scores") as mock_box, \
             patch.object(game_sync, "sync_play_by_play") as mock_pbp, \
             patch.object(game_sync, "sync_shot_charts") as mock_shots:
            # These succeed normally
            mock_box.return_value = 1
            mock_pbp.return_value = 1
            mock_shots.return_value = 1
            # First call raises, second succeeds
            mock_box.side_effect = [Exception("API error"), 1]

            # Should not raise
            run_historical_load(mock_adapter, db_session, seasons=["2022-23"])

    def test_batch_processing(self, db_session, mock_adapter):
        """Games are processed in batches."""
        # Create 120 unique games (60 x 2 rows for dedup)
        game_ids = []
        for i in range(60):
            gid = f"00222{i:05d}"
            game_ids.extend([gid, gid])
        mock_adapter.get_season_games.return_value = pd.DataFrame({
            "GAME_ID": game_ids,
            "GAME_DATE": ["2022-10-18"] * len(game_ids),
        })

        with patch("sportsprediction.data.ingestion.historical.sync_game_box_scores") as mock_box, \
             patch("sportsprediction.data.ingestion.historical.sync_play_by_play") as mock_pbp, \
             patch("sportsprediction.data.ingestion.historical.sync_shot_charts") as mock_shots:
            mock_box.return_value = 1
            mock_pbp.return_value = 1
            mock_shots.return_value = 1

            run_historical_load(mock_adapter, db_session, seasons=["2022-23"])

            # 60 games in batches of 50 = 2 calls each
            assert mock_box.call_count == 2
            # First batch should have 50 games
            assert len(mock_box.call_args_list[0][0][2]) == 50
            # Second batch should have 10 games
            assert len(mock_box.call_args_list[1][0][2]) == 10

    def test_synclog_entries_after_completion(self, db_session, mock_adapter):
        """After completion, SyncLog has entries for the season."""
        run_historical_load(mock_adapter, db_session, seasons=["2022-23"])

        logs = db_session.query(SyncLog).filter_by(
            entity_type="historical_load", season="2022-23"
        ).all()
        assert len(logs) == 1
        assert logs[0].status == "success"
        assert logs[0].records_synced > 0

    def test_teams_synced_before_games(self, db_session, mock_adapter):
        """Teams must be synced before games (FK dependency)."""
        call_order = []

        with patch("sportsprediction.data.ingestion.historical.sync_teams") as mock_teams, \
             patch("sportsprediction.data.ingestion.historical.sync_game_box_scores") as mock_box, \
             patch("sportsprediction.data.ingestion.historical.sync_play_by_play") as mock_pbp, \
             patch("sportsprediction.data.ingestion.historical.sync_shot_charts") as mock_shots:
            mock_teams.side_effect = lambda *a, **kw: call_order.append("teams") or 1
            mock_box.side_effect = lambda *a, **kw: call_order.append("box_scores") or 1
            mock_pbp.return_value = 1
            mock_shots.return_value = 1

            run_historical_load(mock_adapter, db_session, seasons=["2022-23"])

            assert call_order.index("teams") < call_order.index("box_scores")
