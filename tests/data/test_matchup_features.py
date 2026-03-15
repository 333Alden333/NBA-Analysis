"""Tests for FEAT-03: Matchup features (player vs specific team history)."""

import datetime

import pytest

from sportsprediction.data.features.matchup import compute_matchup_stats, compute_matchup_stats_for_games
from sportsprediction.data.models import MatchupStats


class TestMatchupAvgComputed:
    def test_matchup_avg_computed(self, session, make_team, make_player, make_game, make_box_score):
        """Player with 4 games vs Team B scoring [20,25,30,35] -> matchup_avg_points for game 5 = 27.5."""
        make_team(session, team_id=1, full_name="Team A")
        make_team(session, team_id=2, full_name="Team B")
        make_player(session, player_id=101, team_id=1, full_name="Player A")

        # 4 historical games vs Team B
        dates_and_scores = [
            ("0022400001", datetime.date(2024, 1, 1), 20, 5, 3, 8, 16, 4.0),
            ("0022400002", datetime.date(2024, 1, 5), 25, 7, 4, 10, 20, 6.0),
            ("0022400003", datetime.date(2024, 1, 10), 30, 8, 5, 12, 22, 8.0),
            ("0022400004", datetime.date(2024, 1, 15), 35, 10, 6, 14, 25, 10.0),
        ]
        for gid, gdate, pts, reb, ast, fgm, fga, pm in dates_and_scores:
            make_game(session, game_id=gid, game_date=gdate, home_team_id=1, away_team_id=2)
            make_box_score(session, game_id=gid, player_id=101, team_id=1,
                           points=pts, rebounds=reb, assists=ast, fgm=fgm, fga=fga, plus_minus=pm)

        # Game 5 - the one we compute matchup stats FOR
        make_game(session, game_id="0022400005", game_date=datetime.date(2024, 1, 20),
                  home_team_id=1, away_team_id=2)
        make_box_score(session, game_id="0022400005", player_id=101, team_id=1, points=22)

        compute_matchup_stats(session, player_id=101)

        ms = session.query(MatchupStats).filter_by(
            player_id=101, game_id="0022400005"
        ).one()

        assert ms.has_matchup_history is True
        assert ms.matchup_games_played == 4
        assert ms.matchup_avg_points == pytest.approx(27.5, abs=0.01)
        assert ms.matchup_avg_rebounds == pytest.approx(7.5, abs=0.01)
        assert ms.matchup_avg_assists == pytest.approx(4.5, abs=0.01)
        # fg_pct: per game [8/16=0.5, 10/20=0.5, 12/22=0.545, 14/25=0.56], avg ~0.526
        expected_fg_pcts = [8 / 16, 10 / 20, 12 / 22, 14 / 25]
        assert ms.matchup_avg_fg_pct == pytest.approx(
            sum(expected_fg_pcts) / len(expected_fg_pcts), abs=0.01
        )
        assert ms.matchup_avg_plus_minus == pytest.approx(7.0, abs=0.01)


class TestMatchupDiffComputed:
    def test_matchup_diff_computed(self, session, make_team, make_player, make_game, make_box_score):
        """If player's overall avg is different from matchup avg, diff captures it."""
        make_team(session, team_id=1, full_name="Team A")
        make_team(session, team_id=2, full_name="Team B")
        make_team(session, team_id=3, full_name="Team C")
        make_player(session, player_id=101, team_id=1, full_name="Player A")

        # 3 games vs Team B (player scores high: 30 each)
        for i in range(3):
            gid = f"002240010{i}"
            gdate = datetime.date(2024, 1, 1 + i * 3)
            make_game(session, game_id=gid, game_date=gdate, home_team_id=1, away_team_id=2)
            make_box_score(session, game_id=gid, player_id=101, team_id=1,
                           points=30, rebounds=10, assists=8, fgm=12, fga=20, plus_minus=10.0)

        # 3 games vs Team C (player scores low: 10 each)
        for i in range(3):
            gid = f"002240020{i}"
            gdate = datetime.date(2024, 2, 1 + i * 3)
            make_game(session, game_id=gid, game_date=gdate, home_team_id=1, away_team_id=3)
            make_box_score(session, game_id=gid, player_id=101, team_id=1,
                           points=10, rebounds=4, assists=2, fgm=4, fga=15, plus_minus=-5.0)

        # Game 7 vs Team B -> matchup avg should be 30, overall avg ~20
        make_game(session, game_id="0022400300", game_date=datetime.date(2024, 3, 1),
                  home_team_id=1, away_team_id=2)
        make_box_score(session, game_id="0022400300", player_id=101, team_id=1, points=25)

        compute_matchup_stats(session, player_id=101)

        ms = session.query(MatchupStats).filter_by(
            player_id=101, game_id="0022400300"
        ).one()

        assert ms.has_matchup_history is True
        # Matchup avg points vs Team B = 30.0
        assert ms.matchup_avg_points == pytest.approx(30.0, abs=0.01)
        # Overall avg points (6 games: 30,30,30,10,10,10) = 20.0
        # Diff = 30.0 - 20.0 = 10.0
        assert ms.matchup_diff_points == pytest.approx(10.0, abs=0.01)


