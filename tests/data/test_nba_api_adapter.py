"""Tests for NbaApiAdapter wrapping nba_api endpoints."""

from unittest.mock import MagicMock, patch

import pytest

from hermes.data.adapters.base import NBADataAdapter
from hermes.data.adapters.nba_api_adapter import NbaApiAdapter
from hermes.data.ingestion.rate_limiter import RateLimiter
from tests.data.fixtures.sample_responses import (
    player_info_df,
    player_game_log_df,
    box_score_player_stats_df,
    box_score_team_stats_df,
    play_by_play_df,
    shot_chart_df,
    league_standings_df,
    season_games_df,
    schedule_df,
)


@pytest.fixture
def rate_limiter():
    rl = RateLimiter(min_delay=0.0, max_delay=0.0)
    rl.wait = MagicMock()
    return rl


@pytest.fixture
def adapter(rate_limiter):
    return NbaApiAdapter(rate_limiter)


class TestAdapterIsNBADataAdapter:
    def test_is_instance(self, adapter):
        assert isinstance(adapter, NBADataAdapter)


class TestGetPlayerInfo:
    @patch("hermes.data.adapters.nba_api_adapter.commonplayerinfo.CommonPlayerInfo")
    def test_returns_dict_with_expected_keys(self, mock_cls, adapter):
        mock_inst = MagicMock()
        mock_inst.get_data_frames.return_value = [player_info_df()]
        mock_cls.return_value = mock_inst

        result = adapter.get_player_info(201939)

        assert isinstance(result, dict)
        assert "PERSON_ID" in result
        assert "DISPLAY_FIRST_LAST" in result
        assert "TEAM_ID" in result
        assert result["PERSON_ID"] == 201939

    @patch("hermes.data.adapters.nba_api_adapter.commonplayerinfo.CommonPlayerInfo")
    def test_uses_rate_limiter(self, mock_cls, adapter, rate_limiter):
        mock_inst = MagicMock()
        mock_inst.get_data_frames.return_value = [player_info_df()]
        mock_cls.return_value = mock_inst

        adapter.get_player_info(201939)
        rate_limiter.wait.assert_called()


class TestGetPlayerGameLog:
    @patch("hermes.data.adapters.nba_api_adapter.playergamelog.PlayerGameLog")
    def test_returns_dataframe_with_expected_columns(self, mock_cls, adapter):
        mock_inst = MagicMock()
        mock_inst.get_data_frames.return_value = [player_game_log_df()]
        mock_cls.return_value = mock_inst

        result = adapter.get_player_game_log(201939, "2024-25")

        assert "GAME_ID" in result.columns
        assert "PTS" in result.columns
        assert "REB" in result.columns
        assert "AST" in result.columns
        assert len(result) == 2

    @patch("hermes.data.adapters.nba_api_adapter.playergamelog.PlayerGameLog")
    def test_uses_rate_limiter(self, mock_cls, adapter, rate_limiter):
        mock_inst = MagicMock()
        mock_inst.get_data_frames.return_value = [player_game_log_df()]
        mock_cls.return_value = mock_inst

        adapter.get_player_game_log(201939, "2024-25")
        rate_limiter.wait.assert_called()


class TestGetGameBoxScore:
    @patch("hermes.data.adapters.nba_api_adapter.boxscoretraditionalv3.BoxScoreTraditionalV3")
    def test_returns_dict_with_player_and_team_stats(self, mock_cls, adapter):
        mock_inst = MagicMock()
        mock_inst.get_data_frames.return_value = [
            box_score_player_stats_df(),
            box_score_team_stats_df(),
        ]
        mock_cls.return_value = mock_inst

        result = adapter.get_game_box_score("0022400100")

        assert "PlayerStats" in result
        assert "TeamStats" in result
        assert len(result["PlayerStats"]) == 1
        assert len(result["TeamStats"]) == 1

    @patch("hermes.data.adapters.nba_api_adapter.boxscoretraditionalv3.BoxScoreTraditionalV3")
    def test_uses_rate_limiter(self, mock_cls, adapter, rate_limiter):
        mock_inst = MagicMock()
        mock_inst.get_data_frames.return_value = [
            box_score_player_stats_df(),
            box_score_team_stats_df(),
        ]
        mock_cls.return_value = mock_inst

        adapter.get_game_box_score("0022400100")
        rate_limiter.wait.assert_called()


