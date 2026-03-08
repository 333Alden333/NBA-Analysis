"""Tests for FEAT-02: Player advanced stats (TS%, USG%, simplified PER)."""

import datetime

import pytest

from hermes.data.features.advanced import (
    compute_advanced_stats,
    compute_true_shooting_pct,
    compute_usage_rate,
    compute_simplified_per,
)
from hermes.data.models import PlayerAdvancedStats


class TestTrueShootingPct:
    def test_true_shooting_pct(self):
        """TS% = PTS / (2 * (FGA + 0.44 * FTA)) computed correctly."""
        # PTS=25, FGA=18, FTA=6: TS% = 25 / (2 * (18 + 0.44*6)) = 25 / (2 * 20.64) = 25/41.28
        result = compute_true_shooting_pct(points=25, fga=18, fta=6)
        expected = 25.0 / (2.0 * (18.0 + 0.44 * 6.0))
        assert result == pytest.approx(expected, abs=1e-4)


class TestUsageRate:
    def test_usage_rate(self):
        """USG% = 100 * ((FGA + 0.44*FTA + TOV) * (TmMP/5)) / (MP * (TmFGA + 0.44*TmFTA + TmTOV))."""
        # Known inputs
        fga, fta, tov, minutes = 15, 4, 3, 32.0
        team_fga, team_fta, team_tov, team_minutes = 85, 22, 14, 240.0

        result = compute_usage_rate(
            fga=fga, fta=fta, tov=tov, minutes=minutes,
            team_fga=team_fga, team_fta=team_fta,
            team_tov=team_tov, team_minutes=team_minutes,
        )

        numerator = (fga + 0.44 * fta + tov) * (team_minutes / 5.0)
        denominator = minutes * (team_fga + 0.44 * team_fta + team_tov)
        expected = 100.0 * numerator / denominator
        assert result == pytest.approx(expected, abs=1e-4)


class TestSimplifiedPer:
    def test_simplified_per(self):
        """Simplified PER = (positive_contributions - negative_contributions) / minutes * 15."""
        result = compute_simplified_per(
            points=20, rebounds=8, assists=5, steals=2, blocks=1,
            turnovers=3, fgm=8, fga=16, ftm=4, fta=5, minutes=32.0,
        )
        # positive = points + rebounds + assists + steals + blocks = 20+8+5+2+1 = 36
        # missed_fg = fga - fgm = 16 - 8 = 8
        # missed_ft = fta - ftm = 5 - 4 = 1
        # negative = turnovers + missed_fg + missed_ft = 3 + 8 + 1 = 12
        # PER = (36 - 12) / 32 * 15 = 24/32*15 = 11.25
        assert result == pytest.approx(11.25, abs=1e-4)


class TestZeroDivision:
    def test_zero_division(self):
        """Zero minutes, zero FGA, zero team stats all return 0.0 (not crash)."""
        assert compute_true_shooting_pct(points=0, fga=0, fta=0) == 0.0
        assert compute_usage_rate(
            fga=0, fta=0, tov=0, minutes=0,
            team_fga=0, team_fta=0, team_tov=0, team_minutes=0,
        ) == 0.0
        assert compute_simplified_per(
            points=0, rebounds=0, assists=0, steals=0, blocks=0,
            turnovers=0, fgm=0, fga=0, ftm=0, fta=0, minutes=0,
        ) == 0.0


class TestAdvancedStatsStored:
    def test_advanced_stats_stored(self, session, three_game_sequence):
        """Computed stats persisted to PlayerAdvancedStats table."""
        compute_advanced_stats(session, player_id=101)

        rows = session.query(PlayerAdvancedStats).filter_by(player_id=101).all()
        # Should have 3 rows (one per game)
        assert len(rows) == 3

        # Each row should have non-None TS%, USG%, PER
        for row in rows:
            assert row.true_shooting_pct is not None
            assert row.usage_rate is not None
            assert row.simplified_per is not None
            assert row.team_fga is not None
            assert row.team_minutes is not None
