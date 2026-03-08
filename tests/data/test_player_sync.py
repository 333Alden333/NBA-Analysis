"""Tests for player sync functions."""

import json
from unittest.mock import MagicMock

import pandas as pd
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from hermes.data.adapters.base import NBADataAdapter
from hermes.data.models.base import Base
from hermes.data.models.player import Player
from hermes.data.models.box_score import BoxScore
from hermes.data.models.team import Team
from hermes.data.models.game import Game
from hermes.data.models.sync_log import SyncLog
from hermes.data.ingestion.player_sync import sync_players, sync_player_game_logs
from tests.data.fixtures.sample_responses import (
    player_info_df,
    player_game_log_df,
)


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
    # Seed required FK targets
    sess.add(Team(team_id=1610612744, full_name="Golden State Warriors"))
    sess.add(Game(game_id="0022400100", season="2024-25"))
    sess.add(Game(game_id="0022400101", season="2024-25"))
    sess.commit()
    yield sess
    sess.close()


class MockAdapter(NBADataAdapter):
    """Mock adapter returning fixture data."""

    def get_player_info(self, player_id):
        df = player_info_df()
        df["PERSON_ID"] = player_id
        return df.iloc[0].to_dict()

    def get_player_game_log(self, player_id, season):
        return player_game_log_df()

    def get_game_box_score(self, game_id):
        return {}

    def get_play_by_play(self, game_id):
        return pd.DataFrame()

    def get_shot_chart(self, game_id, player_id=None):
        return pd.DataFrame()

    def get_league_standings(self, season):
        return pd.DataFrame()

    def get_season_games(self, season):
        return pd.DataFrame()

    def get_schedule(self, season):
        return pd.DataFrame()


class TestSyncPlayers:
    def test_upserts_player_rows(self, db_session):
        adapter = MockAdapter()
        sync_players(adapter, db_session, [201939], "2024-25")

        players = db_session.query(Player).all()
        assert len(players) == 1
        assert players[0].player_id == 201939
        assert players[0].full_name == "Stephen Curry"

    def test_stores_raw_json(self, db_session):
        adapter = MockAdapter()
        sync_players(adapter, db_session, [201939], "2024-25")

        player = db_session.query(Player).first()
        assert player.raw_json is not None
        data = json.loads(player.raw_json)
        assert "PERSON_ID" in data

    def test_writes_sync_log(self, db_session):
        adapter = MockAdapter()
        sync_players(adapter, db_session, [201939], "2024-25")

        logs = db_session.query(SyncLog).filter_by(entity_type="player").all()
        assert len(logs) == 1
        assert logs[0].records_synced == 1
        assert logs[0].status == "success"

    def test_accepts_abstract_adapter(self, db_session):
        adapter = MockAdapter()
        assert isinstance(adapter, NBADataAdapter)
        sync_players(adapter, db_session, [201939], "2024-25")

    def test_upsert_no_duplicate_on_resync(self, db_session):
        adapter = MockAdapter()
        sync_players(adapter, db_session, [201939], "2024-25")
        sync_players(adapter, db_session, [201939], "2024-25")

        players = db_session.query(Player).all()
        assert len(players) == 1


class TestSyncPlayerGameLogs:
    def test_creates_box_score_rows(self, db_session):
        adapter = MockAdapter()
        # Need the player to exist first (FK)
        db_session.add(Player(player_id=201939, full_name="Stephen Curry", team_id=1610612744))
        db_session.commit()

        sync_player_game_logs(adapter, db_session, [201939], "2024-25")

        scores = db_session.query(BoxScore).all()
        assert len(scores) == 2

    def test_stores_raw_json_on_box_scores(self, db_session):
        adapter = MockAdapter()
        db_session.add(Player(player_id=201939, full_name="Stephen Curry", team_id=1610612744))
        db_session.commit()

        sync_player_game_logs(adapter, db_session, [201939], "2024-25")

        score = db_session.query(BoxScore).first()
        assert score.raw_json is not None

    def test_writes_sync_log(self, db_session):
        adapter = MockAdapter()
        db_session.add(Player(player_id=201939, full_name="Stephen Curry", team_id=1610612744))
        db_session.commit()

        sync_player_game_logs(adapter, db_session, [201939], "2024-25")

        logs = db_session.query(SyncLog).filter_by(entity_type="player_game_log").all()
        assert len(logs) == 1
        assert logs[0].records_synced == 2
