---
phase: 04-dashboard
plan: 03
subsystem: dashboard
tags: [dashboard, predictions, calibration, shot-chart, visualization]
dependency_graph:
  requires: [04-01]
  provides: [prediction-tracker, model-performance, shot-chart, calibration-chart]
  affects: [dashboard-navigation]
tech_stack:
  added: [matplotlib-patches]
  patterns: [plotly-calibration, nba-court-coordinates, shot-scatter]
key_files:
  created:
    - src/hermes/dashboard/pages/predictions.py
    - src/hermes/dashboard/components/court.py
  modified:
    - src/hermes/dashboard/pages/model_perf.py
    - src/hermes/dashboard/components/charts.py
    - src/hermes/dashboard/data_access.py
decisions:
  - "matplotlib for court drawing (patches API better than plotly shapes for complex geometry)"
  - "Exception catch around get_player_shots for graceful handling when shot_charts table absent"
metrics:
  duration: 225s
  completed: "2026-03-09T01:12:23Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 3
requirements: [DASH-04, DASH-05]
---

# Phase 4 Plan 03: Prediction Tracker and Model Performance Summary

Prediction tracker with type/date filtering and sortable outcomes table; model performance dashboard with calibration curve, hit rate bars, and NBA shot chart visualization using matplotlib court drawing.

## Task Results

### Task 1: Prediction Tracker page (8677580)
- Created full prediction tracker replacing stub placeholder
- Type filter selectbox mapping 8 prediction types (display names to DB values)
- Date range inputs defaulting to last 30 days
- Summary metrics row: total predictions, resolved count, hit rate %, avg error
- Sortable dataframe with HIT/MISS/PENDING result column, matchup display
- Formatted number columns (2 decimal predicted/actual, percentage win probability)
- Empty state handled gracefully

### Task 2: Model Performance page + components (99afded)
- **charts.py additions**: `calibration_chart()` with perfect-calibration diagonal (dashed gray), bin markers sized by count; `metrics_summary_chart()` with color-coded hit rate bars per prediction type
- **court.py**: Full NBA half-court drawing (hoop, backboard, paint, free throw arcs, restricted area, three-point line with corners, center court arcs); `shot_chart_figure()` with green circles for makes, red x markers for misses
- **model_perf.py**: Three-section layout -- overall metrics cards + bar chart, calibration curve + bin table, shot chart with player selector
- **data_access.py**: Added `get_player_shots()` for shot chart queries from shot_charts table

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing] Added get_player_shots to data_access.py**
- **Found during:** Task 2
- **Issue:** Plan noted function might not exist; it did not exist
- **Fix:** Added cached SQL query function returning loc_x, loc_y, shot_made dicts
- **Files modified:** src/hermes/dashboard/data_access.py
- **Commit:** 99afded

**2. [Rule 2 - Robustness] Exception guard on shot chart query**
- **Found during:** Task 2
- **Issue:** shot_charts table may not exist in all environments
- **Fix:** try/except around get_player_shots call, falls back to empty list
- **Files modified:** src/hermes/dashboard/pages/model_perf.py
- **Commit:** 99afded

## Verification

- predictions.py: AST verification passed (imports, filters, dataframe)
- court.py: Empty shot chart renders successfully
- charts.py: calibration_chart([]) and metrics_summary_chart({}) return valid figures
- model_perf.py: Structure verification passed
- 196/196 tests passing
