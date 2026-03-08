---
phase: 01-data-foundation
plan: 01
subsystem: data-layer
tags: [database, models, adapters, rate-limiter, alembic]
dependency_graph:
  requires: []
  provides: [sqlalchemy-models, adapter-interfaces, rate-limiter, alembic-config]
  affects: [01-02, 01-03, 01-04]
tech_stack:
  added: [sqlalchemy-2.0, alembic, nba_api, nbainjuries, pandas, apscheduler, python-dotenv]
  patterns: [declarative-base, adapter-pattern, rate-limiter, raw-json-storage, pragma-foreign-keys]
key_files:
  created:
    - pyproject.toml
    - src/hermes/__init__.py
    - src/hermes/config.py
    - src/hermes/data/db.py
    - src/hermes/data/models/base.py
    - src/hermes/data/models/player.py
    - src/hermes/data/models/team.py
    - src/hermes/data/models/game.py
    - src/hermes/data/models/box_score.py
    - src/hermes/data/models/play_by_play.py
    - src/hermes/data/models/shot_chart.py
    - src/hermes/data/models/player_tracking.py
    - src/hermes/data/models/injury.py
    - src/hermes/data/models/schedule.py
    - src/hermes/data/models/sync_log.py
    - src/hermes/data/adapters/base.py
    - src/hermes/data/ingestion/rate_limiter.py
    - alembic.ini
    - alembic/env.py
    - tests/conftest.py
    - tests/data/test_models.py
    - tests/data/test_adapters.py
    - tests/data/test_rate_limiter.py
  modified: []
decisions:
  - Python 3.10 compatibility (not 3.11) due to system Python version
  - RateLimiter uses time.monotonic() instead of time.time() for reliable delay measurement
  - Test backoff uses 0.01s multiplier instead of 5s for fast test execution
metrics:
  duration: 276s
  completed: 2026-03-08
  tasks_completed: 2
  tasks_total: 2
  tests_passed: 40
  tests_failed: 0
---

# Phase 1 Plan 1: Data Foundation Schema and Interfaces Summary

SQLAlchemy 2.0 ORM with 10 normalized tables, abstract adapter ABCs, and rate limiter with exponential backoff on 429 errors

## What Was Built

### Task 1: Project setup, all SQLAlchemy models, and Alembic config
- Created `pyproject.toml` with all dependencies (nba_api, sqlalchemy, alembic, pandas, etc.)
- Built 10 SQLAlchemy 2.0 models with mapped_column style:
  - **Player**: NBA PLAYER_ID as PK (no autoincrement), FK to teams
  - **Team**: NBA TEAM_ID as PK (no autoincrement)
  - **Game**: 10-char string GAME_ID as PK, FKs to home/away teams
  - **BoxScore**: auto PK, FKs to games/players/teams, all stat columns
  - **PlayByPlay**: auto PK, FK to games, event tracking columns
  - **ShotChart**: auto PK, FKs to games/players/teams, location/zone data
  - **PlayerTracking**: auto PK, FK to players, tracking metrics
  - **Injury**: auto PK, player/team/status/reason columns
  - **Schedule**: auto PK, unique game_id, FKs to teams
  - **SyncLog**: auto PK, entity_type/last_sync_at/records_synced/season/status (no raw_json)
- All tables except SyncLog have `raw_json` TEXT column for original API responses
- PRAGMA foreign_keys=ON enforced via SQLAlchemy event listener on every connection
- Settings class with db_path, rate limit config, and seasons list (loaded from .env)
- Alembic configured with model metadata targeting SQLite database
- 19 tests: table creation, raw_json presence, PK types, FK enforcement, SyncLog fields

### Task 2: Abstract adapter interfaces and rate limiter
- **NBADataAdapter** ABC with 8 abstract methods: get_player_info, get_player_game_log, get_game_box_score, get_play_by_play, get_shot_chart, get_league_standings, get_season_games, get_schedule
- **InjuryDataAdapter** ABC with 1 abstract method: get_current_injuries
- **RateLimiter** class with wait() for delay enforcement and call_with_retry() with exponential backoff on 429 errors
- 21 tests: abstract instantiation prevention, concrete subclass validation, delay enforcement, retry behavior, max retry exhaustion, non-429 passthrough

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| 0b6f2d4 | feat | Project setup, 10 SQLAlchemy models, Alembic config |
| ad889e2 | feat | Abstract adapter interfaces and rate limiter |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed build-backend in pyproject.toml**
- **Found during:** Task 1
- **Issue:** `setuptools.backends._legacy:_Backend` does not exist in installed setuptools version
- **Fix:** Changed to `setuptools.build_meta`
- **Files modified:** pyproject.toml

**2. [Rule 3 - Blocking] Fixed Python version requirement**
- **Found during:** Task 1
- **Issue:** System Python is 3.10.19, plan specified `requires-python >= 3.11`
- **Fix:** Changed to `requires-python >= 3.10`
- **Files modified:** pyproject.toml

## Verification Results

- `python -m pytest tests/ -v --tb=short`: 40 passed in 0.70s
- `python -c "from hermes.data.models import Base, Player, Team, Game; print('Models OK')"`: OK
- `python -c "from hermes.data.adapters import NBADataAdapter, InjuryDataAdapter; print('Adapters OK')"`: OK
- `python -c "from hermes.data.ingestion import RateLimiter; print('RateLimiter OK')"`: OK

## Self-Check: PASSED

All key files verified present. Both commits (0b6f2d4, ad889e2) confirmed in git log.
