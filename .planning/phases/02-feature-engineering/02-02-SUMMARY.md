---
phase: 02-feature-engineering
plan: 02
subsystem: feature-computation
tags: [rolling-averages, advanced-stats, temporal-discipline, tdd]
dependency_graph:
  requires: [02-01]
  provides: [compute_rolling_stats, compute_advanced_stats, compute_true_shooting_pct, compute_usage_rate, compute_simplified_per]
  affects: [02-03, 02-04]
tech_stack:
  added: []
  patterns: [shift-by-1 temporal discipline, pure formula functions, upsert via session.merge]
key_files:
  created:
    - src/hermes/data/features/rolling.py
    - src/hermes/data/features/advanced.py
  modified:
    - tests/data/test_rolling_features.py
    - tests/data/test_advanced_features.py
decisions:
  - "Per-game percentage averaging (mean of FG% per game, not aggregate FGM/FGA) per NBA analytics convention"
  - "Shift-by-1 rolling implementation for temporal discipline instead of custom window slicing"
  - "Pure formula functions separated from DB logic for testability of TS%, USG%, PER"
metrics:
  duration: 180s
  completed: "2026-03-08T16:28:00Z"
  tasks_completed: 2
  tasks_total: 2
  tests_passing: 11
  tests_skipped: 0
---

# Phase 02 Plan 02: Rolling Averages + Advanced Stats Summary

Rolling averages (5/10/20 windows) with shift-by-1 temporal discipline and advanced stats (TS%, USG%, simplified PER) as pure formula functions with DB persistence.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Rolling average features (FEAT-01) | ab6a11e | src/hermes/data/features/rolling.py, tests/data/test_rolling_features.py |
| 2 | Advanced stats features (FEAT-02) | d52c7b1 | src/hermes/data/features/advanced.py, tests/data/test_advanced_features.py |

## Implementation Details

### Rolling Averages (Task 1)
- 12 stats (points, rebounds, assists, steals, blocks, turnovers, fg_pct, fg3_pct, ft_pct, minutes, plus_minus, offensive_rebounds) across 3 windows (5, 10, 20)
- Temporal discipline via pandas `.rolling().mean().shift(1)` -- game N's rolling average uses only games strictly before N
- DNP exclusion: games with minutes=0 or NULL filtered at query level
- Short history: min_periods=1 with accurate games_available counts
- Percentage stats computed as mean of per-game values (not aggregate)

### Advanced Stats (Task 2)
- Pure formula functions for TS%, USG%, simplified PER -- no DB dependency, easy to unit test
- TS% = PTS / (2 * (FGA + 0.44 * FTA))
- USG% = 100 * ((FGA + 0.44*FTA + TOV) * (TmMP/5)) / (MP * (TmFGA + 0.44*TmFTA + TmTOV))
- Simplified PER = (positive - negative) / minutes * 15
- All formulas return 0.0 on division by zero
- Team aggregates computed per-game via SUM query on box_scores

## Deviations from Plan

None -- plan executed exactly as written.

## Verification Results

- 11/11 tests passing across both test files
- 124 total tests passing, 10 skipped (other plans' stubs)
- Feature modules importable: `from hermes.data.features.rolling import compute_rolling_stats` and `from hermes.data.features.advanced import compute_advanced_stats`

## Self-Check: PASSED

All 5 files found. Both commits (ab6a11e, d52c7b1) verified in git log.
