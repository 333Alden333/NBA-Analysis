"""Streamlit-free data access layer for agent tools.

All functions take a SQLAlchemy Session and return plain dicts/lists.
No Streamlit imports. No caching decorators.
"""

import difflib
import logging
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def get_all_players(session: Session) -> list[dict]:
    """Get all active players with team info."""
    query = text("""
        SELECT p.player_id, p.full_name, p.position,
               t.abbreviation AS team_abbr, t.full_name AS team_name
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.team_id
        WHERE p.is_active = 1
        ORDER BY p.full_name
    """)
    rows = session.execute(query).mappings().all()
    return [dict(r) for r in rows]


def search_players(session: Session, query_str: str) -> list[dict]:
    """Fuzzy search players by name. Returns top 5 matches.

    Matches on:
    - difflib close matches against full_name
    - Substring match on first_name or last_name
    """
    all_players = get_all_players(session)
    if not all_players:
        return []

    names = [p["full_name"] for p in all_players]
    name_to_player = {p["full_name"]: p for p in all_players}

    # difflib fuzzy matching
    close = difflib.get_close_matches(query_str, names, n=5, cutoff=0.4)

    # Also check substring matches (case-insensitive)
    q_lower = query_str.lower()
    substring_matches = []
    for p in all_players:
        fn = p["full_name"].lower()
        if q_lower in fn and p["full_name"] not in close:
            substring_matches.append(p["full_name"])

    # Combine: close matches first, then substring matches, capped at 5
    combined = close + substring_matches
    results = []
    seen = set()
    for name in combined:
        if name not in seen and len(results) < 5:
            seen.add(name)
            results.append(name_to_player[name])

    return results


def get_player_info(session: Session, player_id: int) -> Optional[dict]:
    """Get detailed player info with team name."""
    query = text("""
        SELECT p.*, t.full_name AS team_name, t.abbreviation AS team_abbr
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.team_id
        WHERE p.player_id = :player_id
    """)
    row = session.execute(query, {"player_id": player_id}).mappings().first()
    return dict(row) if row else None


def get_player_recent_games(
    session: Session, player_id: int, limit: int = 10
) -> list[dict]:
    """Get recent box scores for a player."""
    query = text("""
        SELECT
            bs.points, bs.rebounds, bs.assists, bs.fg3m, bs.minutes,
            bs.fgm, bs.fga, bs.ftm, bs.fta, bs.steals, bs.blocks,
            bs.turnovers, bs.plus_minus,
            g.game_date,
            g.home_team_id, g.away_team_id,
            g.home_score, g.away_score,
            ht.abbreviation AS home_abbr,
            at.abbreviation AS away_abbr
        FROM box_scores bs
        JOIN games g ON bs.game_id = g.game_id
        LEFT JOIN teams ht ON g.home_team_id = ht.team_id
        LEFT JOIN teams at ON g.away_team_id = at.team_id
        WHERE bs.player_id = :player_id
        ORDER BY g.game_date DESC
        LIMIT :limit
    """)
    rows = session.execute(
        query, {"player_id": player_id, "limit": limit}
    ).mappings().all()
    return [dict(r) for r in rows]


def get_player_predictions(
    session: Session, player_id: int, limit: int = 10
) -> list[dict]:
    """Get recent predictions for a player with outcomes."""
    query = text("""
        SELECT
            p.id AS prediction_id,
            p.prediction_type,
            p.predicted_value,
            p.confidence_lower,
            p.confidence_upper,
            p.model_version,
            p.created_at,
            g.game_date,
            ht.abbreviation AS home_abbr,
            at.abbreviation AS away_abbr,
            po.actual_value,
            po.is_correct,
            po.resolved_at
        FROM predictions p
        JOIN games g ON p.game_id = g.game_id
        LEFT JOIN teams ht ON g.home_team_id = ht.team_id
        LEFT JOIN teams at ON g.away_team_id = at.team_id
        LEFT JOIN prediction_outcomes po ON p.id = po.prediction_id
        WHERE p.player_id = :player_id
        ORDER BY g.game_date DESC, p.created_at DESC
        LIMIT :limit
    """)
    rows = session.execute(
        query, {"player_id": player_id, "limit": limit}
    ).mappings().all()
    return [dict(r) for r in rows]


