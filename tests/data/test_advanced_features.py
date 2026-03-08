"""Tests for FEAT-02: Player advanced stats (TS%, USG%, simplified PER)."""

import pytest


class TestTrueShootingPct:
    def test_true_shooting_pct(self, session, three_game_sequence):
        """TS% = PTS / (2 * (FGA + 0.44 * FTA)) computed correctly."""
        pytest.skip("Awaiting implementation in Plan 03")


class TestUsageRate:
    def test_usage_rate(self, session, three_game_sequence):
        """USG% formula correct."""
        pytest.skip("Awaiting implementation in Plan 03")


class TestSimplifiedPer:
    def test_simplified_per(self, session, three_game_sequence):
        """Simplified PER formula correct."""
        pytest.skip("Awaiting implementation in Plan 03")


class TestZeroDivision:
    def test_zero_division(self, session, three_game_sequence):
        """Zero minutes, zero FGA, zero team stats all return 0.0 (not crash)."""
        pytest.skip("Awaiting implementation in Plan 03")


class TestAdvancedStatsStored:
    def test_advanced_stats_stored(self, session, three_game_sequence):
        """Computed stats persisted to PlayerAdvancedStats table."""
        pytest.skip("Awaiting implementation in Plan 03")
