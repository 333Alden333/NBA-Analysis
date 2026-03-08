---
phase: 01-data-foundation
plan: 03
subsystem: data-ingestion
tags: [injuries, adapter-pattern, nbainjuries, sync]
dependency_graph:
  requires: [01-01]
  provides: [NbaInjuriesAdapter, sync_injuries]
  affects: [prediction-pipeline, feature-engineering]
tech_stack:
  added: [nbainjuries]
  patterns: [adapter-pattern, snapshot-sync, tdd]
key_files:
  created:
    - src/hermes/data/adapters/injuries_adapter.py
    - src/hermes/data/ingestion/injury_sync.py
    - tests/data/test_injuries_adapter.py
    - tests/data/test_injury_sync.py
decisions:
  - Catch broad Exception (not just ImportError) on nbainjuries import because jpype throws JVMNotFoundException when Java is missing
  - Injuries use delete-then-insert pattern (point-in-time snapshot, not historical accumulation)
metrics:
  duration: 82s
  completed: 2026-03-08
requirements: [DATA-05]
---

# Phase 01 Plan 03: Injury Data Adapter and Sync Summary

NbaInjuriesAdapter wraps nbainjuries package with graceful Java/import fallback; sync_injuries replaces DB snapshot with current report, stores raw JSON, writes SyncLog on success or failure.

## Tasks Completed

| # | Task | Commit | Key Files |
|---|------|--------|-----------|
| 1 | RED: Failing tests for adapter and sync | bf32c1c | tests/data/test_injuries_adapter.py, tests/data/test_injury_sync.py |
| 1 | GREEN: Implementation passing all tests | d3c8456 | src/hermes/data/adapters/injuries_adapter.py, src/hermes/data/ingestion/injury_sync.py |

## Implementation Details

### NbaInjuriesAdapter
- Implements `InjuryDataAdapter` ABC from `base.py`
- Wraps `nbainjuries.injury.get_reportdata()` call
- Gracefully handles missing Java (JVM) -- catches broad `Exception` on import since jpype throws `JVMNotFoundException`, not `ImportError`
- Returns empty DataFrame on any failure

### sync_injuries()
- Accepts abstract `InjuryDataAdapter` (not concrete class) for testability
- Delete-then-insert pattern: clears all existing Injury rows, inserts current snapshot
- Stores raw row data as JSON in `raw_json` column
- Writes `SyncLog` entry with `entity_type="injuries"`, record count, timestamp
- On adapter error: rolls back, writes SyncLog with `status="failed"`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Broadened exception catch on nbainjuries import**
- **Found during:** Task 1 GREEN phase
- **Issue:** nbainjuries triggers jpype `JVMNotFoundException` (not `ImportError`) when Java is missing
- **Fix:** Changed `except ImportError` to `except Exception` in module-level import
- **Files modified:** src/hermes/data/adapters/injuries_adapter.py

## Verification

- 11 new tests (4 adapter + 7 sync) all passing
- Full test suite: 51/51 passing
- Adapter pattern validated: NbaInjuriesAdapter is subclass of InjuryDataAdapter
