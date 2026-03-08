"""Tests for FEAT-05: Temporal leakage prevention across all feature types."""

import pytest


class TestRollingStatsNoLeakage:
    def test_rolling_stats_no_leakage(self, session, three_game_sequence):
        """Rolling stat for game on date D uses only data from before D."""
        pytest.skip("Awaiting implementation in Plan 02/03/04")


class TestAdvancedStatsNoLeakage:
    def test_advanced_stats_no_leakage(self, session, three_game_sequence):
        """Team aggregates for advanced stats exclude current game."""
        pytest.skip("Awaiting implementation in Plan 02/03/04")


class TestMatchupStatsNoLeakage:
    def test_matchup_stats_no_leakage(self, session, three_game_sequence):
        """Matchup history excludes current game."""
        pytest.skip("Awaiting implementation in Plan 02/03/04")


class TestTeamFeaturesNoLeakage:
    def test_team_features_no_leakage(self, session, three_game_sequence):
        """Team features exclude current game."""
        pytest.skip("Awaiting implementation in Plan 02/03/04")


class TestFullPipelineNoLeakage:
    def test_full_pipeline_no_leakage(self, session, three_game_sequence):
        """End-to-end: compute all features, verify temporal boundaries."""
        pytest.skip("Awaiting implementation in Plan 02/03/04")
