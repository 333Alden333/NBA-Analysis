---
phase: 04-dashboard
plan: 01
subsystem: dashboard
tags: [streamlit, dashboard, data-access, game-cards]
dependency_graph:
  requires: [hermes.config.settings, hermes.data.models, hermes.models.metrics]
  provides: [hermes.dashboard.data_access, hermes.dashboard.app, hermes.dashboard.components.game_card]
  affects: [hermes.cli]
tech_stack:
  added: [streamlit-1.55, plotly-5.24]
  patterns: [st.cache_resource, st.cache_data, st.navigation, st.fragment, st.Page]
key_files:
  created:
    - src/hermes/dashboard/__init__.py
    - src/hermes/dashboard/app.py
    - src/hermes/dashboard/data_access.py
    - src/hermes/dashboard/pages/__init__.py
    - src/hermes/dashboard/pages/today.py
    - src/hermes/dashboard/pages/player.py
    - src/hermes/dashboard/pages/team.py
    - src/hermes/dashboard/pages/predictions.py
    - src/hermes/dashboard/pages/model_perf.py
    - src/hermes/dashboard/components/__init__.py
    - src/hermes/dashboard/components/game_card.py
  modified:
    - pyproject.toml
    - src/hermes/cli.py
decisions:
  - Raw SQL with text() for dashboard queries -- avoids ORM object serialization issues with Streamlit caching
  - st.fragment(run_every=300) for auto-refresh instead of full page rerun
  - Page file paths relative to project root (where streamlit run is invoked)
metrics:
  duration_seconds: 276
  completed: "2026-03-09T00:39:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 11
  files_modified: 2
  tests_before: 196
  tests_after: 196
---

# Phase 4 Plan 1: Dashboard Foundation and Today's Slate Summary

Streamlit multi-page dashboard with cached data access layer, game card components, and Today's Slate page showing NBA matchups with predictions.

## Task Results

### Task 1: Install dependencies, create data access layer and app shell
- **Commit:** 5aa9a1a
- Added streamlit>=1.35 and plotly>=5.22 to pyproject.toml
- Created data_access.py with 14 cached query functions (get_todays_games, get_player_rolling_stats, get_player_recent_games, get_player_info, get_all_players, get_team_standings, get_team_info, get_team_features, get_team_games, get_all_teams, get_predictions_history, get_calibration_data, get_metrics_summary)
- Created app.py with st.navigation for 5 pages across 3 sections (Games, Browse, Analytics)
- Added `hermes dashboard` CLI subcommand using subprocess.run
- Created 4 placeholder stub pages for player, team, predictions, model_perf

### Task 2: Build Today's Games page with game cards
- **Commit:** ded1f51
- Created render_game_card() component: 3-column layout (away/score/home), win probability progress bar, spread metric, O/U metric, clickable team names via st.page_link
- Built today.py page: date picker, game count, auto-refresh via @st.fragment(run_every=300), "no games" info message when empty

## Deviations from Plan

None -- plan executed exactly as written.

## Verification

- All 196 existing tests pass (no regressions)
- data_access module imports successfully with all 14 query functions
- game_card component imports and has correct structure
- today.py references both get_todays_games and render_game_card
- Streamlit 1.55.0 and Plotly 5.24.1 installed

## Self-Check: PASSED
