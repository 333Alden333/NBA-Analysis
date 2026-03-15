# SportsPrediction — Agent Handoff Document

## What This Is

An AI-powered NBA analysis and prediction platform. Custom ML models generate pre-game predictions (winner, spread, totals, player props) with confidence intervals. A Streamlit dashboard visualizes everything. The system is designed to be orchestrated by **Hermes Agent** (Nous Research) for natural language queries, automated analysis, and a learning loop that improves over time.

The end goal: ask "How will Luka do tonight?" and get a data-backed answer grounded in predictions, matchup history, and confidence intervals. Plus a computer vision pipeline that extracts player movement features from game footage.

## Project Location

- **Code**: `/home/absent/HermesAnalysis/`
- **Database**: `/home/absent/HermesAnalysis/data/hermes.db` (SQLite)
- **Planning docs**: `/home/absent/HermesAnalysis/.planning/`
- **CLI command**: `sportspred` (entry point for data sync, predictions, dashboard)

## Tech Stack

- **Python 3.10** (system Python — no 3.11+ syntax)
- **SQLAlchemy 2.0** with declarative mapped_column style
- **SQLite** with foreign keys enabled
- **Alembic** for migrations
- **scikit-learn** (<1.8, pinned for Python 3.10 compat)
- **Streamlit** — web dashboard (5 pages)
- **nba_api** — primary data source (free, rate-limited)
- **pytest** — 212 tests passing
- **Hermes Agent** (Nous Research) — installed locally at `~/.hermes/`, configured with Nous Portal + hermes-4-70b

## What's Done

### Phase 1: Data Foundation (COMPLETE — 4/4 plans)
- 10+ SQLAlchemy models (Player, Team, Game, BoxScore, Injury, SyncLog, etc.)
- nba_api adapter with rate limiter
- Injury adapter (nbainjuries)
- Historical loader (3 seasons, checkpoint/resume)
- Daily sync orchestrator
- CLI: `sportspred sync --daily/--historical/--status`

### Phase 2: Feature Engineering (3/4 plans COMPLETE)
- Rolling averages (5/10/20 game windows) with shift-by-1 temporal discipline
- Advanced stats (PER, TS%, USG%)
- Matchup features (Player X vs Team Y history, 3-year lookback)
- Team features (pace, ORtg, DRtg, rest days, SOS)

### Phase 3: Prediction Models (COMPLETE — 4/4 plans)
- Game winner prediction (LogisticRegression, win probability + spread)
- Over/under totals (GradientBoosting with quantile regression for CIs)
- Player props (points, rebounds, assists, 3PM with confidence intervals)
- Prediction engine, outcome resolver, accuracy metrics
- CLI: `sportspred predict --train/--today/--resolve`

### Phase 4: Dashboard (COMPLETE — 3/3 plans)
- Streamlit multi-page app: Today's Slate, Player Detail, Team Detail, Predictions Tracker, Model Performance
- Shot charts, calibration curves, trend charts
- CLI: `sportspred dashboard`

## What's Incomplete

### Phase 2 Gap: Feature Engine Orchestrator (02-04)
- [ ] `get_features()` unified API for ML models to consume
- [ ] Feature engine CLI integration (`sportspred features --compute` exists but needs orchestrator)
- [ ] Temporal leakage validation tests (FEAT-05)
- **Impact**: Prediction models work but feature computation isn't fully automated end-to-end

### Phase 5: Hermes Agent Integration (NEEDS FULL REWORK)
The previous implementation used `smolagents` (a Python library) with a local LLM. That has been **removed**. Phase 5 needs to be rebuilt around Hermes Agent (Nous Research).

**What was removed**: smolagents agent factory, TUI (tui.py, agent.py), smolagents/litellm/rich/prompt_toolkit dependencies

**What was kept**:
- `src/sportsprediction/agent/data_queries.py` — Streamlit-free DB query functions (reusable)
- `src/sportsprediction/agent/formatters.py` — LLM-readable text formatters (reusable)
- `tests/agent/test_tools.py` — Tool tests (still passing)

**What needs to be built**:
1. MCP server config connecting Hermes Agent to the SQLite database
2. Custom SKILL.md files teaching Hermes how to analyze NBA data
3. The `data_queries.py` and `formatters.py` logic should be exposed via MCP or referenced in skills
4. Hermes Agent's built-in memory/learning loop replaces the need for custom learning code

