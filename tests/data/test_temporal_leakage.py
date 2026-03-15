"""Tests for FEAT-05: Temporal leakage prevention across all feature types.

Each test creates a sequence of games with KNOWN, DISTINCT stat values,
runs feature computation, and verifies that features for a mid-sequence
game use ONLY data from prior games (never the current game or future games).
"""

import datetime

import pytest

from sportsprediction.data.models import (
    Player, Team, Game, BoxScore,
    PlayerRollingStats, PlayerAdvancedStats, MatchupStats, TeamFeatures,
)
from sportsprediction.data.features.rolling import compute_rolling_stats
from sportsprediction.data.features.advanced import compute_advanced_stats
from sportsprediction.data.features.matchup import compute_matchup_stats
from sportsprediction.data.features.team import compute_team_features
from sportsprediction.data.features.engine import compute_all_features_for_games
from sportsprediction.data.features.temporal import validate_no_leakage


def _setup_teams_and_players(session, num_teams=2, players_per_team=2):
    """Create teams and players. Returns (team_ids, player_map)."""
    team_ids = []
    player_map = {}  # team_id -> [player_ids]

    # Create teams first (FK dependency: players reference teams)
    for t in range(num_teams):
        tid = t + 1
        team = Team(team_id=tid, full_name=f"Team {tid}")
        session.add(team)
        team_ids.append(tid)
        player_map[tid] = []

    session.flush()  # Teams must exist before players (FK constraint)

    for tid in team_ids:
        for p in range(players_per_team):
            pid = tid * 100 + p + 1
            player = Player(player_id=pid, team_id=tid, full_name=f"Player {pid}")
            session.add(player)
            player_map[tid].append(pid)

    session.flush()
    return team_ids, player_map


def _create_game(session, game_id, game_date, home_tid, away_tid,
                 home_score=100, away_score=95, season="2024-25"):
    """Create a game record."""
    game = Game(
        game_id=game_id, game_date=game_date,
        home_team_id=home_tid, away_team_id=away_tid,
        home_score=home_score, away_score=away_score, season=season,
    )
    session.add(game)
    session.flush()
    return game


def _create_box_score(session, game_id, player_id, team_id, points=10,
                      rebounds=5, assists=3, minutes=25.0, fgm=4, fga=10,
                      fg3m=1, fg3a=3, ftm=1, fta=2, steals=1, blocks=1,
                      turnovers=2, plus_minus=5.0, offensive_rebounds=1,
                      defensive_rebounds=4, personal_fouls=2, **kwargs):
    """Create a box score record."""
    bs = BoxScore(
        game_id=game_id, player_id=player_id, team_id=team_id,
        points=points, rebounds=rebounds, assists=assists, minutes=minutes,
        fgm=fgm, fga=fga, fg3m=fg3m, fg3a=fg3a, ftm=ftm, fta=fta,
        steals=steals, blocks=blocks, turnovers=turnovers,
        plus_minus=plus_minus, offensive_rebounds=offensive_rebounds,
        defensive_rebounds=defensive_rebounds, personal_fouls=personal_fouls,
        **kwargs,
    )
    session.add(bs)
    session.flush()
    return bs


