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


def calibration_chart(calibration_data: list) -> go.Figure:
    """Calibration plot: predicted probability vs actual win rate.

    Args:
        calibration_data: List of dicts with bin_lower, bin_upper,
            predicted_avg, actual_rate, count from compute_calibration().

    Returns:
        Plotly Figure with calibration curve and perfect-calibration diagonal.
    """
    fig = go.Figure()

    if not calibration_data:
        fig.add_annotation(
            text="No calibration data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray"),
        )
        fig.update_layout(
            title="Model Calibration -- Game Winner",
            xaxis_title="Predicted Probability",
            yaxis_title="Actual Win Rate",
        )
        return fig

    predicted = [d["predicted_avg"] for d in calibration_data]
    actual = [d["actual_rate"] for d in calibration_data]
    counts = [d["count"] for d in calibration_data]

    # Marker size proportional to bin count, clamped to reasonable range
    max_count = max(counts) if counts else 1
    sizes = [max(8, min(40, 8 + 32 * (c / max_count))) for c in counts]

    # Perfect calibration diagonal
    fig.add_trace(go.Scatter(
        x=[0, 1], y=[0, 1],
        mode="lines",
        line=dict(dash="dash", color="gray", width=1),
        name="Perfect Calibration",
        showlegend=True,
    ))

    # Actual calibration points
    hover_text = [
        f"Predicted: {p:.3f}<br>Actual: {a:.3f}<br>Count: {c}"
        for p, a, c in zip(predicted, actual, counts)
    ]
    fig.add_trace(go.Scatter(
        x=predicted,
        y=actual,
        mode="markers+lines",
        marker=dict(size=sizes, color="#636EFA"),
        line=dict(color="#636EFA", width=2),
        text=hover_text,
        hoverinfo="text",
        name="Model",
    ))

    fig.update_layout(
        title="Model Calibration -- Game Winner",
        xaxis_title="Predicted Probability",
        yaxis_title="Actual Win Rate",
        xaxis=dict(range=[0, 1]),
        yaxis=dict(range=[0, 1]),
        template="plotly_white",
        height=450,
    )

    return fig


def metrics_summary_chart(by_type: dict) -> go.Figure:
    """Grouped bar chart of hit rate by prediction type.

    Args:
        by_type: Dict mapping type_name -> {hit_rate, total_predictions, ...}

    Returns:
        Plotly Figure with hit rate bars per prediction type.
    """
    fig = go.Figure()

    if not by_type:
        fig.add_annotation(
            text="No metrics data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray"),
        )
        fig.update_layout(title="Hit Rate by Prediction Type")
        return fig

    type_names = []
    hit_rates = []
    resolved_counts = []

    for type_name, data in by_type.items():
        type_names.append(type_name.replace("_", " ").title())
        hit_rates.append((data.get("hit_rate", 0) or 0) * 100)
        resolved_counts.append(data.get("total_resolved", 0) or 0)

    hover_text = [
        f"{name}<br>Hit Rate: {hr:.1f}%<br>Resolved: {rc}"
        for name, hr, rc in zip(type_names, hit_rates, resolved_counts)
    ]

    colors = [
        "#636EFA", "#EF553B", "#00CC96", "#AB63FA",
        "#FFA15A", "#19D3F3", "#FF6692", "#B6E880",
    ]

    fig.add_trace(go.Bar(
        x=type_names,
        y=hit_rates,
        text=[f"{hr:.1f}%" for hr in hit_rates],
        textposition="outside",
        hovertext=hover_text,
        hoverinfo="text",
        marker_color=colors[:len(type_names)],
    ))

    fig.update_layout(
        title="Hit Rate by Prediction Type",
        xaxis_title="Prediction Type",
        yaxis_title="Hit Rate (%)",
        yaxis=dict(range=[0, 105]),
        template="plotly_white",
        height=400,
        showlegend=False,
    )

    return fig
