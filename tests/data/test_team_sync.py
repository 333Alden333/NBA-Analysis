"""Tests for team sync functions."""

import json

import pandas as pd
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from sportsprediction.data.adapters.base import NBADataAdapter
from sportsprediction.data.models.base import Base
from sportsprediction.data.models.team import Team
from sportsprediction.data.models.sync_log import SyncLog
from sportsprediction.data.ingestion.team_sync import sync_teams, sync_standings
from tests.data.fixtures.sample_responses import league_standings_df


@pytest.fixture
def db_session():
    eng = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(eng, "connect")
    def set_sqlite_pragma(dbapi_conn, _rec):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    sess = Session()
    yield sess
    sess.close()


class MockAdapter(NBADataAdapter):
    def get_player_info(self, player_id):
        return {}

    def get_player_game_log(self, player_id, season):
        return pd.DataFrame()

    def get_game_box_score(self, game_id):
        return {}

    def get_play_by_play(self, game_id):
        return pd.DataFrame()

    def get_shot_chart(self, game_id, player_id=None):
        return pd.DataFrame()

    def get_league_standings(self, season):
        return league_standings_df()

    def get_season_games(self, season):
        return pd.DataFrame()

    def get_schedule(self, season):
        return pd.DataFrame()


class TestSyncTeams:
    def test_upserts_team_rows(self, db_session):
        adapter = MockAdapter()
        sync_teams(adapter, db_session, "2024-25")

        teams = db_session.query(Team).all()
        assert len(teams) == 2
        abbrs = {t.abbreviation for t in teams}
        assert "GSW" in abbrs
        assert "LAL" in abbrs

    def test_stores_raw_json(self, db_session):
        adapter = MockAdapter()
        sync_teams(adapter, db_session, "2024-25")

        team = db_session.query(Team).first()
        assert team.raw_json is not None

    def test_writes_sync_log(self, db_session):
        adapter = MockAdapter()
        sync_teams(adapter, db_session, "2024-25")

        logs = db_session.query(SyncLog).filter_by(entity_type="team").all()
        assert len(logs) == 1
        assert logs[0].records_synced == 2

    def test_upsert_no_duplicate(self, db_session):
        adapter = MockAdapter()
        sync_teams(adapter, db_session, "2024-25")
        sync_teams(adapter, db_session, "2024-25")

        teams = db_session.query(Team).all()
        assert len(teams) == 2


class TestSyncStandings:
    def test_updates_team_records(self, db_session):
        adapter = MockAdapter()
        # Seed teams first
        sync_teams(adapter, db_session, "2024-25")
        sync_standings(adapter, db_session, "2024-25")

        gsw = db_session.query(Team).filter_by(team_id=1610612744).one()
        assert gsw.conference == "West"

    def test_writes_sync_log(self, db_session):
        adapter = MockAdapter()
        sync_teams(adapter, db_session, "2024-25")
        sync_standings(adapter, db_session, "2024-25")

        logs = db_session.query(SyncLog).filter_by(entity_type="standings").all()
        assert len(logs) == 1
