"""SportsPrediction NBA Analytics Dashboard -- Streamlit entry point."""

import streamlit as st

st.set_page_config(
    page_title="SportsPrediction NBA Analytics",
    page_icon=":basketball:",
    layout="wide",
)

pages = st.navigation({
    "Games": [
        st.Page("src/sportsprediction/dashboard/pages/today.py", title="Today's Slate", icon=":material/sports_basketball:", default=True),
    ],
    "Browse": [
        st.Page("src/sportsprediction/dashboard/pages/player.py", title="Players", icon=":material/person:"),
        st.Page("src/sportsprediction/dashboard/pages/team.py", title="Teams", icon=":material/groups:"),
    ],
    "Analytics": [
        st.Page("src/sportsprediction/dashboard/pages/predictions.py", title="Prediction Tracker", icon=":material/track_changes:"),
        st.Page("src/sportsprediction/dashboard/pages/model_perf.py", title="Model Performance", icon=":material/analytics:"),
    ],
})
pages.run()
