---
phase: 04-dashboard
plan: 02
subsystem: dashboard
tags: [streamlit, plotly, charts, player-page, team-page, standings]
dependency_graph:
  requires: [04-01]
  provides: [player-detail-page, team-detail-page, chart-builders]
  affects: [dashboard-navigation]
tech_stack:
  added: [plotly-charts]
  patterns: [query-param-routing, reusable-chart-builders, conference-split-standings]
key_files:
  created:
    - src/hermes/dashboard/components/charts.py
  modified:
    - src/hermes/dashboard/pages/player.py
    - src/hermes/dashboard/pages/team.py
decisions:
  - "Horizontal legend placement for chart readability"
  - "Button-based team navigation (st.button) instead of st.page_link for standings drill-down"
  - "SOS computed from opponent current-season win percentages in standings data"
metrics:
  duration_seconds: 173
  completed: "2026-03-09T01:12:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 2
requirements:
  - DASH-02
  - DASH-03
---

# Phase 4 Plan 02: Player & Team Browse Pages Summary

Plotly chart builders plus player detail page with rolling trend charts and team page with conference standings, ratings trends, and strength of schedule.

## What Was Built

### Chart Builders (components/charts.py)
- `player_trend_chart()`: Rolling average line chart with 5/10/20 game windows for any stat prefix
- `team_ratings_chart()`: Dual-line offensive/defensive rating trend chart
- `team_record_chart()`: Cumulative wins step chart from recent games
- All charts use `plotly_white` template and handle empty data with annotation messages

### Player Detail Page (pages/player.py)
- Player search via `st.selectbox` with all active players formatted as "Name (Team)"
- Query-param routing: selecting a player sets `player_id` and reruns
- Player header with name, position, team, jersey number
- Stat selector dropdown (Points, Rebounds, Assists, Steals, Blocks, FG%, 3P%, TS%, Usage Rate)
- Rolling trend chart rendering via `player_trend_chart()` with Streamlit theme
- Recent games table (last 10) with opponent, core stats, formatted percentages

### Team Page (pages/team.py)
- Standings overview: East/West split, sorted by wins, clickable team buttons
- Team detail via query param routing with back navigation
- Key metrics row: Wins, Losses, Win%, Conference Rank
- Offensive & Defensive Rating trend chart
- Pace trend line chart
- Recent games table (last 20) with opponent, score, W/L result
- Strength of Schedule metric computed from opponent win percentages
- Win-Loss trajectory step chart

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 526d9e7 | Chart builders and player detail page |
| 2 | d9ede97 | Team page with standings, ratings, SOS |

## Deviations from Plan

None -- plan executed exactly as written.

## Verification

- Chart builders tested with empty DataFrames -- all return valid Figures
- Player page source verified: imports data_access functions, uses player_trend_chart, renders plotly_chart
- Team page source verified: uses get_team_standings, get_team_features, team_ratings_chart, team_record_chart
- All 196 existing tests still passing
