---
phase: 02-feature-engineering
plan: 03
subsystem: feature-computation
tags: [matchup-features, team-features, pace, efficiency-ratings, rest-days, tdd]
dependency_graph:
  requires: [02-01]
  provides: [matchup-stats-computation, team-features-computation]
  affects: [02-04, 03-01]
tech_stack:
  added: []
  patterns: [temporal-discipline, pure-formula-functions, upsert-pattern, basketball-reference-formulas]
key_files:
  created:
    - src/hermes/data/features/matchup.py
    - src/hermes/data/features/team.py
  modified:
    - tests/data/test_matchup_features.py
    - tests/data/test_team_features.py
decisions:
  - "3-year lookback window for matchup history (approximate via timedelta, not season parsing)"
  - "DRtg uses team possessions (not opponent possessions) per Basketball-Reference convention"
  - "season_win_pct is None for first game of season (no prior games to compute from)"
  - "ORB fallback: when offensive_rebounds NULL, simplified possession formula (FGA + 0.44*FTA + TOV)"
metrics:
  duration: 244s
  completed: "2026-03-08T16:28:35Z"
  tasks_completed: 2
  tasks_total: 2
  tests_added: 16
  tests_passing: 135
  tests_skipped: 5
---

# Phase 2 Plan 3: Matchup & Team Features Summary

Matchup features (player-vs-team-defense history) and team features (pace, ORtg, DRtg, rest days, win pct) with pure formulas and temporal discipline via TDD.

## Tasks Completed

### Task 1: Implement matchup features (FEAT-03)
- **Commit:** cb43234
- **Files:** `src/hermes/data/features/matchup.py`, `tests/data/test_matchup_features.py`
- `compute_matchup_stats()`: For each game, looks back at player's historical performance against opponent team within 3-year window
- Minimum 3-game threshold: below threshold sets `has_matchup_history=False` with NULL stat columns
- Computes matchup averages (points, rebounds, assists, fg_pct, plus_minus) and diffs from player's overall average
- `compute_matchup_stats_for_games()`: Convenience wrapper for batch processing
- 5 tests: avg computation, diff computation, no-history fallback, minimum threshold, lookback window

### Task 2: Implement team-level features (FEAT-04)
- **Commit:** 5af7c76
- **Files:** `src/hermes/data/features/team.py`, `tests/data/test_team_features.py`
- Pure formula functions: `estimate_possessions`, `compute_offensive_rating`, `compute_pace`, `compute_rest_days`
- `compute_team_features()`: Aggregates box scores per team per game, computes pace/ORtg/DRtg/rest/win_pct with temporal discipline
- Possession formula: `FGA + 0.44*FTA - ORB + TOV` (falls back to simplified without ORB)
- Rest days: gap between games, season opener defaults to 3
- Rolling `season_win_pct`: wins/games from prior games only
- 11 tests: 5 DB integration (pace, ORtg, DRtg, rest days, win pct) + 6 pure function tests

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

- `pytest tests/data/test_matchup_features.py tests/data/test_team_features.py -x -v`: 16 passed
- `pytest tests/ -x`: 135 passed, 5 skipped (pre-existing temporal leakage skips)
- Import check: `from hermes.data.features.matchup import compute_matchup_stats; from hermes.data.features.team import compute_team_features` -- OK

## Self-Check: PASSED

All 4 files found. Both commit hashes verified in git log.
