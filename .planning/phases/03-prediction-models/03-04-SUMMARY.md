---
phase: 03-prediction-models
plan: 04
subsystem: prediction-engine
tags: [prediction, metrics, cli, outcome-resolution, training]
dependency_graph:
  requires: ["03-02", "03-03"]
  provides: ["prediction-engine", "outcome-resolver", "metrics", "cli-predict", "cli-metrics"]
  affects: ["04-dashboard"]
tech_stack:
  added: []
  patterns: ["TDD", "lazy-imports", "mock-model-loading"]
key_files:
  created:
    - src/hermes/models/prediction_engine.py
    - src/hermes/models/training.py
    - src/hermes/models/outcome_resolver.py
    - src/hermes/models/metrics.py
    - tests/models/test_prediction_engine.py
    - tests/models/test_outcome_resolver.py
    - tests/models/test_metrics.py
  modified:
    - src/hermes/cli.py
decisions:
  - "Mock model loading via __new__ bypass in tests for clean isolation"
  - "Brier score ONLY for game_winner (binary); MAE/RMSE for regression types"
  - "Calibration uses manual binning (not sklearn) for transparency"
  - "predict_game stores 3 Prediction rows: game_winner, game_spread, game_total"
  - "Player prop types map: points/rebounds/assists/fg3m -> player_points/player_rebounds/player_assists/player_3pm"
metrics:
  duration_seconds: 402
  completed: "2026-03-08T21:32Z"
  tasks_completed: 2
  tasks_total: 2
  tests_added: 19
  tests_total: 196
requirements: [PRED-05, PRED-06]
---

# Phase 3 Plan 4: Prediction Engine, Outcome Resolution, Metrics Summary

PredictionEngine stores game/player predictions to DB; outcome resolver backfills actuals from Final games; metrics module computes Brier score (classification), MAE/RMSE (regression), CI coverage, and calibration data; CLI provides predict (train/today/resolve) and metrics subcommands.

## Tasks Completed

### Task 1: Training pipeline, PredictionEngine, and outcome resolver
- **Commit**: 963c0cf
- **Files**: training.py, prediction_engine.py, outcome_resolver.py + 2 test files
- Built `train_all_models()` pipeline: builds game + player training data from historical games, trains GamePredictor/TotalsPredictor/PlayerPropsPredictor, saves to disk with version file
- `PredictionEngine` loads models from disk, generates 3 game predictions (winner/spread/total) and 4 player prop predictions per player, stores all as Prediction rows
- `resolve_outcomes()` finds unresolved predictions, validates game is Final with non-null scores, creates PredictionOutcome rows with actual values and is_correct flags
- is_correct logic: game_winner = exact match, game_spread = sign match, game_total/player_* = within CI
- 12 tests: prediction storage, outcome resolution, skip-already-resolved, skip-non-final, skip-null-scores

### Task 2: Metrics module and CLI integration
- **Commit**: 65f1baa
- **Files**: metrics.py, cli.py (updated), test_metrics.py
- `compute_metrics()`: hit rate for all types, Brier score ONLY for game_winner, MAE/RMSE for regression, CI coverage, date range filtering
- `compute_calibration()`: bins game_winner predictions by win_probability, computes actual win rate per bucket
- `format_metrics_report()`: pretty-prints metrics table for CLI output
- CLI: `hermes predict --train/--today/--resolve` and `hermes metrics --type/--start-date/--end-date`
- 7 tests: Brier=0 perfect, Brier=1 always-wrong, MAE correctness, calibration buckets, empty data, date filtering

## Deviations from Plan

None -- plan executed exactly as written.

## Decisions Made

1. **Mock model loading via __new__ bypass**: Instead of patching os.path.exists (which breaks file opens), tests use `PredictionEngine.__new__()` to construct instances with mocked models directly. Cleaner and avoids mock scope issues.
2. **Manual calibration binning**: Used manual bin computation instead of sklearn.calibration.calibration_curve for transparency and fewer dependencies.
3. **Prediction type naming**: fg3m stat maps to "player_3pm" prediction type for consistency with sports terminology.

## Verification Results

- `python -m pytest tests/ -x` -- 196 passed
- `hermes predict --help` -- shows train/today/resolve options
- `hermes metrics --help` -- shows type/date filtering options
- All module imports verified (prediction_engine, metrics, outcome_resolver)
