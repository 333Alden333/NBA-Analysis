"""Team feature computation -- pace, efficiency ratings, rest days.

FEAT-04: Computes team-level features per game for pace context,
offensive/defensive ratings, and rest/scheduling effects.
"""

import datetime
from typing import Optional

from sqlalchemy import func, or_, and_
from sqlalchemy.orm import Session

from sportsprediction.data.models import BoxScore, Game, TeamFeatures


def estimate_possessions(
    fga: int,
    fta: int,
    orb: Optional[int],
    tov: int,
) -> float:
    """Estimate possessions using Basketball-Reference formula.

    Full: FGA + 0.44*FTA - ORB + TOV
    Simplified (no ORB): FGA + 0.44*FTA + TOV
    """
    base = fga + 0.44 * fta + tov
    if orb is not None:
        base -= orb
    return base


def compute_offensive_rating(points: int, possessions: float) -> float:
    """Compute offensive rating per 100 possessions.

    ORtg = (Points / Possessions) * 100
    """
    if possessions == 0:
        return 0.0
    return (points / possessions) * 100


def compute_pace(
    team_poss: float,
    opp_poss: float,
    team_minutes: float,
) -> float:
    """Compute pace (possessions per 48 minutes).

    Pace = ((TeamPoss + OppPoss) / 2) * (240 / TeamMinutes)
    """
    if team_minutes == 0:
        return 0.0
    return ((team_poss + opp_poss) / 2) * (240 / team_minutes)


def compute_rest_days(
    current_game_date: datetime.date,
    previous_game_date: Optional[datetime.date],
) -> int:
    """Compute rest days between games.

    Returns 3 if no previous game (season opener).
    """
    if previous_game_date is None:
        return 3
    return (current_game_date - previous_game_date).days


def _aggregate_team_box_scores(session: Session, game_id: str, team_id: int) -> dict:
    """Aggregate box score stats for a team in a game.

    Returns dict with fga, fta, orb, tov, points, minutes.
    """
    result = session.query(
        func.sum(BoxScore.fga).label("fga"),
        func.sum(BoxScore.fta).label("fta"),
        func.sum(BoxScore.offensive_rebounds).label("orb"),
        func.sum(BoxScore.turnovers).label("tov"),
        func.sum(BoxScore.points).label("points"),
        func.sum(BoxScore.minutes).label("minutes"),
    ).filter(
        BoxScore.game_id == game_id,
        BoxScore.team_id == team_id,
    ).one()

    return {
        "fga": result.fga or 0,
        "fta": result.fta or 0,
        "orb": result.orb,  # Keep None for simplified formula fallback
        "tov": result.tov or 0,
        "points": result.points or 0,
        "minutes": result.minutes or 0.0,
    }


def _get_opponent_team_id(game: Game, team_id: int) -> int:
    """Get the opponent team ID from a game."""
    if team_id == game.home_team_id:
        return game.away_team_id
    return game.home_team_id


def _did_team_win(game: Game, team_id: int) -> bool:
    """Check if team won the game."""
    if game.home_score is None or game.away_score is None:
        return False
    if team_id == game.home_team_id:
        return game.home_score > game.away_score
    else:
        return game.away_score > game.home_score


def compute_team_features(
    session: Session,
    team_id: int,
    as_of_date: Optional[datetime.date] = None,
) -> list[TeamFeatures]:
    """Compute team features for all games a team has played.

    For each game, computes pace, ORtg, DRtg, rest days, and season win pct
    using only data available at the time (temporal discipline).

    Args:
        session: SQLAlchemy session.
        team_id: Team to compute features for.
        as_of_date: If set, only compute for games on or before this date.

    Returns:
        List of TeamFeatures records upserted.
    """
    # Get all games for this team, ordered by date
    team_games = (
        session.query(Game)
        .filter(or_(Game.home_team_id == team_id, Game.away_team_id == team_id))
        .order_by(Game.game_date.asc())
        .all()
    )

    if not team_games:
        return []

    results = []
    previous_game_date = None
    wins_before = 0
    games_before = 0

    for game in team_games:
        if as_of_date and game.game_date > as_of_date:
            continue

        opponent_id = _get_opponent_team_id(game, team_id)

        # Aggregate box scores for team and opponent
        team_agg = _aggregate_team_box_scores(session, game.game_id, team_id)
        opp_agg = _aggregate_team_box_scores(session, game.game_id, opponent_id)

        # Estimate possessions
        team_poss = estimate_possessions(
            team_agg["fga"], team_agg["fta"], team_agg["orb"], team_agg["tov"]
        )
        opp_poss = estimate_possessions(
            opp_agg["fga"], opp_agg["fta"], opp_agg["orb"], opp_agg["tov"]
        )

        # Compute features
        pace_val = compute_pace(team_poss, opp_poss, team_agg["minutes"])

        ortg = compute_offensive_rating(team_agg["points"], team_poss)

        # DRtg: opponent points / team possessions * 100
        drtg = compute_offensive_rating(opp_agg["points"], team_poss)

        rest = compute_rest_days(game.game_date, previous_game_date)

        # Season win pct: wins before this game / games before this game
        season_win_pct = (wins_before / games_before) if games_before > 0 else None

        record = {
            "team_id": team_id,
            "game_id": game.game_id,
            "game_date": game.game_date,
            "pace": pace_val,
            "offensive_rating": ortg,
            "defensive_rating": drtg,
            "rest_days": rest,
            "possessions": team_poss,
            "opponent_possessions": opp_poss,
            "season_win_pct": season_win_pct,
        }

        # Upsert
        existing = session.query(TeamFeatures).filter_by(
            team_id=team_id, game_id=game.game_id
        ).first()

        if existing:
            for key, value in record.items():
                setattr(existing, key, value)
            results.append(existing)
        else:
            tf = TeamFeatures(**record)
            session.add(tf)
            results.append(tf)

        # Update rolling counters for next iteration
        previous_game_date = game.game_date
        games_before += 1
        if _did_team_win(game, team_id):
            wins_before += 1

    session.flush()
    return results


def compute_team_features_for_games(
    session: Session,
    game_ids: list[str],
) -> list[TeamFeatures]:
    """Compute team features for all teams in the given games.

    Args:
        session: SQLAlchemy session.
        game_ids: List of game IDs to process.

    Returns:
        List of all TeamFeatures records created/updated.
    """
    # Find all team_ids in those games
    games = session.query(Game).filter(Game.game_id.in_(game_ids)).all()
    team_ids = set()
    for g in games:
        if g.home_team_id:
            team_ids.add(g.home_team_id)
        if g.away_team_id:
            team_ids.add(g.away_team_id)

    all_results = []
    for tid in team_ids:
        all_results.extend(compute_team_features(session, team_id=tid))

    return all_results