class TestRollingStatsNoLeakage:
    def test_rolling_stats_no_leakage(self, session):
        """Rolling stat for game 3 should use only games 1-2 data (not 3,4,5).

        Player scores 10, 20, 30, 40, 50 in games 1-5.
        Rolling avg_5 for game 3 should be mean(10, 20) = 15.0 (shift-by-1).
        """
        team_ids, player_map = _setup_teams_and_players(session, 2, 1)
        pid = player_map[1][0]

        point_values = [10, 20, 30, 40, 50]
        dates = [datetime.date(2024, 1, d) for d in [1, 3, 5, 7, 9]]

        for i in range(5):
            gid = f"002240000{i+1}"
            _create_game(session, gid, dates[i], 1, 2)
            _create_box_score(session, gid, pid, 1, points=point_values[i], minutes=30.0)
            # Need at least one box score for away team
            _create_box_score(session, gid, player_map[2][0], 2, points=15, minutes=30.0)

        compute_rolling_stats(session, player_id=pid)
        session.flush()

        # Check game 3 (index 2): rolling avg should use only games 1 and 2
        rs_game3 = session.query(PlayerRollingStats).filter_by(
            player_id=pid, game_id="0022400003"
        ).first()
        assert rs_game3 is not None

        # points_avg_5 for game 3 should be mean of games 1,2 = (10+20)/2 = 15.0
        assert rs_game3.points_avg_5 == pytest.approx(15.0)
        assert rs_game3.games_available_5 == 2

        # Check game 1: should have None (no prior games)
        rs_game1 = session.query(PlayerRollingStats).filter_by(
            player_id=pid, game_id="0022400001"
        ).first()
        assert rs_game1 is not None
        assert rs_game1.points_avg_5 is None  # No prior games

        # Check game 5: should use games 1-4 only
        rs_game5 = session.query(PlayerRollingStats).filter_by(
            player_id=pid, game_id="0022400005"
        ).first()
        assert rs_game5 is not None
        # mean(10, 20, 30, 40) = 25.0
        assert rs_game5.points_avg_5 == pytest.approx(25.0)
        assert rs_game5.games_available_5 == 4


class TestAdvancedStatsNoLeakage:
    def test_advanced_stats_no_leakage(self, session):
        """Advanced stats for game 2 use game 2's own box score (per-game stats).

        Key test: team aggregates come from the correct game's data, not future.
        """
        team_ids, player_map = _setup_teams_and_players(session, 2, 2)
        pid1 = player_map[1][0]  # Player on team 1
        pid2 = player_map[1][1]  # Teammate

        # Game 1: player scores 20 pts on 8/16 FGA, 4/4 FTA
        gid1 = "0022400001"
        _create_game(session, gid1, datetime.date(2024, 1, 1), 1, 2)
        _create_box_score(session, gid1, pid1, 1, points=20, fgm=8, fga=16, ftm=4, fta=4, minutes=30.0)
        _create_box_score(session, gid1, pid2, 1, points=15, fgm=6, fga=12, ftm=3, fta=4, minutes=28.0)
        _create_box_score(session, gid1, player_map[2][0], 2, points=10, minutes=25.0)
        _create_box_score(session, gid1, player_map[2][1], 2, points=12, minutes=25.0)

        # Game 2: player scores 30 pts on 12/20 FGA, 6/8 FTA
        gid2 = "0022400002"
        _create_game(session, gid2, datetime.date(2024, 1, 3), 1, 2)
        _create_box_score(session, gid2, pid1, 1, points=30, fgm=12, fga=20, ftm=6, fta=8, minutes=35.0)
        _create_box_score(session, gid2, pid2, 1, points=10, fgm=4, fga=10, ftm=2, fta=3, minutes=25.0)
        _create_box_score(session, gid2, player_map[2][0], 2, points=8, minutes=20.0)
        _create_box_score(session, gid2, player_map[2][1], 2, points=14, minutes=28.0)

        # Game 3: player scores 40 pts (should NOT appear in game 2's stats)
        gid3 = "0022400003"
        _create_game(session, gid3, datetime.date(2024, 1, 5), 1, 2)
        _create_box_score(session, gid3, pid1, 1, points=40, fgm=16, fga=25, ftm=8, fta=10, minutes=38.0)
        _create_box_score(session, gid3, pid2, 1, points=20, fgm=8, fga=16, ftm=4, fta=5, minutes=30.0)
        _create_box_score(session, gid3, player_map[2][0], 2, points=15, minutes=30.0)
        _create_box_score(session, gid3, player_map[2][1], 2, points=18, minutes=32.0)

        compute_advanced_stats(session, player_id=pid1)
        session.flush()

        # Game 2's advanced stats should reflect game 2's own box score
        adv_game2 = session.query(PlayerAdvancedStats).filter_by(
            player_id=pid1, game_id=gid2
        ).first()
        assert adv_game2 is not None

        # TS% for game 2: 30 / (2 * (20 + 0.44 * 8)) = 30 / (2 * 23.52) = 30 / 47.04
        expected_ts = 30.0 / (2.0 * (20 + 0.44 * 8))
        assert adv_game2.true_shooting_pct == pytest.approx(expected_ts, rel=1e-3)

        # Team totals for game 2 should be pid1 + pid2 (not including game 3 data)
        # Team FGA for game 2 = 20 + 10 = 30
        assert adv_game2.team_fga == 30


