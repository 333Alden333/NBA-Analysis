"""Player detail page -- rolling trend charts and recent game log."""

import streamlit as st

from sportsprediction.dashboard.data_access import (
    get_all_players,
    get_player_info,
    get_player_recent_games,
    get_player_rolling_stats,
)
from sportsprediction.dashboard.components.charts import player_trend_chart

# Stat selector options: display label -> column prefix
STAT_OPTIONS = {
    "Points": "pts",
    "Rebounds": "reb",
    "Assists": "ast",
    "Steals": "stl",
    "Blocks": "blk",
    "FG%": "fg_pct",
    "3P%": "fg3_pct",
    "TS%": "ts_pct",
    "Usage Rate": "usg_rate",
}

st.title("Players")

# Read player_id from query params
player_id_str = st.query_params.get("player_id")

if not player_id_str:
    # Player selector mode
    st.markdown("Search for a player to view their rolling stats and recent games.")

    players = get_all_players()
    if not players:
        st.warning("No players found. Run `sportspred sync --daily` to populate data.")
        st.stop()

    # Build display labels and lookup
    player_labels = ["-- Select a player --"] + [
        f"{p['full_name']} ({p.get('team_abbr', 'FA')})" for p in players
    ]
    player_ids = [None] + [p["player_id"] for p in players]

    selection = st.selectbox("Player", player_labels)
    idx = player_labels.index(selection)

    if idx > 0:
        st.query_params["player_id"] = str(player_ids[idx])
        st.rerun()

    st.stop()

# Player detail mode
player_id = int(player_id_str)
info = get_player_info(player_id)

if info is None:
    st.error(f"Player ID {player_id} not found.")
    if st.button("Back to player search"):
        del st.query_params["player_id"]
        st.rerun()
    st.stop()

# Header
st.header(info.get("full_name", "Unknown"))
position = info.get("position", "")
team_name = info.get("team_name", "")
jersey = info.get("jersey", "")
subtitle_parts = [p for p in [position, team_name, f"#{jersey}" if jersey else ""] if p]
st.caption(" | ".join(subtitle_parts))

if st.button("Back to player search"):
    del st.query_params["player_id"]
    st.rerun()

st.divider()

# Stat selector and rolling trend chart
stat_label = st.selectbox("Stat", list(STAT_OPTIONS.keys()))
stat_key = STAT_OPTIONS[stat_label]

rolling_df = get_player_rolling_stats(player_id)

if rolling_df.empty:
    st.info("No rolling stats available for this player.")
else:
    fig = player_trend_chart(rolling_df, stat_key, f"{stat_label} Rolling Average")
    st.plotly_chart(fig, use_container_width=True, theme="streamlit")

st.divider()

# Recent games table
st.subheader("Recent Games")
recent = get_player_recent_games(player_id, 10)

if not recent:
    st.info("No recent games found for this player.")
else:
    import pandas as pd

    df = pd.DataFrame(recent)

    # Determine opponent from game data
    display_cols = {}
    if "game_date" in df.columns:
        display_cols["game_date"] = "Date"
    # Build opponent column
    if "home_team_id" in df.columns and "home_abbr" in df.columns:
        df["opponent"] = df.apply(
            lambda r: (
                f"vs {r['away_abbr']}" if r.get("home_team_id") == player_id
                else f"@ {r['home_abbr']}"
            )
            if r.get("player_id") == player_id or True  # team_id matching via box score
            else "",
            axis=1,
        )
        display_cols["opponent"] = "Opp"

    # Core stat columns
    stat_cols = {
        "pts": "PTS",
        "reb": "REB",
        "ast": "AST",
        "stl": "STL",
        "blk": "BLK",
        "tov": "TOV",
        "min": "MIN",
        "fg_pct": "FG%",
        "fg3_pct": "3P%",
        "ft_pct": "FT%",
    }
    for col, label in stat_cols.items():
        if col in df.columns:
            display_cols[col] = label

    available = [c for c in display_cols if c in df.columns]
    show_df = df[available].rename(columns=display_cols)

    # Format percentage columns
    pct_cols = [c for c in ["FG%", "3P%", "FT%"] if c in show_df.columns]
    for col in pct_cols:
        show_df[col] = show_df[col].apply(
            lambda v: f"{v:.1%}" if v is not None and v == v else ""
        )

    st.dataframe(show_df, use_container_width=True, hide_index=True)
