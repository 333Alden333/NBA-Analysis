"""Prediction tracker page -- browse all predictions with filtering."""

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from sportsprediction.dashboard.data_access import get_predictions_history

# -- Mapping from display names to DB prediction_type values --
PREDICTION_TYPES = {
    "All": None,
    "Game Winner": "game_winner",
    "Game Spread": "game_spread",
    "Game Total": "game_total",
    "Player Points": "player_points",
    "Player Rebounds": "player_rebounds",
    "Player Assists": "player_assists",
    "Player 3PM": "player_3pm",
}

st.title("Prediction Tracker")

# -- Filters --
col_type, col_start, col_end = st.columns(3)

with col_type:
    type_label = st.selectbox("Prediction Type", list(PREDICTION_TYPES.keys()))

with col_start:
    default_start = date.today() - timedelta(days=30)
    start_date = st.date_input("Start Date", value=default_start)

with col_end:
    end_date = st.date_input("End Date", value=date.today())

pred_type = PREDICTION_TYPES[type_label]

# -- Fetch data --
rows = get_predictions_history(
    prediction_type=pred_type,
    start_date=str(start_date),
    end_date=str(end_date),
)

if not rows:
    st.info("No predictions found for the selected filters.")
    st.stop()

df = pd.DataFrame(rows)

# -- Computed columns --
def _result_label(row):
    if row.get("is_correct") is None:
        return "PENDING"
    return "HIT" if row["is_correct"] else "MISS"


df["Result"] = df.apply(_result_label, axis=1)

# Error column: absolute difference for resolved predictions
if "predicted_value" in df.columns and "actual_value" in df.columns:
    df["Error"] = df.apply(
        lambda r: abs(r["predicted_value"] - r["actual_value"])
        if r.get("actual_value") is not None and r.get("predicted_value") is not None
        else None,
        axis=1,
    )

# -- Summary metrics at top --
total = len(df)
resolved = df["is_correct"].notna().sum()
correct = (df["is_correct"] == True).sum()  # noqa: E712
hit_rate = (correct / resolved * 100) if resolved > 0 else 0.0

# Average error for regression-type predictions
error_vals = df["Error"].dropna() if "Error" in df.columns else pd.Series(dtype=float)
avg_error = error_vals.mean() if len(error_vals) > 0 else None

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Predictions", total)
m2.metric("Resolved", int(resolved))
m3.metric("Hit Rate", f"{hit_rate:.1f}%")
m4.metric("Avg Error", f"{avg_error:.2f}" if avg_error is not None else "N/A")

# -- Matchup column --
df["Matchup"] = df.apply(
    lambda r: f"{r.get('away_abbr', '?')} @ {r.get('home_abbr', '?')}", axis=1
)

# -- Display table --
display_cols = [
    "game_date",
    "Matchup",
    "prediction_type",
    "predicted_value",
    "win_probability",
    "actual_value",
    "Result",
]
if "Error" in df.columns:
    display_cols.append("Error")

# Only keep columns that exist
display_cols = [c for c in display_cols if c in df.columns]

column_config = {
    "game_date": st.column_config.TextColumn("Date"),
    "Matchup": st.column_config.TextColumn("Matchup"),
    "prediction_type": st.column_config.TextColumn("Type"),
    "predicted_value": st.column_config.NumberColumn("Predicted", format="%.2f"),
    "win_probability": st.column_config.NumberColumn("Win Prob", format="%.1f%%"),
    "actual_value": st.column_config.NumberColumn("Actual", format="%.2f"),
    "Result": st.column_config.TextColumn("Result"),
    "Error": st.column_config.NumberColumn("Error", format="%.2f"),
}

st.dataframe(
    df[display_cols],
    column_config=column_config,
    use_container_width=True,
    hide_index=True,
)