class TestMatchupStatsNoLeakage:
    def test_matchup_stats_no_leakage(self, session):
        """Matchup stats for game 5 (vs team 2) should use only prior games vs team 2.

        5 games: games 1,2,4 vs team 2, game 3 vs team 3.
        For game 5 (vs team 2): matchup history = games 1,2,4 (3 prior games).
        """
        # 3 teams
        team_ids, player_map = _setup_teams_and_players(session, 3, 1)
        pid = player_map[1][0]

        # Game 1: vs team 2, player scores 10
        _create_game(session, "0022400001", datetime.date(2024, 1, 1), 1, 2)
        _create_box_score(session, "0022400001", pid, 1, points=10, minutes=25.0)
        _create_box_score(session, "0022400001", player_map[2][0], 2, points=12, minutes=25.0)

        # Game 2: vs team 2, player scores 20
        _create_game(session, "0022400002", datetime.date(2024, 1, 3), 1, 2)
        _create_box_score(session, "0022400002", pid, 1, points=20, minutes=30.0)
        _create_box_score(session, "0022400002", player_map[2][0], 2, points=15, minutes=28.0)

        # Game 3: vs team 3, player scores 25 (different opponent)
        _create_game(session, "0022400003", datetime.date(2024, 1, 5), 1, 3)
        _create_box_score(session, "0022400003", pid, 1, points=25, minutes=32.0)
        _create_box_score(session, "0022400003", player_map[3][0], 3, points=18, minutes=30.0)

        # Game 4: vs team 2, player scores 30
        _create_game(session, "0022400004", datetime.date(2024, 1, 7), 1, 2)
        _create_box_score(session, "0022400004", pid, 1, points=30, minutes=28.0)
        _create_box_score(session, "0022400004", player_map[2][0], 2, points=20, minutes=30.0)

        # Game 5: vs team 2, player scores 40 (should NOT be in matchup avg)
        _create_game(session, "0022400005", datetime.date(2024, 1, 9), 1, 2)
        _create_box_score(session, "0022400005", pid, 1, points=40, minutes=35.0)
        _create_box_score(session, "0022400005", player_map[2][0], 2, points=22, minutes=32.0)

        compute_matchup_stats(session, player_id=pid)
        session.flush()

        # Game 5 matchup stats: prior games vs team 2 = games 1,2,4
        ms_game5 = session.query(MatchupStats).filter_by(
            player_id=pid, game_id="0022400005"
        ).first()
        assert ms_game5 is not None
        assert ms_game5.matchup_games_played == 3
        assert ms_game5.has_matchup_history is True

        # Matchup avg points for game 5 = mean(10, 20, 30) = 20.0
        assert ms_game5.matchup_avg_points == pytest.approx(20.0)

        # Verify game 5's own score (40) is NOT included in the avg
        assert ms_game5.matchup_avg_points < 25.0  # Would be 25 if game 5 was included


