"""Tests for FEAT-04: Team features (pace, ratings, rest days)."""

import datetime

import pytest

from hermes.data.features.team import (
    compute_team_features,
    compute_team_features_for_games,
    estimate_possessions,
    compute_offensive_rating,
    compute_pace,
    compute_rest_days,
)
from hermes.data.models import TeamFeatures


class TestPaceComputed:
    def test_pace_computed(self, session, make_team, make_player, make_game, make_box_score):
        """Pace = ((TeamPoss + OppPoss) / 2) * (240 / TeamMinutes)."""
        make_team(session, team_id=1, full_name="Home Team")
        make_team(session, team_id=2, full_name="Away Team")

        # Need players on both teams for box scores
        make_player(session, player_id=101, team_id=1, full_name="Player A")
        make_player(session, player_id=201, team_id=2, full_name="Player B")

        make_game(session, game_id="0022400001", game_date=datetime.date(2024, 1, 1),
                  home_team_id=1, away_team_id=2, home_score=110, away_score=105)

        # Team 1 box score: fga=80, fta=20, orb=10, tov=15, minutes=240
        make_box_score(session, game_id="0022400001", player_id=101, team_id=1,
                       points=110, fga=80, fta=20, offensive_rebounds=10, turnovers=15,
                       minutes=240.0, fgm=40, rebounds=40, assists=20)

        # Team 2 (opponent) box score: fga=85, fta=18, orb=12, tov=13, minutes=240
        make_box_score(session, game_id="0022400001", player_id=201, team_id=2,
                       points=105, fga=85, fta=18, offensive_rebounds=12, turnovers=13,
                       minutes=240.0, fgm=38, rebounds=38, assists=18)

        compute_team_features(session, team_id=1)

        tf = session.query(TeamFeatures).filter_by(
            team_id=1, game_id="0022400001"
        ).one()

        # Team possessions: 80 + 0.44*20 - 10 + 15 = 93.8
        # Opp possessions: 85 + 0.44*18 - 12 + 13 = 93.92
        team_poss = 80 + 0.44 * 20 - 10 + 15
        opp_poss = 85 + 0.44 * 18 - 12 + 13
        expected_pace = ((team_poss + opp_poss) / 2) * (240 / 240.0)

        assert tf.pace == pytest.approx(expected_pace, abs=0.1)
        assert tf.possessions == pytest.approx(team_poss, abs=0.1)
        assert tf.opponent_possessions == pytest.approx(opp_poss, abs=0.1)


class TestOffensiveRating:
    def test_offensive_rating(self, session, make_team, make_player, make_game, make_box_score):
        """ORtg = (Points / Possessions) * 100. Team scores 110 on ~93.8 possessions."""
        make_team(session, team_id=1, full_name="Home Team")
        make_team(session, team_id=2, full_name="Away Team")
        make_player(session, player_id=101, team_id=1, full_name="Player A")
        make_player(session, player_id=201, team_id=2, full_name="Player B")

        make_game(session, game_id="0022400001", game_date=datetime.date(2024, 1, 1),
                  home_team_id=1, away_team_id=2, home_score=110, away_score=105)

        make_box_score(session, game_id="0022400001", player_id=101, team_id=1,
                       points=110, fga=80, fta=20, offensive_rebounds=10, turnovers=15,
                       minutes=240.0, fgm=40, rebounds=40, assists=20)
        make_box_score(session, game_id="0022400001", player_id=201, team_id=2,
                       points=105, fga=85, fta=18, offensive_rebounds=12, turnovers=13,
                       minutes=240.0, fgm=38, rebounds=38, assists=18)

        compute_team_features(session, team_id=1)

        tf = session.query(TeamFeatures).filter_by(
            team_id=1, game_id="0022400001"
        ).one()

        # ORtg = (110 / 93.8) * 100 = ~117.27
        team_poss = 80 + 0.44 * 20 - 10 + 15
        expected_ortg = (110 / team_poss) * 100

        assert tf.offensive_rating == pytest.approx(expected_ortg, abs=0.1)


class TestDefensiveRating:
    def test_defensive_rating(self, session, make_team, make_player, make_game, make_box_score):
        """DRtg = (OppPoints / Possessions) * 100."""
        make_team(session, team_id=1, full_name="Home Team")
        make_team(session, team_id=2, full_name="Away Team")
        make_player(session, player_id=101, team_id=1, full_name="Player A")
        make_player(session, player_id=201, team_id=2, full_name="Player B")

        make_game(session, game_id="0022400001", game_date=datetime.date(2024, 1, 1),
                  home_team_id=1, away_team_id=2, home_score=110, away_score=105)

        make_box_score(session, game_id="0022400001", player_id=101, team_id=1,
                       points=110, fga=80, fta=20, offensive_rebounds=10, turnovers=15,
                       minutes=240.0, fgm=40, rebounds=40, assists=20)
        make_box_score(session, game_id="0022400001", player_id=201, team_id=2,
                       points=105, fga=85, fta=18, offensive_rebounds=12, turnovers=13,
                       minutes=240.0, fgm=38, rebounds=38, assists=18)

        compute_team_features(session, team_id=1)

        tf = session.query(TeamFeatures).filter_by(
            team_id=1, game_id="0022400001"
        ).one()

        # DRtg = (OppPoints / TeamPoss) * 100 = (105 / 93.8) * 100
        team_poss = 80 + 0.44 * 20 - 10 + 15
        expected_drtg = (105 / team_poss) * 100

        assert tf.defensive_rating == pytest.approx(expected_drtg, abs=0.1)


