---
phase: 03-prediction-models
plan: "02"
subsystem: prediction-models
tags: [game-prediction, totals, logistic-regression, quantile-regression, confidence-intervals]
dependency_graph:
  requires: [03-01]
  provides: [GamePredictor, TotalsPredictor]
  affects: [03-03, dashboard]
tech_stack:
  added: [GradientBoostingRegressor-quantile]
  patterns: [quantile-regression-CI, home-away-diff-features]
key_files:
  created:
    - src/hermes/models/game_predictor.py
    - src/hermes/models/totals_predictor.py
    - tests/models/test_game_predictor.py
    - tests/models/test_totals_predictor.py
  modified:
    - src/hermes/models/__init__.py
decisions:
  - LogisticRegression naturally calibrated -- no CalibratedClassifierCV wrapper needed
  - Quantile regression (GBR with quantile loss) for totals CI instead of residual-std approach
  - Shared GAME_FEATURE_COLS and _build_feature_names between both predictors
metrics:
  duration: 3m
  completed: "2026-03-08T21:22:00Z"
  tasks_completed: 2
  tasks_total: 2
  tests_added: 14
  tests_total: 32
---

# Phase 3 Plan 02: Game Prediction Models Summary

GamePredictor (LogisticRegression win probability + Ridge spread) and TotalsPredictor (quantile regression 90% CI) with 16 shared features from TeamFeatures aggregation.

## What Was Built

### GamePredictor
- **Win probability**: LogisticRegression (max_iter=1000), naturally calibrated -- predict_proba gives well-calibrated probabilities without CalibratedClassifierCV
- **Spread prediction**: Ridge regression (alpha=1.0) predicts home_score - away_score
- **Confidence interval**: +/- 1.96 * residual_std from Ridge training residuals
- **Feature engineering**: 16 features from 5 TeamFeatures columns (pace, offensive_rating, defensive_rating, rest_days, season_win_pct) x 3 (home_, away_, diff_) + is_home
- **build_game_features()**: Classmethod queries TeamFeatures for both teams, builds the 16-feature dict

### TotalsPredictor
- **Point prediction**: GradientBoostingRegressor with quantile loss (alpha=0.5, median)
- **Confidence interval**: Two additional GBR models at alpha=0.05 (lower) and alpha=0.95 (upper) for native 90% prediction intervals
- **No normality assumption**: Quantile regression gives proper intervals regardless of error distribution shape
- **GBR hyperparameters**: learning_rate=0.05, n_estimators=200, max_depth=2, min_samples_leaf=9, min_samples_split=9

### Shared Infrastructure
- Both predictors use same GAME_FEATURE_COLS and _build_feature_names() from game_predictor module
- Both inherit BasePredictor ABC (train/predict/get_feature_names/save/load/cross_validate)
- Both handle missing/None features via features_to_array (fills 0.0)

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| aa52f3c | feat | GamePredictor with LogisticRegression win probability and Ridge spread |
| e026cb1 | feat | TotalsPredictor with quantile regression confidence intervals |
| 61e0ab3 | chore | Export GamePredictor and TotalsPredictor from models package |

## Test Coverage

- **test_game_predictor.py** (8 tests): build_game_features aggregation, predict returns PredictionResult, directional win probability (home/away), CI containment, feature names, missing features, None values
- **test_totals_predictor.py** (6 tests): training, predict returns PredictionResult, higher pace -> higher totals, quantile ordering, CI width bounds, cross_validate
- **All 32 model tests passing** (8 base + 8 game + 10 player + 6 totals)

## Decisions Made

1. **LogisticRegression without CalibratedClassifierCV**: LR is naturally well-calibrated for binary classification. Adding CalibratedClassifierCV would add complexity without improving calibration quality.
2. **Quantile regression for totals CI**: GBR with quantile loss gives distribution-free prediction intervals. The residual-std approach (used in GamePredictor for spread) assumes normal errors -- inappropriate for game totals which can be skewed.
3. **Shared feature columns**: TotalsPredictor imports GAME_FEATURE_COLS from game_predictor to ensure consistency. Both models use identical 16-feature format.

## Deviations from Plan

None -- plan executed exactly as written.

## Self-Check: PASSED

- FOUND: src/hermes/models/game_predictor.py
- FOUND: src/hermes/models/totals_predictor.py
- FOUND: tests/models/test_game_predictor.py
- FOUND: tests/models/test_totals_predictor.py
- FOUND: aa52f3c
- FOUND: e026cb1
- FOUND: 61e0ab3
