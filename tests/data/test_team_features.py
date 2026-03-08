"""Tests for FEAT-04: Team features (pace, ratings, rest days)."""

import pytest


class TestPaceComputed:
    def test_pace_computed(self, session, three_game_sequence):
        """Pace formula correct."""
        pytest.skip("Awaiting implementation in Plan 04")


class TestOffensiveRating:
    def test_offensive_rating(self, session, three_game_sequence):
        """ORtg per 100 possessions."""
        pytest.skip("Awaiting implementation in Plan 04")


class TestDefensiveRating:
    def test_defensive_rating(self, session, three_game_sequence):
        """DRtg per 100 possessions."""
        pytest.skip("Awaiting implementation in Plan 04")


class TestRestDays:
    def test_rest_days(self, session, three_game_sequence):
        """Days between games calculated, season opener defaults to 3."""
        pytest.skip("Awaiting implementation in Plan 04")


class TestSeasonWinPct:
    def test_season_win_pct(self, session, three_game_sequence):
        """Rolling win percentage correct."""
        pytest.skip("Awaiting implementation in Plan 04")