**MCP integration** — add to `~/.hermes/config.yaml`:
```yaml
mcp_servers:
  nba:
    command: "uvx"
    args: ["mcp-server-sqlite", "--db-path", "/home/absent/HermesAnalysis/data/hermes.db"]
```

**Requirements to fulfill**:
- [ ] AGENT-01: Hermes Agent has tools for querying player stats, team stats, predictions, model performance
- [ ] AGENT-02: User can ask natural language questions and get data-backed analysis
- [ ] AGENT-03: Agent remembers past predictions and learns from hits/misses
- [ ] AGENT-04: CLI TUI for interactive queries (Hermes Agent provides this natively via `hermes`)

### Phase 6: Computer Vision (NOT STARTED)
- [ ] CV-01: YOLO-based player detection from game footage
- [ ] CV-02: ByteTrack player tracking across frames
- [ ] CV-03: Movement feature extraction (distance, speed, court zone heatmaps)
- [ ] CV-04: CV features fed into prediction models

**CV Concerns**:
- Game footage sourcing is legally and practically uncertain
- May need to pivot to NBA tracking data via nba_api endpoints instead of video
- Hardware: 2x GTX 1080 (8GB each) — sufficient for YOLO + ByteTrack
- This is the highest-risk phase; core system delivers value without it

## Database Schema (key tables)

- `players` — NBA player roster
- `teams` — NBA teams
- `games` — Game results
- `box_scores` — Player game stats
- `injuries` — Current injury reports
- `player_rolling_stats` — Rolling averages (5/10/20 game)
- `player_advanced_stats` — PER, TS%, USG%
- `matchup_stats` — Player vs team history
- `team_features` — Pace, ratings, rest
- `predictions` — Model predictions with confidence
- `prediction_outcomes` — Actual results for tracking accuracy

## Key Files

| File | Purpose |
|------|---------|
| `src/sportsprediction/config.py` | Settings (DB path, API config) |
| `src/sportsprediction/cli.py` | CLI entry point (`sportspred sync/features/predict/metrics/dashboard`) |
| `src/sportsprediction/data/models/` | All SQLAlchemy models |
| `src/sportsprediction/data/ingestion/` | Data sync modules |
| `src/sportsprediction/data/features/` | Feature engineering (rolling, advanced, matchup, team) |
| `src/sportsprediction/models/` | ML prediction models (game, player, totals) |
| `src/sportsprediction/dashboard/` | Streamlit app (5 pages) |
| `src/sportsprediction/agent/data_queries.py` | Reusable DB query functions |
| `src/sportsprediction/agent/formatters.py` | LLM-readable text formatters |
| `data/hermes.db` | SQLite database |
| `.planning/` | Project planning (STATE, ROADMAP, REQUIREMENTS, phase plans) |

## CLI Commands

```bash
cd ~/HermesAnalysis
pip install -e .                    # Install in dev mode
sportspred sync --status            # Check data freshness
sportspred sync --daily             # Pull today's data
sportspred sync --historical        # Backfill 3 seasons
sportspred features --compute       # Compute features
sportspred predict --train          # Train ML models
sportspred predict --today          # Generate today's predictions
sportspred predict --resolve        # Backfill actual outcomes
sportspred metrics                  # View prediction accuracy
sportspred dashboard                # Launch Streamlit UI
pytest                              # Run all tests (212 passing)
```

## Hardware

- **Machine**: Alienware Area-51 R2
- **GPU**: 2x NVIDIA GeForce GTX 1080 (8GB VRAM each)
- **RAM**: 32GB
- **Storage**: ~360GB free
- **OS**: Linux (Ubuntu)

## Constraints

- Free tools preferred, minimize recurring costs
- nba_api as primary data source (rate-limited, cache aggressively)
- 65-68% accuracy ceiling for NBA game prediction with public data
- Python 3.10 only (no 3.11+ syntax)
- scikit-learn <1.8

## End Goal

A system where:
1. Data syncs daily automatically
2. ML models generate pre-game predictions with confidence intervals
3. Streamlit dashboard shows today's slate, player/team pages, prediction tracking
4. Hermes Agent (Nous Research) orchestrates natural language queries — "How will Luka do tonight?" returns data-backed analysis
5. Hermes Agent learns from past predictions (hits/misses) via its built-in memory system
6. (Stretch) CV pipeline extracts movement features from game footage to improve predictions

---
*Generated: 2026-03-11*