class TestNoHistory:
    def test_no_history(self, session, make_team, make_player, make_game, make_box_score):
        """< 3 games vs opponent returns NULL columns with has_matchup_history=False."""
        make_team(session, team_id=1, full_name="Team A")
        make_team(session, team_id=2, full_name="Team B")
        make_player(session, player_id=101, team_id=1, full_name="Player A")

        # Only 2 games vs Team B (below minimum threshold of 3)
        for i in range(2):
            gid = f"002240010{i}"
            gdate = datetime.date(2024, 1, 1 + i * 3)
            make_game(session, game_id=gid, game_date=gdate, home_team_id=1, away_team_id=2)
            make_box_score(session, game_id=gid, player_id=101, team_id=1, points=20)

        # Game 3 - only 2 prior games
        make_game(session, game_id="0022400103", game_date=datetime.date(2024, 1, 10),
                  home_team_id=1, away_team_id=2)
        make_box_score(session, game_id="0022400103", player_id=101, team_id=1, points=22)

        compute_matchup_stats(session, player_id=101)

        ms = session.query(MatchupStats).filter_by(
            player_id=101, game_id="0022400103"
        ).one()

        assert ms.has_matchup_history is False
        assert ms.matchup_avg_points is None
        assert ms.matchup_avg_rebounds is None
        assert ms.matchup_avg_assists is None
        assert ms.matchup_avg_fg_pct is None
        assert ms.matchup_avg_plus_minus is None
        assert ms.matchup_diff_points is None


class TestMinimumThreshold:
    def test_minimum_threshold(self, session, make_team, make_player, make_game, make_box_score):
        """Exactly 3 games vs opponent -> has_matchup_history=True, matchup_games_played=3."""
        make_team(session, team_id=1, full_name="Team A")
        make_team(session, team_id=2, full_name="Team B")
        make_player(session, player_id=101, team_id=1, full_name="Player A")

        # 3 games vs Team B
        for i in range(3):
            gid = f"002240010{i}"
            gdate = datetime.date(2024, 1, 1 + i * 5)
            make_game(session, game_id=gid, game_date=gdate, home_team_id=1, away_team_id=2)
            make_box_score(session, game_id=gid, player_id=101, team_id=1,
                           points=20 + i * 5, rebounds=5 + i, assists=3 + i,
                           fgm=8 + i, fga=16 + i, plus_minus=float(i * 2))

        # Game 4 - has exactly 3 prior matchups
        make_game(session, game_id="0022400200", game_date=datetime.date(2024, 2, 1),
                  home_team_id=1, away_team_id=2)
        make_box_score(session, game_id="0022400200", player_id=101, team_id=1, points=30)

        compute_matchup_stats(session, player_id=101)

        ms = session.query(MatchupStats).filter_by(
            player_id=101, game_id="0022400200"
        ).one()

        assert ms.has_matchup_history is True
        assert ms.matchup_games_played == 3
        assert ms.matchup_avg_points is not None


class TestMatchupLookbackWindow:
    def test_matchup_lookback_window(self, session, make_team, make_player, make_game, make_box_score):
        """Games older than 3 seasons excluded from matchup computation."""
        make_team(session, team_id=1, full_name="Team A")
        make_team(session, team_id=2, full_name="Team B")
        make_player(session, player_id=101, team_id=1, full_name="Player A")

        # 3 old games (4 years ago) -- should be excluded from lookback
        for i in range(3):
            gid = f"002200010{i}"
            gdate = datetime.date(2020, 1, 1 + i * 5)
            make_game(session, game_id=gid, game_date=gdate, home_team_id=1, away_team_id=2,
                      season="2019-20")
            make_box_score(session, game_id=gid, player_id=101, team_id=1, points=50)

        # 2 recent games (within lookback) -- not enough for threshold
        for i in range(2):
            gid = f"002240010{i}"
            gdate = datetime.date(2024, 1, 1 + i * 5)
            make_game(session, game_id=gid, game_date=gdate, home_team_id=1, away_team_id=2,
                      season="2023-24")
            make_box_score(session, game_id=gid, player_id=101, team_id=1, points=20)

        # Current game -- old games excluded, only 2 recent => no history
        make_game(session, game_id="0022400200", game_date=datetime.date(2024, 2, 1),
                  home_team_id=1, away_team_id=2, season="2023-24")
        make_box_score(session, game_id="0022400200", player_id=101, team_id=1, points=22)

        compute_matchup_stats(session, player_id=101)

        ms = session.query(MatchupStats).filter_by(
            player_id=101, game_id="0022400200"
        ).one()

        # Old games excluded -> only 2 recent matchups -> below threshold
        assert ms.has_matchup_history is False
        assert ms.matchup_games_played == 2
        assert ms.matchup_avg_points is None
