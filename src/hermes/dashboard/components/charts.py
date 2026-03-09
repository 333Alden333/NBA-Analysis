"""Reusable Plotly chart builders for the dashboard."""

import pandas as pd
import plotly.graph_objects as go


def player_trend_chart(df: pd.DataFrame, stat: str, title: str) -> go.Figure:
    """Build a rolling average trend chart for a player stat.

    Args:
        df: DataFrame with columns like {stat}_avg_5, {stat}_avg_10, {stat}_avg_20
            and a game_date column.
        stat: Column prefix (e.g., "pts", "reb", "ast").
        title: Display title for the chart.

    Returns:
        Plotly Figure with 3 lines for 5/10/20 game rolling windows.
    """
    fig = go.Figure()

    if df.empty:
        fig.update_layout(
            title=title,
            template="plotly_white",
            annotations=[{
                "text": "No data available",
                "xref": "paper", "yref": "paper",
                "x": 0.5, "y": 0.5,
                "showarrow": False,
                "font": {"size": 16, "color": "gray"},
            }],
        )
        return fig

    windows = [
        (5, "5-Game", "#636EFA"),
        (10, "10-Game", "#EF553B"),
        (20, "20-Game", "#00CC96"),
    ]

    for window, label, color in windows:
        col = f"{stat}_avg_{window}"
        if col not in df.columns:
            continue
        fig.add_trace(go.Scatter(
            x=df["game_date"],
            y=df[col],
            mode="lines",
            name=label,
            line={"color": color, "width": 2},
            hovertemplate="%{x|%b %d}<br>%{y:.1f}<extra>" + label + "</extra>",
        ))

    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title=title,
        template="plotly_white",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
        margin={"t": 60, "b": 40, "l": 50, "r": 20},
        hovermode="x unified",
    )

    return fig


def team_ratings_chart(df: pd.DataFrame) -> go.Figure:
    """Build offensive and defensive rating trend chart.

    Args:
        df: DataFrame with game_date, off_rating, def_rating columns.

    Returns:
        Plotly Figure with dual lines for offensive and defensive rating.
    """
    fig = go.Figure()

    if df.empty:
        fig.update_layout(
            title="Offensive & Defensive Rating",
            template="plotly_white",
            annotations=[{
                "text": "No data available",
                "xref": "paper", "yref": "paper",
                "x": 0.5, "y": 0.5,
                "showarrow": False,
                "font": {"size": 16, "color": "gray"},
            }],
        )
        return fig

    fig.add_trace(go.Scatter(
        x=df["game_date"],
        y=df["off_rating"],
        mode="lines",
        name="Offensive Rating",
        line={"color": "#636EFA", "width": 2},
        hovertemplate="%{x|%b %d}<br>ORtg: %{y:.1f}<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=df["game_date"],
        y=df["def_rating"],
        mode="lines",
        name="Defensive Rating",
        line={"color": "#EF553B", "width": 2},
        hovertemplate="%{x|%b %d}<br>DRtg: %{y:.1f}<extra></extra>",
    ))

    fig.update_layout(
        title="Offensive & Defensive Rating",
        xaxis_title="Date",
        yaxis_title="Rating",
        template="plotly_white",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
        margin={"t": 60, "b": 40, "l": 50, "r": 20},
        hovermode="x unified",
    )

    return fig


def team_record_chart(games: list) -> go.Figure:
    """Build a cumulative wins step chart from recent games.

    Args:
        games: List of game dicts with game_date, home_team_id, away_team_id,
               home_score, away_score. Should be in chronological order
               (oldest first).

    Returns:
        Plotly Figure with step line showing W-L trajectory.
    """
    fig = go.Figure()

    if not games:
        fig.update_layout(
            title="Win-Loss Trajectory",
            template="plotly_white",
            annotations=[{
                "text": "No games available",
                "xref": "paper", "yref": "paper",
                "x": 0.5, "y": 0.5,
                "showarrow": False,
                "font": {"size": 16, "color": "gray"},
            }],
        )
        return fig

    # Sort chronologically (games may come in desc order from query)
    sorted_games = sorted(games, key=lambda g: g.get("game_date", ""))

    dates = []
    cum_wins = []
    wins = 0

    # Determine team_id from first game context
    # We use the fact that all games belong to the same team
    team_id = sorted_games[0].get("team_id")

    for g in sorted_games:
        dates.append(g["game_date"])
        home_id = g.get("home_team_id")
        home_score = g.get("home_score", 0) or 0
        away_score = g.get("away_score", 0) or 0

        is_home = (home_id == team_id) if team_id else True
        if is_home:
            won = home_score > away_score
        else:
            won = away_score > home_score

        if won:
            wins += 1
        cum_wins.append(wins)

    fig.add_trace(go.Scatter(
        x=dates,
        y=cum_wins,
        mode="lines",
        line={"shape": "hv", "color": "#00CC96", "width": 2},
        name="Cumulative Wins",
        hovertemplate="%{x|%b %d}<br>Wins: %{y}<extra></extra>",
    ))

    fig.update_layout(
        title="Win-Loss Trajectory",
        xaxis_title="Date",
        yaxis_title="Cumulative Wins",
        template="plotly_white",
        margin={"t": 60, "b": 40, "l": 50, "r": 20},
        showlegend=False,
    )

    return fig