class TestRestDays:
    def test_rest_days(self, session, make_team, make_player, make_game, make_box_score):
        """Days between games calculated, season opener defaults to 3."""
        make_team(session, team_id=1, full_name="Home Team")
        make_team(session, team_id=2, full_name="Away Team")
        make_player(session, player_id=101, team_id=1, full_name="Player A")
        make_player(session, player_id=201, team_id=2, full_name="Player B")

        # Jan 1, Jan 3, Jan 6
        dates = [datetime.date(2024, 1, 1), datetime.date(2024, 1, 3), datetime.date(2024, 1, 6)]
        for i, d in enumerate(dates):
            gid = f"002240000{i + 1}"
            make_game(session, game_id=gid, game_date=d,
                      home_team_id=1, away_team_id=2, home_score=100, away_score=95)
            make_box_score(session, game_id=gid, player_id=101, team_id=1,
                           points=20, fga=15, fta=5, offensive_rebounds=2, turnovers=3, minutes=48.0,
                           fgm=8, rebounds=8, assists=5)
            make_box_score(session, game_id=gid, player_id=201, team_id=2,
                           points=19, fga=16, fta=4, offensive_rebounds=3, turnovers=4, minutes=48.0,
                           fgm=7, rebounds=7, assists=4)

        compute_team_features(session, team_id=1)

        tf1 = session.query(TeamFeatures).filter_by(team_id=1, game_id="0022400001").one()
        tf2 = session.query(TeamFeatures).filter_by(team_id=1, game_id="0022400002").one()
        tf3 = session.query(TeamFeatures).filter_by(team_id=1, game_id="0022400003").one()

        assert tf1.rest_days == 3   # Season opener default
        assert tf2.rest_days == 2   # Jan 3 - Jan 1 = 2
        assert tf3.rest_days == 3   # Jan 6 - Jan 3 = 3

    def test_pure_rest_days_function(self):
        """Pure function: compute_rest_days works standalone."""
        assert compute_rest_days(datetime.date(2024, 1, 5), datetime.date(2024, 1, 3)) == 2
        assert compute_rest_days(datetime.date(2024, 1, 10), None) == 3  # No prior -> default


class TestSeasonWinPct:
    def test_season_win_pct(self, session, make_team, make_player, make_game, make_box_score):
        """After 10 games with 7 wins, season_win_pct for next game = 0.7."""
        make_team(session, team_id=1, full_name="Home Team")
        make_team(session, team_id=2, full_name="Away Team")
        make_player(session, player_id=101, team_id=1, full_name="Player A")
        make_player(session, player_id=201, team_id=2, full_name="Player B")

        # 10 games: team 1 wins 7, loses 3
        for i in range(10):
            gid = f"00224000{i + 1:02d}"
            gdate = datetime.date(2024, 1, 1 + i)
            if i < 7:
                # Win: home score > away score
                home_score, away_score = 110, 95
            else:
                # Loss: home score < away score
                home_score, away_score = 90, 105
            make_game(session, game_id=gid, game_date=gdate,
                      home_team_id=1, away_team_id=2,
                      home_score=home_score, away_score=away_score)
            make_box_score(session, game_id=gid, player_id=101, team_id=1,
                           points=20, fga=15, fta=5, offensive_rebounds=2, turnovers=3,
                           minutes=48.0, fgm=8, rebounds=8, assists=5)
            make_box_score(session, game_id=gid, player_id=201, team_id=2,
                           points=19, fga=16, fta=4, offensive_rebounds=3, turnovers=4,
                           minutes=48.0, fgm=7, rebounds=7, assists=4)

        # Game 11 - check that win pct reflects prior 10 games
        make_game(session, game_id="0022400011", game_date=datetime.date(2024, 1, 11),
                  home_team_id=1, away_team_id=2, home_score=100, away_score=95)
        make_box_score(session, game_id="0022400011", player_id=101, team_id=1,
                       points=20, fga=15, fta=5, offensive_rebounds=2, turnovers=3,
                       minutes=48.0, fgm=8, rebounds=8, assists=5)
        make_box_score(session, game_id="0022400011", player_id=201, team_id=2,
                       points=19, fga=16, fta=4, offensive_rebounds=3, turnovers=4,
                       minutes=48.0, fgm=7, rebounds=7, assists=4)

        compute_team_features(session, team_id=1)

        tf = session.query(TeamFeatures).filter_by(
            team_id=1, game_id="0022400011"
        ).one()

        assert tf.season_win_pct == pytest.approx(0.7, abs=0.01)


class TestPureFunctions:
    """Test pure formula functions without DB dependency."""

    def test_estimate_possessions_full(self):
        """FGA + 0.44*FTA - ORB + TOV."""
        result = estimate_possessions(fga=80, fta=20, orb=10, tov=15)
        assert result == pytest.approx(93.8, abs=0.01)

    def test_estimate_possessions_no_orb(self):
        """Simplified formula when ORB is None."""
        result = estimate_possessions(fga=80, fta=20, orb=None, tov=15)
        assert result == pytest.approx(103.8, abs=0.01)  # 80 + 8.8 + 15

    def test_compute_offensive_rating(self):
        assert compute_offensive_rating(110, 100) == pytest.approx(110.0)
        assert compute_offensive_rating(110, 0) == 0.0

    def test_compute_pace(self):
        result = compute_pace(100, 98, 240)
        expected = ((100 + 98) / 2) * (240 / 240)
        assert result == pytest.approx(expected, abs=0.01)
        assert compute_pace(100, 98, 0) == 0.0

    def test_compute_rest_days(self):
        assert compute_rest_days(datetime.date(2024, 1, 5), datetime.date(2024, 1, 3)) == 2
        assert compute_rest_days(datetime.date(2024, 1, 1), None) == 3
