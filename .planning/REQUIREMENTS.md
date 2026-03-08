# Requirements: HermesAnalysis

**Defined:** 2026-03-07
**Core Value:** Accurate, current predictions backed by real data — the model's quality and data freshness are everything.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Data Pipeline

- [ ] **DATA-01**: System syncs player stats daily from nba_api with rate-limit-aware caching
- [ ] **DATA-02**: System syncs team stats and standings daily
- [ ] **DATA-03**: System syncs game results and box scores daily
- [ ] **DATA-04**: System ingests 3+ seasons of historical data for ML training
- [x] **DATA-05**: System integrates current injury reports into player/team data
- [x] **DATA-06**: Data source adapter pattern allows swapping nba_api for alternatives without rewriting consumers
- [x] **DATA-07**: Local SQLite database stores all player, team, game, and injury data

### Feature Engineering

- [ ] **FEAT-01**: System computes rolling averages (5, 10, 20 game windows) for key player stats
- [ ] **FEAT-02**: System computes advanced stats (PER, true shooting %, usage rate)
- [ ] **FEAT-03**: System computes matchup-specific features (Player X vs Team Y defense history)
- [ ] **FEAT-04**: System computes team-level features (pace, offensive/defensive rating, rest days)
- [ ] **FEAT-05**: All features enforce temporal discipline — no future data leakage

### Predictions

- [ ] **PRED-01**: Model predicts game winner with probability and spread
- [ ] **PRED-02**: Model predicts over/under total combined score
- [ ] **PRED-03**: Model predicts individual player props (points, rebounds, assists, 3PM)
- [ ] **PRED-04**: All predictions include confidence intervals
- [ ] **PRED-05**: System tracks every prediction vs actual outcome in database
- [ ] **PRED-06**: System displays model accuracy metrics (hit rate, calibration, Brier score)
- [ ] **PRED-07**: Matchup-specific analysis shows how player historically performs against opponent

### Computer Vision

- [ ] **CV-01**: Pipeline detects and identifies players from game footage using YOLO
- [ ] **CV-02**: Pipeline tracks player movement across frames (ByteTrack or equivalent)
- [ ] **CV-03**: Pipeline extracts movement pattern features (distance covered, speed, positioning)
- [ ] **CV-04**: CV-extracted features are fed into prediction models as additional inputs

### Hermes Agent

- [ ] **AGENT-01**: Hermes Agent configured with tools for all data and prediction functions
- [ ] **AGENT-02**: User can ask natural language questions and get data-backed analysis
- [ ] **AGENT-03**: Agent remembers past predictions and learns from outcomes over time
- [ ] **AGENT-04**: CLI TUI available for deep interactive queries via Hermes terminal

### Dashboard

- [ ] **DASH-01**: Today's games slate shows upcoming games with predictions and matchup info
- [ ] **DASH-02**: Player pages show stats, trends, and recent performance with charts
- [ ] **DASH-03**: Team pages show standings, stats, strength of schedule
- [ ] **DASH-04**: Prediction tracker displays historical predictions vs actual outcomes
- [ ] **DASH-05**: Interactive charts for stats trends, shot charts, and model performance

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Automation

- **AUTO-01**: Automated daily briefing generated each morning with today's slate and picks
- **AUTO-02**: Scheduled model retraining as new games are played

### Betting

- **BET-01**: Sports betting odds integration from multiple sportsbooks
- **BET-02**: Expected value calculations comparing model predictions to betting lines
- **BET-03**: Betting recommendation engine (BET/PASS with edge calculation)

### Advanced CV

- **ACV-01**: Shot mechanics analysis from footage
- **ACV-02**: Defensive positioning and coverage analysis

## Out of Scope

| Feature | Reason |
|---------|--------|
| Live in-game predictions | Requires real-time data feeds, extreme complexity |
| Mobile native app | Web-first — responsive dashboard covers mobile |
| Social features | Single-user analysis tool, not a community platform |
| Paid data APIs in v1 | Free-first constraint — upgrade only if gaps found |
| Fantasy sports optimization | Different problem domain than game prediction |
| Automated bet placement | Legal/ethical concerns, massive liability |
| Historical game simulation | Cool but doesn't improve prediction accuracy |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 | Pending |
| DATA-02 | Phase 1 | Pending |
| DATA-03 | Phase 1 | Pending |
| DATA-04 | Phase 1 | Pending |
| DATA-05 | Phase 1 | Complete |
| DATA-06 | Phase 1 | Complete |
| DATA-07 | Phase 1 | Complete |
| FEAT-01 | Phase 2 | Pending |
| FEAT-02 | Phase 2 | Pending |
| FEAT-03 | Phase 2 | Pending |
| FEAT-04 | Phase 2 | Pending |
| FEAT-05 | Phase 2 | Pending |
| PRED-01 | Phase 3 | Pending |
| PRED-02 | Phase 3 | Pending |
| PRED-03 | Phase 3 | Pending |
| PRED-04 | Phase 3 | Pending |
| PRED-05 | Phase 3 | Pending |
| PRED-06 | Phase 3 | Pending |
| PRED-07 | Phase 3 | Pending |
| CV-01 | Phase 6 | Pending |
| CV-02 | Phase 6 | Pending |
| CV-03 | Phase 6 | Pending |
| CV-04 | Phase 6 | Pending |
| AGENT-01 | Phase 5 | Pending |
| AGENT-02 | Phase 5 | Pending |
| AGENT-03 | Phase 5 | Pending |
| AGENT-04 | Phase 5 | Pending |
| DASH-01 | Phase 4 | Pending |
| DASH-02 | Phase 4 | Pending |
| DASH-03 | Phase 4 | Pending |
| DASH-04 | Phase 4 | Pending |
| DASH-05 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 32 total
- Mapped to phases: 32
- Unmapped: 0

---
*Requirements defined: 2026-03-07*
*Last updated: 2026-03-07 after roadmap creation*
