---
phase: 01-data-foundation
plan: 02
subsystem: data-ingestion
tags: [nba-api, adapter, sync, player, team, game]
dependency_graph:
  requires: [01-01]
  provides: [NbaApiAdapter, sync_players, sync_player_game_logs, sync_teams, sync_standings, sync_game_box_scores, sync_play_by_play, sync_shot_charts]
  affects: [01-03, 01-04]
tech_stack:
  added: [nba_api]
  patterns: [adapter-pattern, upsert-merge, abstract-interface-injection]
key_files:
  created:
    - src/hermes/data/adapters/nba_api_adapter.py
    - src/hermes/data/ingestion/player_sync.py
    - src/hermes/data/ingestion/team_sync.py
    - src/hermes/data/ingestion/game_sync.py
    - tests/data/fixtures/sample_responses.py
    - tests/data/test_nba_api_adapter.py
    - tests/data/test_player_sync.py
    - tests/data/test_team_sync.py
    - tests/data/test_game_sync.py
  modified: []
decisions:
  - Used V3 endpoints (BoxScoreTraditionalV3, PlayByPlayV3, LeagueStandingsV3) for modern column names
  - session.flush() after Team seed in test fixtures to respect FK ordering in SQLite with PRAGMA foreign_keys=ON
metrics:
  tasks_completed: 2
  tasks_total: 2
  tests_added: 42
  tests_passing: 92
  completed: 2026-03-08
---

# Phase 1 Plan 2: NBA API Adapter and Sync Functions Summary

Concrete NbaApiAdapter wrapping 8 nba_api V3 endpoints through rate limiter, plus 3 sync modules (player, team, game) that fetch data via abstract adapter interface, upsert to SQLAlchemy models with raw JSON, and log to SyncLog.

## Task 1: NbaApiAdapter Implementation (TDD)

**Commits:** d530127 (RED), 622f9cc (GREEN)

Implemented `NbaApiAdapter(NBADataAdapter)` with all 8 methods:
- get_player_info -> CommonPlayerInfo
- get_player_game_log -> PlayerGameLog
- get_game_box_score -> BoxScoreTraditionalV3 (returns PlayerStats + TeamStats)
- get_play_by_play -> PlayByPlayV3
- get_shot_chart -> ShotChartDetail
- get_league_standings -> LeagueStandingsV3
- get_season_games -> LeagueGameFinder
- get_schedule -> ScheduleLeagueV2

All methods route through `self.rate_limiter.call_with_retry()`. Tests mock nba_api endpoint classes and verify correct output shape and rate limiter usage. 18 tests.

## Task 2: Player, Team, and Game Sync Functions (TDD)

**Commits:** 126a0fb (RED), 395f4b0 (GREEN)

### player_sync.py
- `sync_players()`: fetches player info via adapter, upserts Player rows with raw_json
- `sync_player_game_logs()`: fetches game logs, creates BoxScore rows with stats

### team_sync.py
- `sync_teams()`: fetches standings, upserts Team rows with city/name/abbreviation
- `sync_standings()`: updates Team W/L/conference rank from standings data

### game_sync.py
- `sync_game_box_scores()`: fetches V3 box scores, creates BoxScore rows per player
- `sync_play_by_play()`: fetches PBP, creates PlayByPlay rows with event details
- `sync_shot_charts()`: fetches shot data, creates ShotChart rows with coordinates

All sync functions: accept abstract `NBADataAdapter`, store `raw_json`, write `SyncLog` entry, handle failures gracefully (log + continue). 24 tests.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed FK constraint ordering in test_game_sync.py fixture**
- **Found during:** Task 2
- **Issue:** SQLite with `PRAGMA foreign_keys=ON` requires parent rows to exist before child INSERT. `session.add()` doesn't guarantee flush order, so Player INSERT could precede Team INSERT, violating the `team_id` FK.
- **Fix:** Added `session.flush()` after adding Team, before adding Player in the `db_session` fixture.
- **Files modified:** tests/data/test_game_sync.py
- **Commit:** 395f4b0

## Verification

```
92 passed in 1.27s
```

All tests pass including Plan 01 schema tests, Plan 02 adapter + sync tests, and Plan 03 injury tests.
