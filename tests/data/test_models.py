"""Tests for SQLAlchemy models - table creation, FK constraints, PK types."""

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from sportsprediction.data.models import (
    Base,
    Player,
    Team,
    Game,
    BoxScore,
    PlayByPlay,
    ShotChart,
    PlayerTracking,
    Injury,
    Schedule,
    SyncLog,
)


class TestTableCreation:
    """All 10 tables should be created successfully."""

    def test_all_tables_exist(self, engine):
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        expected = [
            "players",
            "teams",
            "games",
            "box_scores",
            "play_by_play",
            "shot_charts",
            "player_tracking",
            "injuries",
            "schedule",
            "sync_log",
        ]
        for table in expected:
            assert table in table_names, f"Table '{table}' not found"

    def test_ten_tables_total(self, engine):
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        assert len(table_names) == 16


class TestRawJsonColumns:
    """Each table (except SyncLog) has a raw_json TEXT column."""

    @pytest.mark.parametrize(
        "table_name",
        [
            "players",
            "teams",
            "games",
            "box_scores",
            "play_by_play",
            "shot_charts",
            "player_tracking",
            "injuries",
            "schedule",
        ],
    )
    def test_raw_json_column_exists(self, engine, table_name):
        inspector = inspect(engine)
        columns = {c["name"] for c in inspector.get_columns(table_name)}
        assert "raw_json" in columns, f"'{table_name}' missing raw_json column"

    def test_sync_log_no_raw_json(self, engine):
        inspector = inspect(engine)
        columns = {c["name"] for c in inspector.get_columns("sync_log")}
        assert "raw_json" not in columns


class TestPrimaryKeys:
    """Player and Team use NBA IDs, Game uses string ID."""

    def test_player_uses_nba_player_id(self, session):
        player = Player(
            player_id=203999,
            full_name="Nikola Jokic",
        )
        session.add(player)
        session.commit()
        assert session.get(Player, 203999) is not None

    def test_team_uses_nba_team_id(self, session):
        team = Team(
            team_id=1610612743,
            abbreviation="DEN",
            full_name="Denver Nuggets",
        )
        session.add(team)
        session.commit()
        assert session.get(Team, 1610612743) is not None

    def test_game_uses_string_id(self, session):
        # Need teams first for FK
        session.add(Team(team_id=1, abbreviation="HOM", full_name="Home"))
        session.add(Team(team_id=2, abbreviation="AWY", full_name="Away"))
        session.commit()

        game = Game(
            game_id="0022400001",
            season="2024-25",
            home_team_id=1,
            away_team_id=2,
        )
        session.add(game)
        session.commit()
        assert session.get(Game, "0022400001") is not None
        assert len("0022400001") == 10


class TestForeignKeyConstraints:
    """FK constraints are enforced."""

    def test_boxscore_fk_game_id_enforced(self, session):
        # Insert BoxScore with nonexistent game_id
        session.add(Team(team_id=1, abbreviation="TST", full_name="Test"))
        session.add(Player(player_id=1, full_name="Test Player"))
        session.commit()

        bs = BoxScore(game_id="9999999999", player_id=1, team_id=1)
        session.add(bs)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_plabyplay_fk_game_id_enforced(self, session):
        pbp = PlayByPlay(game_id="9999999999", event_num=1)
        session.add(pbp)
        with pytest.raises(IntegrityError):
            session.commit()


class TestSyncLogFields:
    """SyncLog tracks entity_type, last_sync_at, records_synced, season, status."""

    def test_sync_log_fields(self, session):
        from datetime import datetime

        log = SyncLog(
            entity_type="player_stats",
            last_sync_at=datetime(2024, 1, 1),
            records_synced=100,
            season="2024-25",
            status="success",
        )
        session.add(log)
        session.commit()

        result = session.get(SyncLog, log.id)
        assert result.entity_type == "player_stats"
        assert result.records_synced == 100
        assert result.season == "2024-25"
        assert result.status == "success"

    def test_sync_log_default_status(self, session):
        from datetime import datetime

        log = SyncLog(
            entity_type="box_scores",
            last_sync_at=datetime(2024, 1, 1),
            records_synced=50,
        )
        session.add(log)
        session.commit()

        result = session.get(SyncLog, log.id)
        assert result.status == "success"