class TestTeamFeaturesNoLeakage:
    def test_team_features_no_leakage(self, session):
        """Team features for game 3 should use only games 1-2 for win_pct.

        4 games: team 1 wins games 1,3 and loses games 2,4.
        For game 3: win_pct should be 1/2 = 0.5 (1 win in 2 games before game 3).
        Rest days for game 3 = days between game 2 and game 3.
        """
        team_ids, player_map = _setup_teams_and_players(session, 2, 1)

        # Game 1: team 1 wins (100-95), Jan 1
        _create_game(session, "0022400001", datetime.date(2024, 1, 1), 1, 2,
                      home_score=100, away_score=95)
        _create_box_score(session, "0022400001", player_map[1][0], 1, points=20, minutes=30.0)
        _create_box_score(session, "0022400001", player_map[2][0], 2, points=18, minutes=30.0)

        # Game 2: team 1 loses (90-105), Jan 3
        _create_game(session, "0022400002", datetime.date(2024, 1, 3), 1, 2,
                      home_score=90, away_score=105)
        _create_box_score(session, "0022400002", player_map[1][0], 1, points=15, minutes=28.0)
        _create_box_score(session, "0022400002", player_map[2][0], 2, points=22, minutes=32.0)

        # Game 3: team 1 wins (110-100), Jan 7
        _create_game(session, "0022400003", datetime.date(2024, 1, 7), 1, 2,
                      home_score=110, away_score=100)
        _create_box_score(session, "0022400003", player_map[1][0], 1, points=25, minutes=35.0)
        _create_box_score(session, "0022400003", player_map[2][0], 2, points=20, minutes=30.0)

        # Game 4: team 1 loses (85-95), Jan 9
        _create_game(session, "0022400004", datetime.date(2024, 1, 9), 1, 2,
                      home_score=85, away_score=95)
        _create_box_score(session, "0022400004", player_map[1][0], 1, points=12, minutes=25.0)
        _create_box_score(session, "0022400004", player_map[2][0], 2, points=19, minutes=30.0)

        compute_team_features(session, team_id=1)
        session.flush()

        # Game 3: win_pct should be 1/2 = 0.5 (1 win, 1 loss before game 3)
        tf_game3 = session.query(TeamFeatures).filter_by(
            team_id=1, game_id="0022400003"
        ).first()
        assert tf_game3 is not None
        assert tf_game3.season_win_pct == pytest.approx(0.5)

        # Rest days for game 3 = Jan 7 - Jan 3 = 4 days
        assert tf_game3.rest_days == 4

        # Game 1: win_pct should be None (no prior games)
        tf_game1 = session.query(TeamFeatures).filter_by(
            team_id=1, game_id="0022400001"
        ).first()
        assert tf_game1 is not None
        assert tf_game1.season_win_pct is None

        # Game 4: win_pct should be 2/3 (2 wins in 3 games before game 4)
        tf_game4 = session.query(TeamFeatures).filter_by(
            team_id=1, game_id="0022400004"
        ).first()
        assert tf_game4 is not None
        assert tf_game4.season_win_pct == pytest.approx(2 / 3)


