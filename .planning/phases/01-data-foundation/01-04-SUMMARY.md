---
phase: 01-data-foundation
plan: 04
subsystem: data-ingestion
tags: [historical-load, daily-sync, cli, checkpoint-resume, orchestration]
dependency_graph:
  requires: [01-02, 01-03]
  provides: [run_historical_load, run_daily_sync, hermes-cli]
  affects: [feature-engineering, prediction-pipeline, daily-operations]
tech_stack:
  added: []
  patterns: [checkpoint-resume, batch-processing, incremental-sync, tdd]
key_files:
  created:
    - src/hermes/data/ingestion/historical.py
    - src/hermes/data/ingestion/daily_sync.py
    - src/hermes/cli.py
    - src/hermes/__main__.py
    - tests/data/test_historical_load.py
    - tests/data/test_daily_sync.py
  modified:
    - pyproject.toml
decisions:
  - Game IDs tracked per-game in SyncLog (entity_type=historical_game_detail, game_id in season field) for fine-grained checkpoint/resume
  - Daily sync filters games by date string comparison against last sync timestamp
  - CLI uses argparse (no external dependency) with sync subcommand
metrics:
  duration: 300s
  completed: 2026-03-08
requirements: [DATA-04, DATA-01, DATA-02, DATA-03, DATA-05]
---

# Phase 01 Plan 04: Historical Loader, Daily Sync, and CLI Summary

Historical loader processes 3 seasons in batches of 50 with SyncLog-based checkpoint/resume; daily sync orchestrates incremental updates for all entity types with partial-failure resilience; CLI provides --historical, --daily, --status commands.

## Tasks Completed

| # | Task | Commit | Key Files |
|---|------|--------|-----------|
| 1 | Historical data loader with checkpoint/resume (TDD) | dfa003f | src/hermes/data/ingestion/historical.py, tests/data/test_historical_load.py |
| 2 | Daily sync orchestrator and CLI entry points (TDD) | 078e35f | src/hermes/data/ingestion/daily_sync.py, src/hermes/cli.py, src/hermes/__main__.py, tests/data/test_daily_sync.py |

## Implementation Details

### Historical Loader (historical.py)
- `run_historical_load()` processes configured seasons sequentially
- Teams synced first per season (FK dependency for Game rows)
- Game IDs deduplicated (LeagueGameFinder returns 2 rows per game)
- Batches of 50 games: box scores, PBP, shot charts per batch
- SyncLog checkpoint per batch + per-game detail for resume
- Individual batch failures logged and skipped

### Daily Sync (daily_sync.py)
- `run_daily_sync()` checks SyncLog timestamps per entity type
- Sync sequence: teams -> standings -> new games -> injuries
- Only fetches games with GAME_DATE after last sync
- Each step wrapped in try/except for partial-failure resilience
- Summary SyncLog entry with status "success" or "partial"

### CLI (cli.py + __main__.py)
- `hermes sync --historical` runs full historical load
- `hermes sync --daily` runs incremental sync
- `hermes sync --status` prints SyncLog summary table
- `python -m hermes` enabled via __main__.py
- `[project.scripts]` entry in pyproject.toml

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed pandas SettingWithCopyWarning**
- **Found during:** Task 2
- **Issue:** `drop_duplicates()` returns a view; assigning to column triggers warning
- **Fix:** Added `.copy()` after `drop_duplicates()`
- **Files modified:** src/hermes/data/ingestion/daily_sync.py

## Test Results

16 tests passing (7 historical + 9 daily sync/CLI):
- Season processing, deduplication, checkpoint/resume
- Batch sizing, error resilience, SyncLog entries
- All entity type syncs, incremental filtering, partial failures
- CLI argument parsing for all 3 flags

## Self-Check: PASSED
