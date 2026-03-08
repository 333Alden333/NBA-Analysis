"""Tests for FEAT-01: Player rolling averages (5/10/20 game windows)."""

import pytest


class TestRollingAvg5GameWindow:
    def test_rolling_avg_5_game_window(self, session, three_game_sequence):
        """5-game rolling average computed correctly."""
        pytest.skip("Awaiting implementation in Plan 02")


class TestRollingAvg10GameWindow:
    def test_rolling_avg_10_game_window(self, session, three_game_sequence):
        """10-game rolling average computed correctly."""
        pytest.skip("Awaiting implementation in Plan 02")


class TestRollingAvg20GameWindow:
    def test_rolling_avg_20_game_window(self, session, three_game_sequence):
        """20-game rolling average computed correctly."""
        pytest.skip("Awaiting implementation in Plan 02")


class TestShortHistory:
    def test_short_history(self, session, three_game_sequence):
        """< window size produces correct partial averages, games_available reflects actual count."""
        pytest.skip("Awaiting implementation in Plan 02")


class TestDnpExcluded:
    def test_dnp_excluded(self, session, three_game_sequence):
        """Games with minutes=0 or None excluded from rolling window."""
        pytest.skip("Awaiting implementation in Plan 02")


class TestRollingPercentages:
    def test_rolling_percentages(self, session, three_game_sequence):
        """FG%, 3P%, FT% rolling averages computed correctly."""
        pytest.skip("Awaiting implementation in Plan 02")