def get_today_games(session: Session, today_str: str) -> list[dict]:
    """Get games for a given date with predictions."""
    query = text("""
        SELECT
            g.game_id,
            g.game_date,
            g.status,
            g.home_team_id,
            g.away_team_id,
            g.home_score,
            g.away_score,
            ht.full_name AS home_team,
            ht.abbreviation AS home_abbr,
            at.full_name AS away_team,
            at.abbreviation AS away_abbr
        FROM games g
        LEFT JOIN teams ht ON g.home_team_id = ht.team_id
        LEFT JOIN teams at ON g.away_team_id = at.team_id
        WHERE g.game_date = :game_date
        ORDER BY g.game_id
    """)
    rows = session.execute(query, {"game_date": today_str}).mappings().all()

    games = []
    for row in rows:
        game = dict(row)

        pred_query = text("""
            SELECT prediction_type, predicted_value, win_probability,
                   confidence_lower, confidence_upper
            FROM predictions
            WHERE game_id = :game_id
              AND player_id IS NULL
            ORDER BY created_at DESC
        """)
        preds = session.execute(
            pred_query, {"game_id": game["game_id"]}
        ).mappings().all()

        game["win_probability"] = None
        game["predicted_spread"] = None
        game["predicted_total"] = None

        seen_types = set()
        for pred in preds:
            ptype = pred["prediction_type"]
            if ptype in seen_types:
                continue
            seen_types.add(ptype)

            if ptype == "game_winner":
                game["win_probability"] = pred["win_probability"]
            elif ptype == "game_spread":
                game["predicted_spread"] = pred["predicted_value"]
            elif ptype == "game_total":
                game["predicted_total"] = pred["predicted_value"]

        games.append(game)

    return games


def get_team_standings(session: Session) -> list[dict]:
    """Get team standings with W-L records, grouped by conference."""
    query = text("""
        SELECT
            t.team_id,
            t.full_name,
            t.abbreviation,
            t.conference,
            t.division,
            SUM(CASE
                WHEN (g.home_team_id = t.team_id AND g.home_score > g.away_score)
                  OR (g.away_team_id = t.team_id AND g.away_score > g.home_score)
                THEN 1 ELSE 0
            END) AS wins,
            SUM(CASE
                WHEN (g.home_team_id = t.team_id AND g.home_score < g.away_score)
                  OR (g.away_team_id = t.team_id AND g.away_score < g.home_score)
                THEN 1 ELSE 0
            END) AS losses
        FROM teams t
        LEFT JOIN games g ON (g.home_team_id = t.team_id OR g.away_team_id = t.team_id)
            AND g.status = 'Final'
            AND g.season = (SELECT MAX(season) FROM games)
        GROUP BY t.team_id
        ORDER BY t.conference, wins DESC
    """)
    rows = session.execute(query).mappings().all()
    return [dict(r) for r in rows]


def get_team_info_with_record(
    session: Session, team_id: int
) -> Optional[dict]:
    """Get team info + W-L record."""
    query = text("""
        SELECT
            t.team_id,
            t.full_name,
            t.abbreviation,
            t.conference,
            t.division,
            SUM(CASE
                WHEN (g.home_team_id = t.team_id AND g.home_score > g.away_score)
                  OR (g.away_team_id = t.team_id AND g.away_score > g.home_score)
                THEN 1 ELSE 0
            END) AS wins,
            SUM(CASE
                WHEN (g.home_team_id = t.team_id AND g.home_score < g.away_score)
                  OR (g.away_team_id = t.team_id AND g.away_score < g.home_score)
                THEN 1 ELSE 0
            END) AS losses
        FROM teams t
        LEFT JOIN games g ON (g.home_team_id = t.team_id OR g.away_team_id = t.team_id)
            AND g.status = 'Final'
            AND g.season = (SELECT MAX(season) FROM games)
        WHERE t.team_id = :team_id
        GROUP BY t.team_id
    """)
    row = session.execute(query, {"team_id": team_id}).mappings().first()
    return dict(row) if row else None


