"""Cached data access layer for all dashboard pages.

All functions return plain dicts/DataFrames, never SQLAlchemy model instances.
Uses st.cache_resource for engine and st.cache_data for query results.
"""

import logging

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from sportsprediction.config import settings

logger = logging.getLogger(__name__)


@st.cache_resource
def _get_engine():
    """Create and cache the SQLAlchemy engine."""
    engine = create_engine(f"sqlite:///{settings.db_path}")
    return engine


def _get_session():
    """Create a new session from the cached engine."""
    engine = _get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


@st.cache_data(ttl=300)
def get_todays_games(today_str: str) -> list:
    """Get games for a given date with team info and predictions.

    Returns list of dicts with game info, team names, and prediction data.
    """
    session = _get_session()
    try:
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

            # Get predictions for this game
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
            game["confidence_lower_spread"] = None
            game["confidence_upper_spread"] = None
            game["confidence_lower_total"] = None
            game["confidence_upper_total"] = None

            seen_types = set()
            for pred in preds:
                ptype = pred["prediction_type"]
                if ptype in seen_types:
                    continue  # Take most recent only
                seen_types.add(ptype)

                if ptype == "game_winner":
                    game["win_probability"] = pred["win_probability"]
                elif ptype == "game_spread":
                    game["predicted_spread"] = pred["predicted_value"]
                    game["confidence_lower_spread"] = pred["confidence_lower"]
                    game["confidence_upper_spread"] = pred["confidence_upper"]
                elif ptype == "game_total":
                    game["predicted_total"] = pred["predicted_value"]
                    game["confidence_lower_total"] = pred["confidence_lower"]
                    game["confidence_upper_total"] = pred["confidence_upper"]

            games.append(game)

        return games
    finally:
        session.close()


@st.cache_data(ttl=3600)
def get_player_rolling_stats(player_id: int) -> pd.DataFrame:
    """Get rolling stats for a player, ordered by game_date."""
    session = _get_session()
    try:
        query = text("""
            SELECT * FROM player_rolling_stats
            WHERE player_id = :player_id
            ORDER BY game_date
        """)
        result = session.execute(query, {"player_id": player_id})
        df = pd.DataFrame(result.mappings().all())
        return df
    finally:
        session.close()


