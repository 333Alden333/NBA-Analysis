---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: unknown
last_updated: "2026-03-09T01:13:00Z"
progress:
  total_phases: 6
  completed_phases: 4
  total_plans: 15
  completed_plans: 15
---

# Project State: HermesAnalysis

## Project Reference
- **Core value**: Accurate, current predictions backed by real data
- **Current focus**: Phase 4 - Dashboard
- **Project file**: `.planning/PROJECT.md`
- **Roadmap file**: `.planning/ROADMAP.md`
- **Requirements file**: `.planning/REQUIREMENTS.md`

## Current Position

**Phase**: 4 - Dashboard
**Plan**: 3 of 3 (04-03 complete)
**Status**: Phase 4 complete
**Progress**: ##################### 15/15 plans complete

### Phase Checklist
- [x] Phase 1: Data Foundation
- [ ] Phase 2: Feature Engineering
- [x] Phase 3: Prediction Models
- [x] Phase 4: Dashboard
- [ ] Phase 5: Hermes Agent
- [ ] Phase 6: Computer Vision

## Performance Metrics

| Metric | Value |
|--------|-------|
| Plans completed | 15 |
| Plans attempted | 15 |
| Requirements delivered | 20/32 |
| Phases completed | 4/6 |

## Accumulated Context

### Key Decisions
- 2026-03-07: Phase structure follows bottom-up dependency chain (Data -> Features -> Models -> Dashboard -> Agent -> CV) per research recommendations
- 2026-03-07: CV pipeline placed last (Phase 6) due to highest risk and uncertain footage sourcing -- core system delivers value without it
- 2026-03-07: Phase 6 depends on Phase 3 (not 5) so it can run in parallel with Dashboard/Agent work if desired
- 2026-03-08: Python 3.10 compatibility (system Python) instead of 3.11+
- 2026-03-08: RateLimiter uses time.monotonic() for reliable delay measurement
- 2026-03-08: Broad exception catch on nbainjuries import (JVMNotFoundException not ImportError)
- 2026-03-08: SQLite FK constraint requires flush() between parent/child inserts in test fixtures
- 2026-03-08: Game IDs tracked per-game in SyncLog for fine-grained checkpoint/resume (entity_type=historical_game_detail)
- 2026-03-08: Daily sync filters games by date string comparison against last sync timestamp
- 2026-03-08: CLI uses argparse with sync subcommand (no external dependency)
- 2026-03-08: Explicit column definitions (not dynamic) for all 36 rolling stat columns -- clarity over DRY
- 2026-03-08: Factory fixtures as standalone functions (not class-based) for composability
- 2026-03-08: Per-game percentage averaging (mean of FG% per game, not aggregate FGM/FGA) per NBA analytics convention
- 2026-03-08: Shift-by-1 rolling implementation for temporal discipline
- 2026-03-08: Pure formula functions separated from DB logic for TS%, USG%, PER testability
- 2026-03-08: 3-year lookback window for matchup history (approximate via timedelta, not season parsing)
- 2026-03-08: DRtg uses team possessions (not opponent possessions) per Basketball-Reference convention
- 2026-03-08: season_win_pct is None for first game of season (no prior games to compute from)
- 2026-03-08: ORB fallback: when offensive_rebounds NULL, simplified possession formula
- 2026-03-08: DummyPredictor at module level for joblib pickle compatibility (local classes unpicklable)
- 2026-03-08: scikit-learn pinned <1.8 -- 1.8.0 drops Python 3.10 support
- 2026-03-08: LogisticRegression naturally calibrated -- no CalibratedClassifierCV wrapper needed for win probability
- 2026-03-08: Quantile regression (GBR with quantile loss) for totals CI -- no normality assumption
- 2026-03-08: Shared GAME_FEATURE_COLS between GamePredictor and TotalsPredictor for consistency
- 2026-03-08: Per-stat feature sets for player props (not shared) -- domain-appropriate feature selection
- 2026-03-08: fg3m uses fg3_pct rolling averages + matchup_avg_fg_pct as proxy (no fg3m-specific matchup stats exist)
- 2026-03-08: Matchup features zeroed when matchup_games_played is 0 or None (graceful fallback to rolling avgs)
- 2026-03-08: CI widening for sparse data via sqrt(20/games_available_20) multiplier
- 2026-03-08: Mock model loading via __new__ bypass in tests for clean isolation
- 2026-03-08: Brier score ONLY for game_winner (binary); MAE/RMSE for regression types
- 2026-03-08: Manual calibration binning for transparency (not sklearn.calibration)
- 2026-03-08: fg3m stat maps to "player_3pm" prediction type for sports terminology consistency
- 2026-03-09: Raw SQL with text() for dashboard queries -- avoids ORM object serialization issues with Streamlit caching
- 2026-03-09: st.fragment(run_every=300) for auto-refresh instead of full page rerun
- 2026-03-09: Page file paths relative to project root (where streamlit run is invoked)
- 2026-03-09: Button-based team navigation (st.button) instead of st.page_link for standings drill-down
- 2026-03-09: SOS computed from opponent current-season win percentages in standings data
- 2026-03-09: Horizontal legend placement for chart readability
- 2026-03-09: matplotlib patches for NBA court drawing (better than plotly shapes for complex geometry)
- 2026-03-09: Exception guard on shot_charts table queries (table may not exist in all environments)

### Known Issues
- nba_api is unofficial and can be unstable (Cloudflare rate limiting, endpoint deprecation) -- build adapter pattern from day one
- Hermes Agent released Feb 2026, young project -- plan for workarounds if features underperform
- CV footage sourcing legally and practically uncertain -- Phase 6 may pivot to NBA tracking data via nba_api endpoints
- Academic literature suggests 65-68% accuracy ceiling for NBA game prediction with public data

### Deferred Items
- AUTO-01, AUTO-02: Automated daily briefings and model retraining (v2)
- BET-01 through BET-03: Betting odds integration (v2)
- ACV-01, ACV-02: Advanced CV analysis (v2)

### TODOs
(None yet)

### Blockers
(None)

## Session Continuity

### Last Session
- **Date**: 2026-03-09
- **What happened**: Completed 04-03-PLAN.md -- Prediction tracker page with type/date filtering and HIT/MISS/PENDING table. Model performance page with calibration curve, hit rate bars, NBA shot chart. Phase 4 (Dashboard) fully complete. 196 tests passing.
- **Where stopped**: Completed 04-03-PLAN.md (Phase 4 complete)

### Next Session
- **Start with**: Phase 5 -- Hermes Agent (natural language queries, CLI TUI, learning loop)
- **Context needed**: Dashboard data access layer, prediction/metrics APIs, full model pipeline

---
*State initialized: 2026-03-07*
*Last updated: 2026-03-09T01:13Z*
