# Roadmap: HermesAnalysis

**Created:** 2026-03-07
**Granularity:** Standard
**Phases:** 6
**Coverage:** 32/32 v1 requirements mapped

## Phases

- [x] **Phase 1: Data Foundation** - Local database with daily NBA data sync pipeline
- [ ] **Phase 2: Feature Engineering** - ML-ready features with temporal anti-leakage discipline
- [ ] **Phase 3: Prediction Models** - Game, totals, and player prop predictions with tracking
- [ ] **Phase 4: Dashboard** - Streamlit web interface surfacing predictions and stats
- [ ] **Phase 5: Hermes Agent** - Natural language queries, CLI TUI, and learning loop
- [ ] **Phase 6: Computer Vision** - Player detection and tracking from game footage

## Phase Details

### Phase 1: Data Foundation
**Goal**: The system has a complete, current, and reliable local NBA database that updates itself daily
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, DATA-07
**Success Criteria** (what must be TRUE):
  1. Running the sync command populates the local SQLite database with player stats, team stats, and game box scores from the current season
  2. Running the historical ingest loads 3+ seasons of data without manual intervention
  3. Injury reports for today's games are available in the database and update daily
  4. Swapping the data source adapter (e.g., nba_api to balldontlie) requires zero changes to downstream consumers
  5. The daily sync completes without hitting rate limits and logs data freshness timestamps
**Plans:** 4 plans

Plans:
- [x] 01-01-PLAN.md — Project setup, DB schema (10 models), adapter interfaces, rate limiter, Alembic
- [x] 01-02-PLAN.md — nba_api adapter + player/team/game sync functions
- [x] 01-03-PLAN.md — Injury adapter (nbainjuries) + injury sync
- [x] 01-04-PLAN.md — Historical loader (3 seasons, checkpoint/resume) + daily sync orchestrator + CLI

### Phase 2: Feature Engineering
**Goal**: Raw stats are transformed into ML-ready feature rows that respect temporal boundaries
**Depends on**: Phase 1
**Requirements**: FEAT-01, FEAT-02, FEAT-03, FEAT-04, FEAT-05
**Success Criteria** (what must be TRUE):
  1. For any player on any date, the system produces rolling average features (5/10/20 game windows) using only data available before that date
  2. Advanced stats (PER, true shooting %, usage rate) are computed and stored for every player-game record
  3. Matchup features exist showing Player X historical performance against Team Y defense
  4. Team-level features (pace, offensive/defensive rating, rest days) are computed for every team-game record
  5. A temporal validation check confirms zero future data leakage across the entire feature set
**Plans:** 4 plans

Plans:
- [ ] 02-01-PLAN.md — Feature table models (4 tables), Alembic migration, test fixtures and stubs
- [ ] 02-02-PLAN.md — Rolling averages (FEAT-01) + advanced stats (FEAT-02) with tests
- [ ] 02-03-PLAN.md — Matchup features (FEAT-03) + team features (FEAT-04) with tests
- [ ] 02-04-PLAN.md — Feature engine orchestrator, CLI integration, temporal leakage tests (FEAT-05), get_features() API

### Phase 3: Prediction Models
**Goal**: The system produces calibrated, tracked predictions for games, totals, and player props
**Depends on**: Phase 2
**Requirements**: PRED-01, PRED-02, PRED-03, PRED-04, PRED-05, PRED-06, PRED-07
**Success Criteria** (what must be TRUE):
  1. Before any game today, the system outputs a winner prediction with win probability, spread estimate, and confidence interval
  2. Before any game today, the system outputs an over/under total prediction with confidence interval
  3. For any player in today's games, the system outputs predicted points, rebounds, assists, and 3PM with confidence intervals
  4. Every prediction is logged to the database, and after the game completes, actual outcomes are backfilled automatically
  5. A model performance page shows hit rate, Brier score, and calibration metrics across all historical predictions
**Plans**: TBD

### Phase 4: Dashboard
**Goal**: Users can browse today's predictions, player/team stats, and model performance through a web interface
**Depends on**: Phase 3
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05
**Success Criteria** (what must be TRUE):
  1. Opening the dashboard shows today's games with predictions, matchup info, and key stats for each game
  2. Clicking a player shows their stats page with rolling trend charts and recent performance
  3. Clicking a team shows standings, team stats, and strength of schedule
  4. A prediction tracker page displays all past predictions alongside actual outcomes with filtering
  5. Interactive charts render for stats trends, shot charts, and model calibration plots
**Plans**: TBD

### Phase 5: Hermes Agent
**Goal**: Users can ask natural language questions and get data-backed analysis through a conversational interface
**Depends on**: Phase 4
**Requirements**: AGENT-01, AGENT-02, AGENT-03, AGENT-04
**Success Criteria** (what must be TRUE):
  1. Hermes Agent has registered tools for querying player stats, team stats, predictions, and model performance
  2. A user can type "How will Luka do tonight?" and receive a response grounded in actual model predictions and matchup data
  3. The agent can recall its past predictions and reference whether they hit or missed when asked
  4. The CLI TUI launches and supports multi-turn interactive queries with the agent
**Plans**: TBD

### Phase 6: Computer Vision
**Goal**: Game footage is processed to extract player movement features that enrich prediction models
**Depends on**: Phase 3
**Requirements**: CV-01, CV-02, CV-03, CV-04
**Success Criteria** (what must be TRUE):
  1. Given a game footage clip, the pipeline detects and identifies individual players by jersey/team
  2. Player positions are tracked across consecutive frames maintaining identity through occlusions
  3. Movement metrics (distance covered, average speed, court zone heatmap) are extracted per player per game
  4. CV-extracted features are available as additional columns in the feature set and improve model accuracy when included
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Foundation | 4/4 | Complete | 2026-03-08 |
| 2. Feature Engineering | 0/4 | In progress | - |
| 3. Prediction Models | 0/? | Not started | - |
| 4. Dashboard | 0/? | Not started | - |
| 5. Hermes Agent | 0/? | Not started | - |
| 6. Computer Vision | 0/? | Not started | - |

## Dependency Graph

```
Phase 1: Data Foundation
  |
  v
Phase 2: Feature Engineering
  |
  v
Phase 3: Prediction Models
  |         |
  v         v
Phase 4   Phase 6: Computer Vision
  |
  v
Phase 5: Hermes Agent
```

Note: Phase 6 (CV) depends on Phase 3 (not Phase 4/5) because CV features feed into prediction models. It can run in parallel with Phases 4-5 if desired.

---
*Roadmap created: 2026-03-07*
*Last updated: 2026-03-08*
