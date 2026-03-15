"""Tests for NbaInjuriesAdapter."""

from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

from sportsprediction.data.adapters.base import InjuryDataAdapter
from sportsprediction.data.adapters.injuries_adapter import NbaInjuriesAdapter


class TestNbaInjuriesAdapter:
    def test_is_instance_of_injury_data_adapter(self):
        adapter = NbaInjuriesAdapter()
        assert isinstance(adapter, InjuryDataAdapter)

    @patch("sportsprediction.data.adapters.injuries_adapter.injury")
    def test_get_current_injuries_returns_dataframe(self, mock_injury_mod):
        mock_injury_mod.get_reportdata.return_value = pd.DataFrame(
            {
                "Player Name": ["LeBron James"],
                "Team": ["LAL"],
                "Current Status": ["Out"],
                "Reason": ["Ankle"],
                "Game Date": ["2026-03-08"],
                "Game Time": ["7:00 PM"],
                "Matchup": ["LAL vs GSW"],
            }
        )
        adapter = NbaInjuriesAdapter()
        df = adapter.get_current_injuries()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        for col in ["Player Name", "Team", "Current Status", "Reason"]:
            assert col in df.columns

    @patch("sportsprediction.data.adapters.injuries_adapter.injury")
    def test_handles_empty_report(self, mock_injury_mod):
        mock_injury_mod.get_reportdata.return_value = pd.DataFrame()
        adapter = NbaInjuriesAdapter()
        df = adapter.get_current_injuries()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    @patch("sportsprediction.data.adapters.injuries_adapter.injury", None)
    def test_handles_missing_java_gracefully(self):
        """When nbainjuries is not available, return empty DataFrame."""
        adapter = NbaInjuriesAdapter()
        df = adapter.get_current_injuries()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
