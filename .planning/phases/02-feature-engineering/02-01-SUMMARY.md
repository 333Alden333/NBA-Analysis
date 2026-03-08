---
phase: 02-feature-engineering
plan: 01
subsystem: data-models
tags: [feature-engineering, sqlalchemy, alembic, testing]
dependency_graph:
  requires: [01-data-foundation]
  provides: [PlayerRollingStats, PlayerAdvancedStats, MatchupStats, TeamFeatures, test-fixtures]
  affects: [02-02, 02-03, 02-04]
tech_stack:
  added: []
  patterns: [feature-table-models, factory-fixtures]
key_files:
  created:
    - src/hermes/data/models/player_rolling_stats.py
    - src/hermes/data/models/player_advanced_stats.py
    - src/hermes/data/models/matchup_stats.py
    - src/hermes/data/models/team_features.py
    - src/hermes/data/features/__init__.py
    - alembic/versions/83f355add86d_add_feature_tables.py
    - tests/data/test_rolling_features.py
    - tests/data/test_advanced_features.py
    - tests/data/test_matchup_features.py
    - tests/data/test_team_features.py
    - tests/data/test_temporal_leakage.py
  modified:
    - src/hermes/data/models/__init__.py
    - tests/data/conftest.py
    - tests/data/test_models.py
decisions:
  - "Explicit column definitions (not dynamic) for all 36 rolling stat columns -- clarity over DRY"
  - "Factory fixtures as standalone functions (not class-based) for composability"
metrics:
  duration: 156s
  completed: "2026-03-08T16:22:17Z"
  tasks_completed: 2
  tasks_total: 2
  tests_added: 26
  tests_passing: 108
  tests_skipped: 26
---

# Phase 02 Plan 01: Feature Table Models and Test Scaffolding Summary

Four SQLAlchemy feature models (PlayerRollingStats with 36+3 columns, PlayerAdvancedStats, MatchupStats, TeamFeatures) with Alembic migration, plus 26 test stubs and factory fixtures for all FEAT requirements.

## Task Completion

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Feature table models + Alembic migration | 9544a03 | 4 model files, __init__.py, migration, features pkg |
| 2 | Test fixtures and test stubs | 37709e1 | conftest.py, 5 test files, test_models.py fix |

## What Was Built

### Feature Models (Task 1)
- **PlayerRollingStats**: 36 rolling average columns (12 stats x 3 windows: 5/10/20) plus 3 games_available counters. UniqueConstraint on (player_id, game_id).
- **PlayerAdvancedStats**: TS%, USG%, simplified PER with team-level audit columns (team_fga, team_fta, team_tov, team_minutes).
- **MatchupStats**: Player-vs-team historical averages and differentials for 5 key stats, with matchup_games_played count and has_matchup_history flag.
- **TeamFeatures**: pace, ORtg, DRtg, rest_days, possessions, opponent_possessions, season_win_pct.
- All models follow established Mapped/mapped_column pattern, with indexed FKs and Date columns.
- Alembic migration `83f355add86d` auto-generated with all 4 tables, indexes, and unique constraints.

### Test Scaffolding (Task 2)
- Factory fixtures: make_team, make_player, make_game, make_box_score (with sensible defaults)
- Composite fixtures: sample_team_and_players (2 teams, 3 players), three_game_sequence (3 games with distinct stat lines)
- 26 test stubs across 5 files covering all FEAT-01 through FEAT-05 requirements, all collected and skipped

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated table count assertion in test_models.py**
- **Found during:** Task 2 verification
- **Issue:** `test_ten_tables_total` asserted exactly 10 tables, but adding 4 feature tables made it 14
- **Fix:** Updated assertion from 10 to 14
- **Files modified:** tests/data/test_models.py
- **Commit:** 37709e1

## Verification Results

- All 4 models importable: `from hermes.data.models import PlayerRollingStats, PlayerAdvancedStats, MatchupStats, TeamFeatures`
- Alembic head: `83f355add86d`
- 26 new test stubs: all collected and skipped (no errors)
- Full suite: 108 passed, 26 skipped, 0 failed
