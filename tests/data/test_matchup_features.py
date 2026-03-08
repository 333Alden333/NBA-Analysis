"""Tests for FEAT-03: Matchup features (player vs specific team history)."""

import pytest


class TestMatchupAvgComputed:
    def test_matchup_avg_computed(self, session, three_game_sequence):
        """Player's average stats vs specific team computed."""
        pytest.skip("Awaiting implementation in Plan 03")


class TestMatchupDiffComputed:
    def test_matchup_diff_computed(self, session, three_game_sequence):
        """Difference from player's overall average."""
        pytest.skip("Awaiting implementation in Plan 03")


class TestNoHistory:
    def test_no_history(self, session, three_game_sequence):
        """< 3 games returns NULL columns with has_matchup_history=False."""
        pytest.skip("Awaiting implementation in Plan 03")


class TestMinimumThreshold:
    def test_minimum_threshold(self, session, three_game_sequence):
        """Exactly 3 games produces valid matchup features."""
        pytest.skip("Awaiting implementation in Plan 03")


class TestMatchupLookbackWindow:
    def test_matchup_lookback_window(self, session, three_game_sequence):
        """Only uses last 2-3 seasons of data."""
        pytest.skip("Awaiting implementation in Plan 03")
