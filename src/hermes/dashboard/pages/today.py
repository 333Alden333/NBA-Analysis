"""Today's NBA Slate -- game cards with predictions for the selected date."""

from datetime import date

import streamlit as st

from hermes.dashboard.data_access import get_todays_games
from hermes.dashboard.components.game_card import render_game_card

st.title("Today's NBA Slate")

selected_date = st.date_input("Select date", value=date.today())
st.caption(f"Games for {selected_date.strftime('%A, %B %d, %Y')}")


@st.fragment(run_every=300)
def games_section():
    """Auto-refreshing games section."""
    games = get_todays_games(str(selected_date))

    if not games:
        st.info(
            "No games scheduled for this date. "
            "If you expected games, check that data has been synced "
            "(`hermes sync --daily`)."
        )
        return

    st.markdown(f"**{len(games)} game{'s' if len(games) != 1 else ''}**")

    for game in games:
        render_game_card(game)


games_section()
