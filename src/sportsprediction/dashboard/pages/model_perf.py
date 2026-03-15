"""Model performance page -- calibration curves, metrics, and shot charts."""

import pandas as pd
import streamlit as st

from sportsprediction.dashboard.data_access import (
    get_calibration_data,
    get_metrics_summary,
    get_all_players,
    get_player_shots,
)
from sportsprediction.dashboard.components.charts import calibration_chart, metrics_summary_chart
from sportsprediction.dashboard.components.court import shot_chart_figure

st.title("Model Performance")

# ---- Section 1: Overall Metrics ----
st.header("Overall Metrics")

metrics = get_metrics_summary()
by_type = metrics.get("by_type", {}) if metrics else {}

if by_type:
    # Show metric cards for each prediction type
    cols = st.columns(min(len(by_type), 4))
    for i, (type_name, data) in enumerate(by_type.items()):
        col = cols[i % len(cols)]
        hit_rate = data.get("hit_rate", 0) or 0
        resolved = data.get("total_resolved", 0) or 0
        display_name = type_name.replace("_", " ").title()
        col.metric(display_name, f"{hit_rate * 100:.1f}%", f"{resolved} resolved")

    # Hit rate bar chart
    fig = metrics_summary_chart(by_type)
    st.plotly_chart(fig, use_container_width=True, theme="streamlit")
else:
    st.info(
        "No prediction metrics available yet. "
        "Run predictions and resolve outcomes first."
    )

# ---- Section 2: Calibration (Game Winner) ----
st.header("Calibration -- Game Winner")

cal_data = get_calibration_data()

if cal_data:
    fig = calibration_chart(cal_data)
    st.plotly_chart(fig, use_container_width=True, theme="streamlit")

    # Calibration table
    st.subheader("Calibration Bins")
    cal_df = pd.DataFrame(cal_data)
    if not cal_df.empty:
        cal_df["Bin Range"] = cal_df.apply(
            lambda r: f"{r['bin_lower']:.2f} - {r['bin_upper']:.2f}", axis=1
        )
        display_df = cal_df[["Bin Range", "predicted_avg", "actual_rate", "count"]].copy()
        display_df.columns = ["Bin Range", "Predicted Avg", "Actual Rate", "Count"]
        st.dataframe(
            display_df,
            column_config={
                "Predicted Avg": st.column_config.NumberColumn(format="%.3f"),
                "Actual Rate": st.column_config.NumberColumn(format="%.3f"),
                "Count": st.column_config.NumberColumn(format="%d"),
            },
            use_container_width=True,
            hide_index=True,
        )
else:
    st.info(
        "No calibration data available -- run predictions and resolve outcomes first."
    )

# ---- Section 3: Shot Chart ----
st.header("Shot Chart")

players = get_all_players()

if not players:
    st.info("No player data available. Sync player data first.")
else:
    player_options = {
        f"{p['full_name']} ({p.get('team_abbr', '?')})": p["player_id"]
        for p in players
    }

    selected_label = st.selectbox(
        "Select Player",
        options=list(player_options.keys()),
        index=0,
    )
    selected_player_id = player_options[selected_label]
    player_name = selected_label.split(" (")[0]

    try:
        shots = get_player_shots(selected_player_id)
    except Exception:
        # Table may not exist yet
        shots = []

    if shots:
        fig = shot_chart_figure(shots, f"{player_name} Shot Chart")
        st.pyplot(fig)
        st.caption(f"{len(shots)} shots displayed")
    else:
        st.info(
            "No shot chart data available for this player. "
            "Shot data may need to be synced."
        )
