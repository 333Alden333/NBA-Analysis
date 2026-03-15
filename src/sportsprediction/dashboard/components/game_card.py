"""Reusable game card component for displaying NBA matchups."""

import streamlit as st


def render_game_card(game: dict):
    """Render a single game card with teams, score/status, and predictions.

    Args:
        game: Dict with keys from data_access.get_todays_games().
    """
    with st.container(border=True):
        # Header row: Away @ Home (or score if final)
        away_abbr = game.get("away_abbr") or "AWY"
        home_abbr = game.get("home_abbr") or "HME"
        away_team = game.get("away_team") or "Away"
        home_team = game.get("home_team") or "Home"
        status = game.get("status") or ""

        col_away, col_mid, col_home = st.columns([2, 1, 2])

        with col_away:
            if game.get("away_team_id"):
                st.page_link(
                    "src/sportsprediction/dashboard/pages/team.py",
                    label=f"**{away_abbr}**",
                )
            else:
                st.markdown(f"**{away_abbr}**")
            st.caption(away_team)

        with col_mid:
            if status and status.lower() == "final":
                away_score = game.get("away_score") or 0
                home_score = game.get("home_score") or 0
                st.markdown(
                    f"<div style='text-align:center; font-size:1.3em; font-weight:bold;'>"
                    f"{away_score} - {home_score}</div>",
                    unsafe_allow_html=True,
                )
                st.caption("Final")
            else:
                st.markdown(
                    "<div style='text-align:center; font-size:1.2em;'>@</div>",
                    unsafe_allow_html=True,
                )
                if status:
                    st.caption(status)
                else:
                    st.caption("Scheduled")

        with col_home:
            if game.get("home_team_id"):
                st.page_link(
                    "src/sportsprediction/dashboard/pages/team.py",
                    label=f"**{home_abbr}**",
                )
            else:
                st.markdown(f"**{home_abbr}**")
            st.caption(home_team)

        # Predictions section
        win_prob = game.get("win_probability")
        spread = game.get("predicted_spread")
        total = game.get("predicted_total")

        has_predictions = any(v is not None for v in [win_prob, spread, total])

        if has_predictions:
            st.divider()

            if win_prob is not None:
                # win_probability is home team's win probability
                home_pct = win_prob
                away_pct = 1.0 - win_prob

                prob_col1, prob_col2, prob_col3 = st.columns([1, 3, 1])
                with prob_col1:
                    st.markdown(f"**{away_pct:.0%}**")
                with prob_col2:
                    st.progress(home_pct, text="Win Probability")
                with prob_col3:
                    st.markdown(f"**{home_pct:.0%}**")

            pred_cols = st.columns(2)

            if spread is not None:
                with pred_cols[0]:
                    # Negative spread means home favored
                    if spread < 0:
                        label = f"{home_abbr} {spread:+.1f}"
                    else:
                        label = f"{away_abbr} {-spread:+.1f}"
                    st.metric("Spread", label)

            if total is not None:
                with pred_cols[1]:
                    st.metric("O/U", f"{total:.1f}")