@st.cache_data(ttl=3600)
def get_player_recent_games(player_id: int, limit: int = 10) -> list:
    """Get recent box scores for a player."""
    session = _get_session()
    try:
        query = text("""
            SELECT
                bs.*,
                g.game_date,
                g.status,
                g.home_team_id,
                g.away_team_id,
                g.home_score,
                g.away_score,
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
    finally:
        session.close()


@st.cache_data(ttl=3600)
def get_player_info(player_id: int):
    """Get player info dict, or None if not found."""
    session = _get_session()
    try:
        query = text("""
            SELECT p.*, t.full_name AS team_name, t.abbreviation AS team_abbr
            FROM players p
            LEFT JOIN teams t ON p.team_id = t.team_id
            WHERE p.player_id = :player_id
        """)
        row = session.execute(
            query, {"player_id": player_id}
        ).mappings().first()
        return dict(row) if row else None
    finally:
        session.close()


@st.cache_data(ttl=3600)
def get_all_players() -> list:
    """Get all active players for search/selection."""
    session = _get_session()
    try:
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
    finally:
        session.close()


@st.cache_data(ttl=3600)
def get_team_standings() -> list:
    """Get team standings with W-L records, grouped by conference."""
    session = _get_session()
    try:
        # Count wins and losses from games where status is Final
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
    finally:
        session.close()


@st.cache_data(ttl=3600)
def get_team_info(team_id: int):
    """Get team info dict, or None if not found."""
    session = _get_session()
    try:
        query = text("""
            SELECT * FROM teams WHERE team_id = :team_id
        """)
        row = session.execute(query, {"team_id": team_id}).mappings().first()
        return dict(row) if row else None
    finally:
        session.close()


@st.cache_data(ttl=3600)
def get_team_features(team_id: int) -> pd.DataFrame:
    """Get team features (pace, ratings, etc.) ordered by game_date."""
    session = _get_session()
    try:
        query = text("""
            SELECT * FROM team_features
            WHERE team_id = :team_id
            ORDER BY game_date
        """)
        result = session.execute(query, {"team_id": team_id})
        df = pd.DataFrame(result.mappings().all())
        return df
    finally:
        session.close()


@st.cache_data(ttl=3600)
def get_team_games(team_id: int, limit: int = 20) -> list:
    """Get recent games for a team."""
    session = _get_session()
    try:
        query = text("""
            SELECT
                g.*,
                ht.full_name AS home_team,
                ht.abbreviation AS home_abbr,
                at.full_name AS away_team,
                at.abbreviation AS away_abbr
            FROM games g
            LEFT JOIN teams ht ON g.home_team_id = ht.team_id
            LEFT JOIN teams at ON g.away_team_id = at.team_id
            WHERE (g.home_team_id = :team_id OR g.away_team_id = :team_id)
            ORDER BY g.game_date DESC
            LIMIT :limit
        """)
        rows = session.execute(
            query, {"team_id": team_id, "limit": limit}
        ).mappings().all()
        return [dict(r) for r in rows]
    finally:
        session.close()


@st.cache_data(ttl=3600)
def get_all_teams() -> list:
    """Get all teams for selection."""
    session = _get_session()
    try:
        query = text("""
            SELECT team_id, full_name, abbreviation, conference, division
            FROM teams
            ORDER BY full_name
        """)
        rows = session.execute(query).mappings().all()
        return [dict(r) for r in rows]
    finally:
        session.close()


@st.cache_data(ttl=300)
def get_predictions_history(
    prediction_type: str = None,
    start_date: str = None,
    end_date: str = None,
) -> list:
    """Get prediction history with outcomes for the tracker page."""
    session = _get_session()
    try:
        conditions = []
        params = {}

        if prediction_type:
            conditions.append("p.prediction_type = :ptype")
            params["ptype"] = prediction_type

        if start_date:
            conditions.append("g.game_date >= :start_date")
            params["start_date"] = start_date

        if end_date:
            conditions.append("g.game_date <= :end_date")
            params["end_date"] = end_date

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        query = text(f"""
            SELECT
                p.id AS prediction_id,
                p.game_id,
                p.prediction_type,
                p.predicted_value,
                p.win_probability,
                p.confidence_lower,
                p.confidence_upper,
                p.model_version,
                p.created_at,
                g.game_date,
                g.home_score,
                g.away_score,
                g.status,
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
        """)
        rows = session.execute(query, params).mappings().all()
        return [dict(r) for r in rows]
    finally:
        session.close()


@st.cache_data(ttl=3600)
def get_calibration_data() -> list:
    """Compute calibration data for game_winner predictions."""
    from sportsprediction.models.metrics import compute_calibration

    engine = _get_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        return compute_calibration(session)
    finally:
        session.close()


@st.cache_data(ttl=3600)
def get_metrics_summary() -> dict:
    """Compute overall prediction metrics."""
    from sportsprediction.models.metrics import compute_metrics

    engine = _get_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        return compute_metrics(session)
    finally:
        session.close()


@st.cache_data(ttl=3600)
def get_player_shots(player_id: int) -> list:
    """Get shot chart data for a player.

    Returns list of dicts with loc_x, loc_y, shot_made, shot_type,
    shot_distance for court visualization.
    """
    session = _get_session()
    try:
        query = text("""
            SELECT loc_x, loc_y, shot_made, shot_type, shot_distance,
                   action_type, shot_zone_basic, game_id
            FROM shot_charts
            WHERE player_id = :player_id
              AND loc_x IS NOT NULL
              AND loc_y IS NOT NULL
            ORDER BY game_id DESC
        """)
        rows = session.execute(query, {"player_id": player_id}).mappings().all()
        return [dict(r) for r in rows]
    finally:
        session.close()
