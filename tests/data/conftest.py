"""Data-specific test fixtures."""

import datetime

import pytest

from hermes.data.models import Player, Team, Game, BoxScore


@pytest.fixture
def make_team():
    """Factory fixture to create a Team record."""

    def _make_team(session, team_id, full_name="Test Team", **kwargs):
        team = Team(team_id=team_id, full_name=full_name, **kwargs)
        session.add(team)
        session.flush()
        return team

    return _make_team


@pytest.fixture
def make_player():
    """Factory fixture to create a Player record."""

    def _make_player(session, player_id, team_id, full_name="Test Player", **kwargs):
        player = Player(player_id=player_id, team_id=team_id, full_name=full_name, **kwargs)
        session.add(player)
        session.flush()
        return player

    return _make_player


@pytest.fixture
def make_game():
    """Factory fixture to create a Game record."""

    def _make_game(
        session, game_id, game_date, home_team_id, away_team_id,
        home_score=100, away_score=95, season="2024-25", **kwargs,
    ):
        game = Game(
            game_id=game_id,
            game_date=game_date,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_score=home_score,
            away_score=away_score,
            season=season,
            **kwargs,
        )
        session.add(game)
        session.flush()
        return game

    return _make_game


@pytest.fixture
def make_box_score():
    """Factory fixture to create a BoxScore record with sensible defaults."""

    def _make_box_score(
        session, game_id, player_id, team_id,
        points=10, rebounds=5, assists=3, minutes=25.0,
        fgm=4, fga=10, fg3m=1, fg3a=3, ftm=1, fta=2,
        steals=1, blocks=1, turnovers=2, plus_minus=5.0,
        offensive_rebounds=1, defensive_rebounds=4, personal_fouls=2,
        **kwargs,
    ):
        bs = BoxScore(
            game_id=game_id,
            player_id=player_id,
            team_id=team_id,
            points=points,
            rebounds=rebounds,
            assists=assists,
            minutes=minutes,
            fgm=fgm,
            fga=fga,
            fg3m=fg3m,
            fg3a=fg3a,
            ftm=ftm,
            fta=fta,
            steals=steals,
            blocks=blocks,
            turnovers=turnovers,
            plus_minus=plus_minus,
            offensive_rebounds=offensive_rebounds,
            defensive_rebounds=defensive_rebounds,
            personal_fouls=personal_fouls,
            **kwargs,
        )
        session.add(bs)
        session.flush()
        return bs

    return _make_box_score


@pytest.fixture
def sample_team_and_players(session, make_team, make_player):
    """Create 2 teams and 3 players on team 1. Returns dict with IDs."""
    make_team(session, team_id=1, full_name="Home Team")
    make_team(session, team_id=2, full_name="Away Team")
    make_player(session, player_id=101, team_id=1, full_name="Player A")
    make_player(session, player_id=102, team_id=1, full_name="Player B")
    make_player(session, player_id=103, team_id=1, full_name="Player C")
    return {
        "team_ids": [1, 2],
        "player_ids": [101, 102, 103],
    }


@pytest.fixture
def three_game_sequence(session, sample_team_and_players, make_game, make_box_score):
    """Create 3 games on Jan 1/3/5 2024 with box scores for all 3 players."""
    dates = [
        datetime.date(2024, 1, 1),
        datetime.date(2024, 1, 3),
        datetime.date(2024, 1, 5),
    ]
    game_ids = ["0022400001", "0022400002", "0022400003"]
    player_ids = sample_team_and_players["player_ids"]

    # Create 3 games
    for i, (gid, gdate) in enumerate(zip(game_ids, dates)):
        make_game(session, game_id=gid, game_date=gdate, home_team_id=1, away_team_id=2)

    # Create box scores with distinct stat lines per player per game
    stat_lines = [
        # Game 1: player A=20pts, B=15pts, C=8pts
        {"101": {"points": 20, "rebounds": 8, "assists": 5, "minutes": 32.0, "fgm": 8, "fga": 16},
         "102": {"points": 15, "rebounds": 6, "assists": 4, "minutes": 28.0, "fgm": 6, "fga": 14},
         "103": {"points": 8, "rebounds": 3, "assists": 2, "minutes": 18.0, "fgm": 3, "fga": 8}},
        # Game 2: player A=25pts, B=12pts, C=10pts
        {"101": {"points": 25, "rebounds": 10, "assists": 7, "minutes": 35.0, "fgm": 10, "fga": 20},
         "102": {"points": 12, "rebounds": 5, "assists": 3, "minutes": 24.0, "fgm": 5, "fga": 12},
         "103": {"points": 10, "rebounds": 4, "assists": 3, "minutes": 20.0, "fgm": 4, "fga": 10}},
        # Game 3: player A=18pts, B=22pts, C=14pts
        {"101": {"points": 18, "rebounds": 6, "assists": 4, "minutes": 30.0, "fgm": 7, "fga": 15},
         "102": {"points": 22, "rebounds": 9, "assists": 6, "minutes": 34.0, "fgm": 9, "fga": 18},
         "103": {"points": 14, "rebounds": 6, "assists": 4, "minutes": 25.0, "fgm": 6, "fga": 13}},
    ]

    for i, gid in enumerate(game_ids):
        for pid in player_ids:
            stats = stat_lines[i][str(pid)]
            make_box_score(session, game_id=gid, player_id=pid, team_id=1, **stats)

    return {
        "game_ids": game_ids,
        "dates": dates,
        "player_ids": player_ids,
    }
