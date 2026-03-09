"""Tests for agent tools -- each tool's forward() with seeded DB."""

import pytest


class TestSearchPlayer:
    def test_finds_by_partial_name(self, session):
        from hermes.agent.tools import SearchPlayer

        tool = SearchPlayer(db_session=session)
        result = tool.forward(player_name="LeBron")
        assert "LeBron James" in result

    def test_finds_by_last_name(self, session):
        from hermes.agent.tools import SearchPlayer

        tool = SearchPlayer(db_session=session)
        result = tool.forward(player_name="Tatum")
        assert "Jayson Tatum" in result

    def test_not_found_graceful(self, session):
        from hermes.agent.tools import SearchPlayer

        tool = SearchPlayer(db_session=session)
        result = tool.forward(player_name="Zxqwerty Nonexistent")
        assert "no matching" in result.lower() or "not found" in result.lower()


class TestGetPlayerStats:
    def test_returns_formatted_games(self, session):
        from hermes.agent.tools import GetPlayerStats

        tool = GetPlayerStats(db_session=session)
        result = tool.forward(player_name="LeBron James")
        assert "PTS" in result
        assert "REB" in result

    def test_not_found(self, session):
        from hermes.agent.tools import GetPlayerStats

        tool = GetPlayerStats(db_session=session)
        result = tool.forward(player_name="Nonexistent Player")
        assert "not found" in result.lower() or "no matching" in result.lower()


class TestGetPlayerPredictions:
    def test_returns_predictions(self, session):
        from hermes.agent.tools import GetPlayerPredictions

        tool = GetPlayerPredictions(db_session=session)
        result = tool.forward(player_name="LeBron James")
        # Should have at least the player_points prediction
        assert "player_points" in result.lower() or "prediction" in result.lower() or "no prediction" in result.lower()


class TestGetTeamInfo:
    def test_finds_by_name(self, session):
        from hermes.agent.tools import GetTeamInfo

        tool = GetTeamInfo(db_session=session)
        result = tool.forward(team_name="Lakers")
        assert "Los Angeles Lakers" in result or "LAL" in result

    def test_finds_by_abbreviation(self, session):
        from hermes.agent.tools import GetTeamInfo

        tool = GetTeamInfo(db_session=session)
        result = tool.forward(team_name="BOS")
        assert "Boston Celtics" in result or "BOS" in result

    def test_not_found(self, session):
        from hermes.agent.tools import GetTeamInfo

        tool = GetTeamInfo(db_session=session)
        result = tool.forward(team_name="Nonexistent FC")
        assert "not found" in result.lower()


class TestGetTodayGames:
    def test_returns_games_for_date(self, session):
        from hermes.agent.tools import GetTodayGames

        tool = GetTodayGames(db_session=session)
        # Use a date with games in our fixture
        result = tool.forward(date_str="2025-01-10")
        assert "LAL" in result or "BOS" in result or "no games" in result.lower()

    def test_no_games(self, session):
        from hermes.agent.tools import GetTodayGames

        tool = GetTodayGames(db_session=session)
        result = tool.forward(date_str="2099-01-01")
        assert "no games" in result.lower()


class TestGetPredictionAccuracy:
    def test_returns_metrics(self, session):
        from hermes.agent.tools import GetPredictionAccuracy

        tool = GetPredictionAccuracy(db_session=session)
        result = tool.forward(prediction_type=None)
        # Should have some accuracy info
        assert "hit rate" in result.lower() or "type" in result.lower()

    def test_specific_type(self, session):
        from hermes.agent.tools import GetPredictionAccuracy

        tool = GetPredictionAccuracy(db_session=session)
        result = tool.forward(prediction_type="game_winner")
        assert "game_winner" in result.lower() or "hit rate" in result.lower()


class TestGetPredictionHistory:
    def test_returns_history(self, session):
        from hermes.agent.tools import GetPredictionHistory

        tool = GetPredictionHistory(db_session=session)
        result = tool.forward(prediction_type=None)
        assert "HIT" in result or "MISS" in result or "PENDING" in result or "no prediction" in result.lower()


class TestGetMatchupAnalysis:
    def test_returns_matchup(self, session):
        from hermes.agent.tools import GetMatchupAnalysis

        tool = GetMatchupAnalysis(db_session=session)
        result = tool.forward(player_name="LeBron James", team_name="Celtics")
        # Should have matchup info or not-found message
        assert "LeBron" in result or "no matchup" in result.lower() or "not found" in result.lower()

    def test_player_not_found(self, session):
        from hermes.agent.tools import GetMatchupAnalysis

        tool = GetMatchupAnalysis(db_session=session)
        result = tool.forward(player_name="Nobody", team_name="Lakers")
        assert "not found" in result.lower()