def get_all_teams(session: Session) -> list[dict]:
    """Get all teams."""
    query = text("""
        SELECT team_id, full_name, abbreviation, conference, division
        FROM teams
        ORDER BY full_name
    """)
    rows = session.execute(query).mappings().all()
    return [dict(r) for r in rows]


def search_teams(session: Session, query_str: str) -> Optional[dict]:
    """Fuzzy search for a team by name or abbreviation. Returns best match."""
    all_teams = get_all_teams(session)
    if not all_teams:
        return None

    q_lower = query_str.lower()

    # Exact abbreviation match first
    for t in all_teams:
        if t.get("abbreviation") and t["abbreviation"].lower() == q_lower:
            return t

    # Substring match on full_name
    for t in all_teams:
        if q_lower in t["full_name"].lower():
            return t

    # Fuzzy match on full_name
    names = [t["full_name"] for t in all_teams]
    close = difflib.get_close_matches(query_str, names, n=1, cutoff=0.5)
    if close:
        name_to_team = {t["full_name"]: t for t in all_teams}
        return name_to_team[close[0]]

    return None


def get_prediction_accuracy(
    session: Session, prediction_type: Optional[str] = None
) -> dict:
    """Get prediction accuracy metrics. Wraps metrics.compute_metrics."""
    from hermes.models.metrics import compute_metrics
    return compute_metrics(session, prediction_type=prediction_type)


def get_prediction_history(
    session: Session,
    prediction_type: Optional[str] = None,
    limit: int = 20,
) -> list[dict]:
    """Get recent predictions with HIT/MISS/PENDING status."""
    conditions = []
    params = {"limit": limit}

    if prediction_type:
        conditions.append("p.prediction_type = :ptype")
        params["ptype"] = prediction_type

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    query = text(f"""
        SELECT
            p.id AS prediction_id,
            p.prediction_type,
            p.predicted_value,
            p.win_probability,
            p.confidence_lower,
            p.confidence_upper,
            p.model_version,
            g.game_date,
            g.status AS game_status,
            ht.abbreviation AS home_abbr,
            at.abbreviation AS away_abbr,
            po.actual_value,
            po.is_correct,
            po.resolved_at
        FROM predictions p
        JOIN games g ON p.game_id = g.game_id
        LEFT JOIN teams ht ON g.home_team_id = ht.team_id
        LEFT JOIN teams at ON g.away_team_id = at.team_id
        LEFT JOIN prediction_outcomes po ON p.id = po.prediction_id
        {where_clause}
        ORDER BY g.game_date DESC, p.created_at DESC
        LIMIT :limit
    """)
    rows = session.execute(query, params).mappings().all()

    results = []
    for row in rows:
        d = dict(row)
        # Compute status
        if d.get("is_correct") is not None:
            d["status"] = "HIT" if d["is_correct"] == 1 else "MISS"
        else:
            d["status"] = "PENDING"
        results.append(d)

    return results


def get_matchup_analysis(
    session: Session, player_id: int, opponent_team_id: int
) -> Optional[dict]:
    """Get player's historical matchup stats vs a specific team.

    Returns the most recent matchup_stats row for the player vs the team,
    which contains rolling matchup averages.
    """
    query = text("""
        SELECT
            ms.*,
            p.full_name AS player_name,
            t.full_name AS opponent_team
        FROM matchup_stats ms
        JOIN players p ON ms.player_id = p.player_id
        JOIN teams t ON ms.opponent_team_id = t.team_id
        WHERE ms.player_id = :player_id
          AND ms.opponent_team_id = :opponent_team_id
        ORDER BY ms.game_date DESC
        LIMIT 1
    """)
    row = session.execute(
        query, {"player_id": player_id, "opponent_team_id": opponent_team_id}
    ).mappings().first()
    return dict(row) if row else None
