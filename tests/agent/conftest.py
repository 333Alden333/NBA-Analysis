"""Agent test fixtures -- seeded DB with players, teams, games, predictions."""

import datetime

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from sportsprediction.data.models.base import Base
from sportsprediction.data.models import (
    Player, Team, Game, BoxScore, Prediction, PredictionOutcome,
)


@pytest.fixture
def engine():
    """In-memory SQLite engine with FK enforcement."""
    eng = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(eng, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def session(engine):
    """Session with seeded data for agent tool testing."""
    Session = sessionmaker(bind=engine)
    sess = Session()

    # Teams
    lakers = Team(
        team_id=1, full_name="Los Angeles Lakers", abbreviation="LAL",
        conference="West", division="Pacific",
    )
    celtics = Team(
        team_id=2, full_name="Boston Celtics", abbreviation="BOS",
        conference="East", division="Atlantic",
    )
    sess.add_all([lakers, celtics])
    sess.flush()

    # Players
    lebron = Player(
        player_id=101, full_name="LeBron James", first_name="LeBron",
        last_name="James", team_id=1, position="F", is_active=True,
    )
    tatum = Player(
        player_id=102, full_name="Jayson Tatum", first_name="Jayson",
        last_name="Tatum", team_id=2, position="F", is_active=True,
    )
    sess.add_all([lebron, tatum])
    sess.flush()

    # Games
    dates = [
        datetime.date(2025, 1, 10),
        datetime.date(2025, 1, 12),
        datetime.date(2025, 1, 14),
    ]
    games = []
    for i, d in enumerate(dates):
        g = Game(
            game_id=f"002250{i+1:04d}", game_date=d,
            home_team_id=1, away_team_id=2,
            home_score=105 + i * 3, away_score=100 + i * 2,
            season="2024-25", status="Final",
        )
        games.append(g)
    sess.add_all(games)
    sess.flush()

    # Box scores
    for i, g in enumerate(games):
        # LeBron
        sess.add(BoxScore(
            game_id=g.game_id, player_id=101, team_id=1,
            points=25 + i * 3, rebounds=8, assists=7, fg3m=2,
            minutes=35.0, fgm=10, fga=20, ftm=3, fta=4,
            steals=1, blocks=1, turnovers=3, plus_minus=5.0,
            offensive_rebounds=1, defensive_rebounds=7, personal_fouls=2,
        ))
        # Tatum
        sess.add(BoxScore(
            game_id=g.game_id, player_id=102, team_id=2,
            points=22 + i * 2, rebounds=6, assists=4, fg3m=3,
            minutes=34.0, fgm=9, fga=19, ftm=2, fta=3,
            steals=2, blocks=0, turnovers=2, plus_minus=-3.0,
            offensive_rebounds=0, defensive_rebounds=6, personal_fouls=3,
        ))
    sess.flush()

    # Predictions with outcomes
    pred1 = Prediction(
        game_id=games[0].game_id, prediction_type="game_winner",
        predicted_value=1.0, win_probability=0.65, model_version="v1",
    )
    sess.add(pred1)
    sess.flush()

    outcome1 = PredictionOutcome(
        prediction_id=pred1.id, actual_value=1.0, is_correct=1,
        resolved_at=datetime.datetime(2025, 1, 10, 23, 0),
    )
    sess.add(outcome1)

    # Player prediction for LeBron points
    pred2 = Prediction(
        game_id=games[1].game_id, prediction_type="player_points",
        player_id=101, predicted_value=27.0, model_version="v1",
        confidence_lower=20.0, confidence_upper=34.0,
    )
    sess.add(pred2)
    sess.flush()

    outcome2 = PredictionOutcome(
        prediction_id=pred2.id, actual_value=28.0, is_correct=1,
        resolved_at=datetime.datetime(2025, 1, 12, 23, 0),
    )
    sess.add(outcome2)
    sess.flush()

    # Matchup stats (create table manually since MatchupStats may need it)
    try:
        from sportsprediction.data.models.matchup_stats import MatchupStats
        ms = MatchupStats(
            player_id=101, game_id=games[0].game_id,
            game_date=dates[0], opponent_team_id=2,
            matchup_games_played=5, has_matchup_history=True,
            matchup_avg_points=28.5, matchup_avg_rebounds=9.0,
            matchup_avg_assists=7.5, matchup_avg_fg_pct=0.52,
            matchup_avg_plus_minus=4.5,
            matchup_diff_points=2.5, matchup_diff_rebounds=1.0,
            matchup_diff_assists=0.5, matchup_diff_fg_pct=0.02,
            matchup_diff_plus_minus=1.5,
        )
        sess.add(ms)
        sess.flush()
    except Exception:
        pass  # matchup_stats table may not exist in minimal schema

    sess.commit()
    yield sess
    sess.close()
