"""Tests for abstract adapter interfaces."""

import pytest
from typing import Any

import pandas as pd

from sportsprediction.data.adapters.base import NBADataAdapter, InjuryDataAdapter


class TestNBADataAdapterAbstract:
    """NBADataAdapter cannot be instantiated directly."""

    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            NBADataAdapter()

    def test_defines_get_player_info(self):
        assert hasattr(NBADataAdapter, "get_player_info")

    def test_defines_get_player_game_log(self):
        assert hasattr(NBADataAdapter, "get_player_game_log")

    def test_defines_get_game_box_score(self):
        assert hasattr(NBADataAdapter, "get_game_box_score")

    def test_defines_get_play_by_play(self):
        assert hasattr(NBADataAdapter, "get_play_by_play")

    def test_defines_get_shot_chart(self):
        assert hasattr(NBADataAdapter, "get_shot_chart")

    def test_defines_get_league_standings(self):
        assert hasattr(NBADataAdapter, "get_league_standings")

    def test_defines_get_season_games(self):
        assert hasattr(NBADataAdapter, "get_season_games")

    def test_defines_get_schedule(self):
        assert hasattr(NBADataAdapter, "get_schedule")

    def test_has_eight_abstract_methods(self):
        # All 8 methods should be abstract
        abstract_methods = getattr(NBADataAdapter, "__abstractmethods__", set())
        assert len(abstract_methods) == 8


class TestInjuryDataAdapterAbstract:
    """InjuryDataAdapter cannot be instantiated directly."""

    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            InjuryDataAdapter()

    def test_defines_get_current_injuries(self):
        assert hasattr(InjuryDataAdapter, "get_current_injuries")

    def test_has_one_abstract_method(self):
        abstract_methods = getattr(InjuryDataAdapter, "__abstractmethods__", set())
        assert len(abstract_methods) == 1


class TestConcreteSubclass:
    """A concrete subclass implementing all methods CAN be instantiated."""

    def test_concrete_nba_adapter(self):
        class ConcreteNBA(NBADataAdapter):
            def get_player_info(self, player_id: int) -> dict[str, Any]:
                return {}

            def get_player_game_log(self, player_id: int, season: str) -> pd.DataFrame:
                return pd.DataFrame()

            def get_game_box_score(self, game_id: str) -> dict[str, pd.DataFrame]:
                return {}

            def get_play_by_play(self, game_id: str) -> pd.DataFrame:
                return pd.DataFrame()

            def get_shot_chart(self, game_id: str, player_id: int | None = None) -> pd.DataFrame:
                return pd.DataFrame()

            def get_league_standings(self, season: str) -> pd.DataFrame:
                return pd.DataFrame()

            def get_season_games(self, season: str) -> pd.DataFrame:
                return pd.DataFrame()

            def get_schedule(self, season: str) -> pd.DataFrame:
                return pd.DataFrame()

        adapter = ConcreteNBA()
        assert adapter is not None

    def test_concrete_injury_adapter(self):
        class ConcreteInjury(InjuryDataAdapter):
            def get_current_injuries(self) -> pd.DataFrame:
                return pd.DataFrame()

        adapter = ConcreteInjury()
        assert adapter is not None