class TestFullPipelineNoLeakage:
    def test_full_pipeline_no_leakage(self, session):
        """End-to-end: create 10-game sequence, compute all features for game 5,
        verify ALL feature types use only prior data.

        2 teams (A=1, B=2), 2 players per team, 10 games alternating home/away.
        Games on dates Jan 1, 3, 5, 7, 9, 11, 13, 15, 17, 19.
        Each game has distinct score lines.
        """
        team_ids, player_map = _setup_teams_and_players(session, 2, 2)

        dates = [datetime.date(2024, 1, d) for d in range(1, 20, 2)]  # 1,3,...,19
        game_ids = [f"002240{i+1:04d}" for i in range(10)]

        # Point values per game for player_map[1][0] (star player on team 1)
        star_points = [10, 20, 30, 15, 25, 35, 40, 18, 28, 45]

        # Alternate home/away
        for i in range(10):
            home = 1 if i % 2 == 0 else 2
            away = 2 if i % 2 == 0 else 1
            # Team 1 wins odd-indexed games (0-based): games 1,3,5,7,9
            h_score = 110 if (i % 2 == 0) else 95
            a_score = 95 if (i % 2 == 0) else 110
            _create_game(session, game_ids[i], dates[i], home, away,
                          home_score=h_score, away_score=a_score)

            # Box scores for each player
            for tid in [1, 2]:
                for pid in player_map[tid]:
                    pts = star_points[i] if pid == player_map[1][0] else 12
                    _create_box_score(
                        session, game_ids[i], pid, tid,
                        points=pts, rebounds=5, assists=3,
                        minutes=30.0, fgm=pts // 2, fga=pts,
                        ftm=2, fta=3, steals=1, blocks=1,
                        turnovers=2, plus_minus=5.0,
                        offensive_rebounds=1, defensive_rebounds=4,
                    )

        # Compute features for game 5 (index 4)
        compute_all_features_for_games(session, [game_ids[4]])

        star_pid = player_map[1][0]

        # 1. Rolling stats for game 5: should use only games 1-4
        rs = session.query(PlayerRollingStats).filter_by(
            player_id=star_pid, game_id=game_ids[4]
        ).first()
        assert rs is not None

        # Points avg for game 5 = mean of games 1-4 = mean(10,20,30,15) = 18.75
        expected_rolling_avg = (10 + 20 + 30 + 15) / 4.0
        assert rs.points_avg_5 == pytest.approx(expected_rolling_avg)
        assert rs.games_available_5 == 4

        # 2. Advanced stats for game 5: should reflect game 5's own box score
        adv = session.query(PlayerAdvancedStats).filter_by(
            player_id=star_pid, game_id=game_ids[4]
        ).first()
        assert adv is not None
        # TS% for game 5: pts=25, fga=25, fta=3
        # TS% = 25 / (2 * (25 + 0.44*3)) = 25 / (2 * 26.32) = 25 / 52.64
        expected_ts = 25.0 / (2.0 * (25 + 0.44 * 3))
        assert adv.true_shooting_pct == pytest.approx(expected_ts, rel=1e-3)

        # 3. Matchup stats for game 5: all prior games are vs same opponent (team 2)
        ms = session.query(MatchupStats).filter_by(
            player_id=star_pid, game_id=game_ids[4]
        ).first()
        assert ms is not None
        # 4 prior games vs team 2, matchup min games = 3, so has_history
        assert ms.matchup_games_played == 4
        assert ms.has_matchup_history is True
        # Matchup avg points = mean(10, 20, 30, 15) = 18.75
        assert ms.matchup_avg_points == pytest.approx(18.75)

        # 4. Team features for game 5
        tf = session.query(TeamFeatures).filter_by(
            team_id=1, game_id=game_ids[4]
        ).first()
        assert tf is not None
        # Team 1 won games at index 0,2 (home wins) and lost at index 1,3 (away losses)
        # where h_score=110 for even index (team 1 is home) and h_score=95 for odd (team 2 is home)
        # Game 0 (home=1): 110-95 -> team 1 wins
        # Game 1 (home=2): 95-110 -> team 1 is away, away_score=110 -> team 1 wins
        # Wait -- re-check the scoring logic:
        # i=0: home=1, h_score=110, a_score=95 -> team 1 wins (home)
        # i=1: home=2, h_score=95, a_score=110 -> team 1 is away, away_score=110 > home_score=95 -> team 1 wins
        # i=2: home=1, h_score=110, a_score=95 -> team 1 wins
        # i=3: home=2, h_score=95, a_score=110 -> team 1 is away, wins again
        # All games team 1 wins! win_pct before game 5 = 4/4 = 1.0
        assert tf.season_win_pct == pytest.approx(1.0)

        # Rest days for game 5: Jan 9 - Jan 7 = 2 days
        assert tf.rest_days == 2

    def test_validate_no_leakage_utility(self, session):
        """Run validate_no_leakage() after computing features, expect no violations."""
        team_ids, player_map = _setup_teams_and_players(session, 2, 1)
        star_pid = player_map[1][0]

        # Create 5 games with distinct scores
        for i in range(5):
            gid = f"002240000{i+1}"
            _create_game(session, gid, datetime.date(2024, 1, 2 * i + 1), 1, 2)
            _create_box_score(session, gid, star_pid, 1,
                              points=(i + 1) * 10, minutes=30.0)
            _create_box_score(session, gid, player_map[2][0], 2,
                              points=15, minutes=28.0)

        # Compute all features
        game_ids = [f"002240000{i+1}" for i in range(5)]
        compute_all_features_for_games(session, game_ids)

        # Validate should find zero violations
        violations = validate_no_leakage(session)
        assert violations == [], f"Temporal leakage detected: {violations}"
