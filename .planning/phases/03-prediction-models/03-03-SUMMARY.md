---
phase: 03-prediction-models
plan: "03"
subsystem: models
tags: [prediction, player-props, quantile-regression, matchup-analysis]
dependency_graph:
  requires: [base_model, feature_api]
  provides: [PlayerPropPredictor, PlayerPropsPredictor]
  affects: [dashboard, agent]
tech_stack:
  added: []
  patterns: [quantile-regression-ci, matchup-aware-prediction, sparse-data-widening]
key_files:
  created:
    - src/hermes/models/player_predictor.py
    - tests/models/test_player_predictor.py
  modified:
    - src/hermes/models/__init__.py
decisions:
  - Per-stat feature sets (not shared) for domain-appropriate feature selection
  - fg3m uses fg3_pct rolling averages + matchup_avg_fg_pct as proxy (no fg3m-specific matchup stats exist)
  - Matchup features zeroed when matchup_games_played is 0 or None (graceful fallback)
  - CI widening uses sqrt(20/games_available_20) multiplier for sparse data
metrics:
  duration: 168s
  completed: "2026-03-08T21:22:00Z"
  tasks_completed: 1
  tasks_total: 1
  tests_added: 10
  tests_total_passing: 32
---

# Phase 3 Plan 3: Player Prop Predictor Summary

Player prop prediction for points/rebounds/assists/3PM using quantile regression CIs with matchup-specific history and sparse data uncertainty widening.

## What Was Built

### PlayerPropPredictor (single stat)
- Initialized with stat_type ("points", "rebounds", "assists", "fg3m")
- Per-stat feature sets using only features that actually exist in the feature API
- Three GradientBoostingRegressors with quantile loss (alpha=0.05, 0.5, 0.95) for 90% CI
- Matchup-aware: when matchup_games_played is 0 or None, all matchup features zeroed out
- Sparse data CI widening: sqrt(20/games_available_20) multiplier when games_available_20 < 10
- fg3m model uses fg3_pct_avg rolling stats and matchup_avg_fg_pct (NOT nonexistent matchup_avg_fg3m)

### PlayerPropsPredictor (multi-stat wrapper)
- Holds dict of 4 PlayerPropPredictor instances
- train_all(features, targets_dict) trains all stats from shared features
- predict_all(features) returns {stat_name: PredictionResult} for all 4 stats
- save/load via joblib for all 4 models together

## Test Coverage

| Test | Description | Status |
|------|-------------|--------|
| test_points_predictor_trains_and_predicts | Points prediction with quantile CI | PASS |
| test_rebounds_predictor | Rebounds prediction | PASS |
| test_assists_predictor | Assists prediction | PASS |
| test_fg3m_predictor | 3PM prediction | PASS |
| test_matchup_influence_on_points | High matchup avg -> higher prediction | PASS |
| test_missing_matchup_data | Handles 0 and None matchup games | PASS |
| test_wider_ci_with_sparse_data | CI widens with low games_available_20 | PASS |
| test_predict_all_returns_all_stats | Multi-stat predict_all | PASS |
| test_train_all | Multi-stat train_all | PASS |
| test_save_load_roundtrip | Serialization preserves all models | PASS |

## Commits

| Hash | Message |
|------|---------|
| aa52f3c | test(03-03): add failing tests for player prop predictor |
| dcfb12a | feat(03-03): implement PlayerPropPredictor with matchup context and quantile CI |
| a5a018d | chore(03-03): export PlayerPropPredictor and PlayerPropsPredictor from models package |

## Deviations from Plan

None -- plan executed exactly as written.

## Self-Check: PASSED

All files exist. All commits verified. 32/32 model tests passing.