class TestGetPlayByPlay:
    @patch("hermes.data.adapters.nba_api_adapter.playbyplayv3.PlayByPlayV3")
    def test_returns_dataframe_with_expected_columns(self, mock_cls, adapter):
        mock_inst = MagicMock()
        mock_inst.get_data_frames.return_value = [play_by_play_df()]
        mock_cls.return_value = mock_inst

        result = adapter.get_play_by_play("0022400100")

        assert "actionNumber" in result.columns
        assert "period" in result.columns
        assert "clock" in result.columns
        assert "description" in result.columns
        assert len(result) == 2

    @patch("hermes.data.adapters.nba_api_adapter.playbyplayv3.PlayByPlayV3")
    def test_uses_rate_limiter(self, mock_cls, adapter, rate_limiter):
        mock_inst = MagicMock()
        mock_inst.get_data_frames.return_value = [play_by_play_df()]
        mock_cls.return_value = mock_inst

        adapter.get_play_by_play("0022400100")
        rate_limiter.wait.assert_called()


class TestGetShotChart:
    @patch("hermes.data.adapters.nba_api_adapter.shotchartdetail.ShotChartDetail")
    def test_returns_dataframe_with_expected_columns(self, mock_cls, adapter):
        mock_inst = MagicMock()
        mock_inst.get_data_frames.return_value = [shot_chart_df()]
        mock_cls.return_value = mock_inst

        result = adapter.get_shot_chart("0022400100", player_id=201939)

        assert "GAME_ID" in result.columns
        assert "LOC_X" in result.columns
        assert "LOC_Y" in result.columns
        assert "SHOT_MADE_FLAG" in result.columns
        assert len(result) == 2

    @patch("hermes.data.adapters.nba_api_adapter.shotchartdetail.ShotChartDetail")
    def test_uses_rate_limiter(self, mock_cls, adapter, rate_limiter):
        mock_inst = MagicMock()
        mock_inst.get_data_frames.return_value = [shot_chart_df()]
        mock_cls.return_value = mock_inst

        adapter.get_shot_chart("0022400100")
        rate_limiter.wait.assert_called()


class TestGetLeagueStandings:
    @patch("hermes.data.adapters.nba_api_adapter.leaguestandingsv3.LeagueStandingsV3")
    def test_returns_dataframe_with_expected_columns(self, mock_cls, adapter):
        mock_inst = MagicMock()
        mock_inst.get_data_frames.return_value = [league_standings_df()]
        mock_cls.return_value = mock_inst

        result = adapter.get_league_standings("2024-25")

        assert "TeamID" in result.columns
        assert "WINS" in result.columns
        assert "LOSSES" in result.columns
        assert len(result) == 2

    @patch("hermes.data.adapters.nba_api_adapter.leaguestandingsv3.LeagueStandingsV3")
    def test_uses_rate_limiter(self, mock_cls, adapter, rate_limiter):
        mock_inst = MagicMock()
        mock_inst.get_data_frames.return_value = [league_standings_df()]
        mock_cls.return_value = mock_inst

        adapter.get_league_standings("2024-25")
        rate_limiter.wait.assert_called()


class TestGetSeasonGames:
    @patch("hermes.data.adapters.nba_api_adapter.leaguegamefinder.LeagueGameFinder")
    def test_returns_dataframe_with_game_id(self, mock_cls, adapter):
        mock_inst = MagicMock()
        mock_inst.get_data_frames.return_value = [season_games_df()]
        mock_cls.return_value = mock_inst

        result = adapter.get_season_games("2024-25")

        assert "GAME_ID" in result.columns
        assert len(result) == 2

    @patch("hermes.data.adapters.nba_api_adapter.leaguegamefinder.LeagueGameFinder")
    def test_uses_rate_limiter(self, mock_cls, adapter, rate_limiter):
        mock_inst = MagicMock()
        mock_inst.get_data_frames.return_value = [season_games_df()]
        mock_cls.return_value = mock_inst

        adapter.get_season_games("2024-25")
        rate_limiter.wait.assert_called()


class TestGetSchedule:
    @patch("hermes.data.adapters.nba_api_adapter.scheduleleaguev2.ScheduleLeagueV2")
    def test_returns_dataframe_with_schedule_data(self, mock_cls, adapter):
        mock_inst = MagicMock()
        mock_inst.get_data_frames.return_value = [schedule_df()]
        mock_cls.return_value = mock_inst

        result = adapter.get_schedule("2024-25")

        assert "GAME_ID" in result.columns
        assert len(result) == 2

    @patch("hermes.data.adapters.nba_api_adapter.scheduleleaguev2.ScheduleLeagueV2")
    def test_uses_rate_limiter(self, mock_cls, adapter, rate_limiter):
        mock_inst = MagicMock()
        mock_inst.get_data_frames.return_value = [schedule_df()]
        mock_cls.return_value = mock_inst

        adapter.get_schedule("2024-25")
        rate_limiter.wait.assert_called()
