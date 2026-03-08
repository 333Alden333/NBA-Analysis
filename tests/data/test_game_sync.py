"""Tests for game sync functions."""

import json

import pandas as pd
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from hermes.data.adapters.base import NBADataAdapter
from hermes.data.models.base import Base
from hermes.data.models.team import Team
from hermes.data.models.player import Player
from hermes.data.models.game import Game
from hermes.data.models.box_score import BoxScore
from hermes.data.models.play_by_play import PlayByPlay
from hermes.data.models.shot_chart import ShotChart
from hermes.data.models.sync_log import SyncLog
from hermes.data.ingestion.game_sync import (
    sync_game_box_scores,
    sync_play_by_play,
    sync_shot_charts,
)
from tests.data.fixtures.sample_responses import (
    box_score_player_stats_df,
    box_score_team_stats_df,
    play_by_play_df,
    shot_chart_df,
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
    # Seed FK targets -- order matters for FK constraints
    sess.add(Team(team_id=1610612744, full_name="Golden State Warriors"))
    sess.flush()
    sess.add(Player(player_id=201939, full_name="Stephen Curry", team_id=1610612744))
    sess.add(Game(game_id="0022400100", season="2024-25"))
    sess.commit()
    yield sess
    sess.close()


class MockAdapter(NBADataAdapter):
    def get_player_info(self, player_id):
        return {}

    def get_player_game_log(self, player_id, season):
        return pd.DataFrame()

    def get_game_box_score(self, game_id):
        return {
            "PlayerStats": box_score_player_stats_df(),
            "TeamStats": box_score_team_stats_df(),
        }

    def get_play_by_play(self, game_id):
        return play_by_play_df()

    def get_shot_chart(self, game_id, player_id=None):
        return shot_chart_df()

    def get_league_standings(self, season):
        return pd.DataFrame()

    def get_season_games(self, season):
        return pd.DataFrame()

    def get_schedule(self, season):
        return pd.DataFrame()


class TestSyncGameBoxScores:
    def test_creates_box_score_rows(self, db_session):
        adapter = MockAdapter()
        sync_game_box_scores(adapter, db_session, ["0022400100"])

        scores = db_session.query(BoxScore).all()
        assert len(scores) == 1
        assert scores[0].points == 32

    def test_stores_raw_json(self, db_session):
        adapter = MockAdapter()
        sync_game_box_scores(adapter, db_session, ["0022400100"])

        score = db_session.query(BoxScore).first()
        assert score.raw_json is not None

    def test_writes_sync_log(self, db_session):
        adapter = MockAdapter()
        sync_game_box_scores(adapter, db_session, ["0022400100"])

        logs = db_session.query(SyncLog).filter_by(entity_type="box_score").all()
        assert len(logs) == 1
        assert logs[0].records_synced >= 1

    def test_handles_game_failure_gracefully(self, db_session):
        class FailAdapter(MockAdapter):
            def get_game_box_score(self, game_id):
                raise RuntimeError("API error")

        adapter = FailAdapter()
        # Should not raise
        sync_game_box_scores(adapter, db_session, ["0022400100"])


class TestSyncPlayByPlay:
    def test_creates_pbp_rows(self, db_session):
        adapter = MockAdapter()
        sync_play_by_play(adapter, db_session, ["0022400100"])

        pbp = db_session.query(PlayByPlay).all()
        assert len(pbp) == 2

    def test_stores_raw_json(self, db_session):
        adapter = MockAdapter()
        sync_play_by_play(adapter, db_session, ["0022400100"])

        pbp = db_session.query(PlayByPlay).first()
        assert pbp.raw_json is not None

    def test_writes_sync_log(self, db_session):
        adapter = MockAdapter()
        sync_play_by_play(adapter, db_session, ["0022400100"])

        logs = db_session.query(SyncLog).filter_by(entity_type="play_by_play").all()
        assert len(logs) == 1


class TestSyncShotCharts:
    def test_creates_shot_chart_rows(self, db_session):
        adapter = MockAdapter()
        sync_shot_charts(adapter, db_session, ["0022400100"])

        shots = db_session.query(ShotChart).all()
        assert len(shots) == 2

    def test_stores_raw_json(self, db_session):
        adapter = MockAdapter()
        sync_shot_charts(adapter, db_session, ["0022400100"])

        shot = db_session.query(ShotChart).first()
        assert shot.raw_json is not None

    def test_writes_sync_log(self, db_session):
        adapter = MockAdapter()
        sync_shot_charts(adapter, db_session, ["0022400100"])

        logs = db_session.query(SyncLog).filter_by(entity_type="shot_chart").all()
        assert len(logs) == 1
