"""Team detail page -- standings overview and team stats with charts."""

import streamlit as st

from sportsprediction.dashboard.data_access import (
    get_team_features,
    get_team_games,
    get_team_info,
    get_team_standings,
)
from sportsprediction.dashboard.components.charts import team_ratings_chart, team_record_chart


def _standings_overview():
    """Show conference standings with clickable team names."""
    st.title("NBA Standings")

    standings = get_team_standings()
    if not standings:
        st.warning("No standings data. Run `sportspred sync --daily` to populate data.")
        return

    # Split by conference
    east = [t for t in standings if t.get("conference") == "East"]
    west = [t for t in standings if t.get("conference") == "West"]

    # Sort by wins descending
    east.sort(key=lambda t: (t.get("wins") or 0), reverse=True)
    west.sort(key=lambda t: (t.get("wins") or 0), reverse=True)

    col_east, col_west = st.columns(2)

    for col, conf_name, teams in [
        (col_east, "Eastern Conference", east),
        (col_west, "Western Conference", west),
    ]:
        with col:
            st.subheader(conf_name)
            if not teams:
                st.info(f"No {conf_name} teams found.")
                continue

            for rank, team in enumerate(teams, 1):
                wins = team.get("wins") or 0
                losses = team.get("losses") or 0
                total = wins + losses
                pct = wins / total if total > 0 else 0.0

                team_col, stat_col = st.columns([3, 2])
                with team_col:
                    if st.button(
                        f"{rank}. {team['full_name']}",
                        key=f"team_{team['team_id']}",
                        use_container_width=True,
                    ):
                        st.query_params["team_id"] = str(team["team_id"])
                        st.rerun()
                with stat_col:
                    st.caption(f"{wins}-{losses} ({pct:.3f})")


def _team_detail(team_id: int):
    """Show detailed team page with charts and stats."""
    info = get_team_info(team_id)

    if info is None:
        st.error(f"Team ID {team_id} not found.")
        if st.button("Back to standings"):
            del st.query_params["team_id"]
            st.rerun()
        return

    # Header
    st.header(info.get("full_name", "Unknown"))
    conference = info.get("conference", "")
    division = info.get("division", "")
    subtitle_parts = [p for p in [conference, division] if p]
    if subtitle_parts:
        st.caption(" | ".join(subtitle_parts))

    if st.button("Back to standings"):
        del st.query_params["team_id"]
        st.rerun()

    st.divider()

    # W-L record from standings
    standings = get_team_standings()
    team_standing = next(
        (t for t in standings if t.get("team_id") == team_id), None
    )

    wins = 0
    losses = 0
    win_pct = 0.0
    conf_rank = "-"

    if team_standing:
        wins = team_standing.get("wins") or 0
        losses = team_standing.get("losses") or 0
        total = wins + losses
        win_pct = wins / total if total > 0 else 0.0

        # Compute conference rank
        conf = team_standing.get("conference", "")
        conf_teams = [t for t in standings if t.get("conference") == conf]
        conf_teams.sort(key=lambda t: (t.get("wins") or 0), reverse=True)
        for i, t in enumerate(conf_teams, 1):
            if t.get("team_id") == team_id:
                conf_rank = str(i)
                break

    # Key stats row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Wins", wins)
    c2.metric("Losses", losses)
    c3.metric("Win %", f"{win_pct:.3f}")
    c4.metric("Conf. Rank", conf_rank)

    st.divider()

    # Offensive & Defensive Rating trends
    features_df = get_team_features(team_id)

    if features_df.empty:
        st.info("No team features available.")
    else:
        fig_ratings = team_ratings_chart(features_df)
        st.plotly_chart(fig_ratings, use_container_width=True, theme="streamlit")

        # Pace trend
        if "pace" in features_df.columns:
            import plotly.graph_objects as go

            fig_pace = go.Figure()
            fig_pace.add_trace(go.Scatter(
                x=features_df["game_date"],
                y=features_df["pace"],
                mode="lines",
                line={"color": "#AB63FA", "width": 2},
                hovertemplate="%{x|%b %d}<br>Pace: %{y:.1f}<extra></extra>",
            ))
            fig_pace.update_layout(
                title="Pace",
                xaxis_title="Date",
                yaxis_title="Possessions per Game",
                template="plotly_white",
                margin={"t": 60, "b": 40, "l": 50, "r": 20},
                showlegend=False,
            )
            st.plotly_chart(fig_pace, use_container_width=True, theme="streamlit")

    st.divider()

    # Recent games and SOS
    st.subheader("Recent Games")
    games = get_team_games(team_id, 20)

    if not games:
        st.info("No recent games found.")
    else:
        import pandas as pd

        # Annotate each game with team_id for the record chart
        for g in games:
            g["team_id"] = team_id

        # Win-Loss trajectory chart
        fig_record = team_record_chart(games)
        st.plotly_chart(fig_record, use_container_width=True, theme="streamlit")

        # Games table
        rows = []
        for g in games:
            home_id = g.get("home_team_id")
            is_home = home_id == team_id
            opp = g.get("away_abbr", "?") if is_home else g.get("home_abbr", "?")
            prefix = "vs" if is_home else "@"
            home_score = g.get("home_score") or 0
            away_score = g.get("away_score") or 0
            score = f"{home_score}-{away_score}" if is_home else f"{away_score}-{home_score}"

            if is_home:
                result = "W" if home_score > away_score else "L"
            else:
                result = "W" if away_score > home_score else "L"

            rows.append({
                "Date": g.get("game_date", ""),
                "Opponent": f"{prefix} {opp}",
                "Score": score,
                "Result": result,
            })

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Strength of schedule
        if standings:
            opp_pcts = []
            standings_map = {
                t["team_id"]: t for t in standings
            }
            for g in games:
                home_id = g.get("home_team_id")
                is_home = home_id == team_id
                opp_id = g.get("away_team_id") if is_home else g.get("home_team_id")
                opp_standing = standings_map.get(opp_id)
                if opp_standing:
                    ow = opp_standing.get("wins") or 0
                    ol = opp_standing.get("losses") or 0
                    ot = ow + ol
                    if ot > 0:
                        opp_pcts.append(ow / ot)

            if opp_pcts:
                avg_opp_winpct = sum(opp_pcts) / len(opp_pcts)
                st.metric("Strength of Schedule", f"{avg_opp_winpct:.3f}")
            else:
                st.caption("Strength of schedule unavailable (no opponent data).")


# Main routing
team_id_str = st.query_params.get("team_id")

if team_id_str:
    try:
        _team_detail(int(team_id_str))
    except (ValueError, TypeError):
        st.error("Invalid team ID.")
        if st.button("Back to standings"):
            del st.query_params["team_id"]
            st.rerun()
else:
    _standings_overview()
