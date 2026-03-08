"""Tests for FEAT-01: Player rolling averages (5/10/20 game windows)."""

import datetime

import pytest

from hermes.data.features.rolling import compute_rolling_stats
from hermes.data.models import PlayerRollingStats


def _create_games_with_points(session, make_team, make_player, make_game, make_box_score,
                               points_list, player_id=101, team_id=1):
    """Helper: create N games with specific points for a single player."""
    make_team(session, team_id=team_id, full_name="Home Team")
    make_team(session, team_id=team_id + 1, full_name="Away Team")
    make_player(session, player_id=player_id, team_id=team_id, full_name="Test Player")

    game_ids = []
    for i, pts in enumerate(points_list):
        gid = f"00224{i:05d}"
        gdate = datetime.date(2024, 1, 1) + datetime.timedelta(days=i * 2)
        make_game(session, game_id=gid, game_date=gdate, home_team_id=team_id, away_team_id=team_id + 1)
        make_box_score(session, game_id=gid, player_id=player_id, team_id=team_id,
                       points=pts, minutes=30.0, rebounds=5, assists=3,
                       fgm=pts // 3, fga=pts // 2 + 1)
        game_ids.append(gid)
    return game_ids


class TestRollingAvg5GameWindow:
    def test_rolling_avg_5_game_window(self, session, make_team, make_player, make_game, make_box_score):
        """5-game rolling average computed correctly with shift-by-1 temporal discipline."""
        # 6 games with known points: [10, 20, 30, 40, 50, 60]
        points = [10, 20, 30, 40, 50, 60]
        _create_games_with_points(session, make_team, make_player, make_game, make_box_score, points)

        compute_rolling_stats(session, player_id=101)

        # Game 6 (index 5): rolling_avg_5 should use games 2-5 (shifted by 1)
        # Prior 5 games before game 6: games 1-5 with points [10,20,30,40,50]
        # Last 5 of those: [10,20,30,40,50] -> mean = 30.0
        game6_id = "00224" + f"{5:05d}"
        row = session.query(PlayerRollingStats).filter_by(
            player_id=101, game_id=game6_id
        ).one()
        assert row.points_avg_5 == pytest.approx(30.0, abs=0.01)

        # Game 1 should have no prior data (None or NaN-like)
        game1_id = "00224" + f"{0:05d}"
        row1 = session.query(PlayerRollingStats).filter_by(
            player_id=101, game_id=game1_id
        ).one()
        assert row1.points_avg_5 is None


class TestRollingAvg10GameWindow:
    def test_rolling_avg_10_game_window(self, session, make_team, make_player, make_game, make_box_score):
        """With < 10 games available, uses all available; games_available_10 reflects actual count."""
        # 6 games -- fewer than 10 available
        points = [10, 20, 30, 40, 50, 60]
        _create_games_with_points(session, make_team, make_player, make_game, make_box_score, points)

        compute_rolling_stats(session, player_id=101)

        # Game 6: prior 5 games -> games_available_10 = 5 (not 10)
        game6_id = "00224" + f"{5:05d}"
        row = session.query(PlayerRollingStats).filter_by(
            player_id=101, game_id=game6_id
        ).one()
        assert row.games_available_10 == 5
        # 10-game avg with only 5 games = mean of all 5 prior: mean([10,20,30,40,50]) = 30.0
        assert row.points_avg_10 == pytest.approx(30.0, abs=0.01)


class TestRollingAvg20GameWindow:
    def test_rolling_avg_20_game_window(self, session, make_team, make_player, make_game, make_box_score):
        """With exactly 20 prior games, window is full; games_available_20 = 20."""
        # Create 21 games so game 21 has exactly 20 prior
        points = list(range(1, 22))  # [1, 2, 3, ..., 21]
        _create_games_with_points(session, make_team, make_player, make_game, make_box_score, points)

        compute_rolling_stats(session, player_id=101)

        game21_id = "00224" + f"{20:05d}"
        row = session.query(PlayerRollingStats).filter_by(
            player_id=101, game_id=game21_id
        ).one()
        assert row.games_available_20 == 20
        # Prior 20 games: [1..20], mean = 10.5
        assert row.points_avg_20 == pytest.approx(10.5, abs=0.01)


class TestShortHistory:
    def test_short_history(self, session, make_team, make_player, make_game, make_box_score):
        """Player with 2 prior games: avg_5 = mean of those 2, games_available_5 = 2."""
        points = [10, 20, 30]  # 3 games total, game 3 has 2 prior
        _create_games_with_points(session, make_team, make_player, make_game, make_box_score, points)

        compute_rolling_stats(session, player_id=101)

        game3_id = "00224" + f"{2:05d}"
        row = session.query(PlayerRollingStats).filter_by(
            player_id=101, game_id=game3_id
        ).one()
        assert row.games_available_5 == 2
        assert row.points_avg_5 == pytest.approx(15.0, abs=0.01)  # mean([10, 20])


class TestDnpExcluded:
    def test_dnp_excluded(self, session, make_team, make_player, make_game, make_box_score):
        """Games with minutes=0 or None excluded from rolling window."""
        make_team(session, team_id=1, full_name="Home Team")
        make_team(session, team_id=2, full_name="Away Team")
        make_player(session, player_id=101, team_id=1, full_name="Test Player")

        # Game 1: played, 20 pts
        make_game(session, game_id="G001", game_date=datetime.date(2024, 1, 1),
                  home_team_id=1, away_team_id=2)
        make_box_score(session, game_id="G001", player_id=101, team_id=1,
                       points=20, minutes=30.0)

        # Game 2: DNP (minutes=0)
        make_game(session, game_id="G002", game_date=datetime.date(2024, 1, 3),
                  home_team_id=1, away_team_id=2)
        make_box_score(session, game_id="G002", player_id=101, team_id=1,
                       points=0, minutes=0)

        # Game 3: DNP (minutes=None)
        make_game(session, game_id="G003", game_date=datetime.date(2024, 1, 5),
                  home_team_id=1, away_team_id=2)
        make_box_score(session, game_id="G003", player_id=101, team_id=1,
                       points=0, minutes=None)

        # Game 4: played, 40 pts
        make_game(session, game_id="G004", game_date=datetime.date(2024, 1, 7),
                  home_team_id=1, away_team_id=2)
        make_box_score(session, game_id="G004", player_id=101, team_id=1,
                       points=40, minutes=32.0)

        compute_rolling_stats(session, player_id=101)

        # Game 4 rolling should only see game 1 as prior (DNPs excluded)
        row = session.query(PlayerRollingStats).filter_by(
            player_id=101, game_id="G004"
        ).one()
        assert row.games_available_5 == 1
        assert row.points_avg_5 == pytest.approx(20.0, abs=0.01)

        # DNP games should NOT have rolling stats rows
        dnp_rows = session.query(PlayerRollingStats).filter(
            PlayerRollingStats.game_id.in_(["G002", "G003"])
        ).all()
        assert len(dnp_rows) == 0


class TestRollingPercentages:
    def test_rolling_percentages(self, session, make_team, make_player, make_game, make_box_score):
        """FG% rolling averages are mean of per-game FG% values."""
        make_team(session, team_id=1, full_name="Home Team")
        make_team(session, team_id=2, full_name="Away Team")
        make_player(session, player_id=101, team_id=1, full_name="Test Player")

        # Game 1: 4/10 = 0.4 FG%
        make_game(session, game_id="G001", game_date=datetime.date(2024, 1, 1),
                  home_team_id=1, away_team_id=2)
        make_box_score(session, game_id="G001", player_id=101, team_id=1,
                       fgm=4, fga=10, minutes=30.0)

        # Game 2: 6/12 = 0.5 FG%
        make_game(session, game_id="G002", game_date=datetime.date(2024, 1, 3),
                  home_team_id=1, away_team_id=2)
        make_box_score(session, game_id="G002", player_id=101, team_id=1,
                       fgm=6, fga=12, minutes=28.0)

        # Game 3: 8/16 = 0.5 FG%
        make_game(session, game_id="G003", game_date=datetime.date(2024, 1, 5),
                  home_team_id=1, away_team_id=2)
        make_box_score(session, game_id="G003", player_id=101, team_id=1,
                       fgm=8, fga=16, minutes=32.0)

        compute_rolling_stats(session, player_id=101)

        # Game 3 rolling: prior games are [G001, G002] -> FG% = [0.4, 0.5] -> mean = 0.45
        row = session.query(PlayerRollingStats).filter_by(
            player_id=101, game_id="G003"
        ).one()
        assert row.fg_pct_avg_5 == pytest.approx(0.45, abs=0.01)
