# Architecture Patterns

**Domain:** NBA AI Analysis and Prediction Platform
**Researched:** 2026-03-07

## Recommended Architecture

HermesAnalysis follows a **layered pipeline architecture** with six major subsystems. Each subsystem is independently developable but connected through a shared database and message/event flow.

```
                    +------------------+
                    |  Hermes Agent    |
                    |  (Orchestrator)  |
                    +--------+---------+
                             |
              +--------------+--------------+
              |              |              |
     +--------v---+  +------v------+  +----v--------+
     | Web        |  | CLI / TUI   |  | Scheduler   |
     | Dashboard  |  | Interface   |  | (Cron/Daily)|
     +--------+---+  +------+------+  +----+--------+
              |              |              |
              +--------------+--------------+
                             |
                    +--------v---------+
                    |  Query / API     |
                    |  Layer           |
                    +--------+---------+
                             |
              +--------------+--------------+
              |              |              |
     +--------v---+  +------v------+  +----v--------+
     | ML Models  |  | CV Pipeline |  | Feature     |
     | (Predict)  |  | (Video)     |  | Engine      |
     +--------+---+  +------+------+  +----+--------+
              |              |              |
              +--------------+--------------+
                             |
                    +--------v---------+
                    |  SQLite Database |
                    |  (Central Store) |
                    +--------+---------+
                             |
                    +--------v---------+
                    |  Data Ingestion  |
                    |  Pipeline        |
                    +------------------+
```

## Component Boundaries

### 1. Data Ingestion Pipeline

| Aspect | Detail |
|--------|--------|
| **Responsibility** | Fetch, validate, and store raw NBA data from external sources |
| **Inputs** | nba_api endpoints (stats.nba.com), injury reports, schedule data |
| **Outputs** | Normalized rows in SQLite: schedules, players, games, box scores, play-by-play |
| **Communicates With** | SQLite database (write), Scheduler (triggered by) |
| **Key Constraint** | nba_api rate limits (Cloudflare-enforced). Must use 2-3s delays between requests. Some cloud IPs blocked entirely. |

**Internal modules:**
- `sync_manager.py` -- orchestrates the full ETL sequence
- `schedule_sync.py` -- fetches and updates game schedule
- `player_sync.py` -- fetches player reference data, roster changes
- `boxscore_sync.py` -- fetches team and player box scores
- `pbp_sync.py` -- fetches play-by-play data
- `injury_sync.py` -- scrapes official NBA injury reports

**ETL sequence (order matters):**
```
Schedule -> Players -> Injuries -> Play-by-Play -> Box Scores
```

Each step depends on IDs from prior steps (game IDs from schedule, player IDs from players).

### 2. Feature Engineering Engine

| Aspect | Detail |
|--------|--------|
| **Responsibility** | Transform raw stats into ML-ready features |
| **Inputs** | Raw box scores, PBP, schedule data from SQLite |
| **Outputs** | Feature rows in SQLite `features` table, keyed by game_id + team_id |
| **Communicates With** | SQLite (read raw, write features), ML Models (consumed by) |
| **Key Constraint** | Must prevent data leakage -- game N features use only data from games 1 to N-1 |

**Feature categories:**
- **Rolling averages** (last 5, 10, 20 games): points, rebounds, assists, FG%, 3P%, FT%
- **Lag features**: performance 1-3 games ago
- **Trend features**: delta between recent and season average
- **Advanced stats**: offensive rating, defensive rating, true shooting %, pace, net rating
- **Matchup features**: head-to-head history, opponent defensive rating vs position
- **Situational**: home/away, rest days, back-to-back flag, travel distance
- **Roster context**: minutes distribution, injury-adjusted lineup strength

**Anti-leakage discipline:** All rolling/lag calculations use `.shift(1)` so the current game's data is never included in its own features. This is the single most common bug in NBA prediction systems.

### 3. ML Model Layer

| Aspect | Detail |
|--------|--------|
| **Responsibility** | Train models, generate predictions, track accuracy |
| **Inputs** | Feature rows from Feature Engine |
| **Outputs** | Predictions table (game_id, prediction_type, predicted_value, confidence, actual_value) |
| **Communicates With** | Feature Engine (reads features), SQLite (writes predictions), Hermes Agent (exposes as tools) |

**Model architecture -- multi-head design:**

| Prediction Type | Model | Features Focus |
|----------------|-------|----------------|
| Game winner / spread | XGBoost classifier | Team rolling stats, matchup features, home/away, rest |
| Over/under totals | XGBoost regressor | Pace, offensive/defensive ratings, recent scoring trends |
| Player points | XGBoost regressor | Player rolling stats, opponent defensive rating vs position, minutes projection |
| Player props (rebounds, assists, etc.) | LightGBM regressors | Position-specific features, matchup data |

**Why XGBoost over neural nets for v1:** Tabular data with <100 features and <50K rows. XGBoost/LightGBM consistently outperform neural nets here (validated by multiple NBA prediction papers). Neural nets add complexity without accuracy gain at this data scale. Consider MLP ensemble as v2 upgrade.

**Training approach:**
- `TimeSeriesSplit` cross-validation (never future data in training fold)
- `GridSearchCV` or `Optuna` for hyperparameter tuning
- SHAP for feature importance and model interpretability
- Retrain weekly or when prediction accuracy drops below threshold

**Prediction tracking loop:**
- Every prediction is logged with timestamp and confidence
- After game completes, actual outcome is backfilled
- Weekly accuracy report: hit rate by prediction type, calibration curves
- Feed accuracy data back to Hermes Agent for learning loop

### 4. Computer Vision Pipeline

| Aspect | Detail |
|--------|--------|
| **Responsibility** | Extract player movement, shot patterns, and tactical data from game footage |
| **Inputs** | Video files (MP4) from game footage sources |
| **Outputs** | Structured tracking data in SQLite: player positions, speeds, distances, shot locations, movement patterns |
| **Communicates With** | SQLite (writes tracking data), Feature Engine (consumed as features), Hermes Agent (triggered by) |
| **Key Constraint** | GPU required for inference. Footage sourcing is the biggest unknown -- legal/practical availability TBD. |

**Pipeline stages:**
```
Video Input -> Frame Extraction -> Player Detection (YOLOv8)
    -> Multi-Object Tracking (ByteTrack/Basketball-SORT)
    -> Team Classification (zero-shot CLIP)
    -> Court Keypoint Detection -> Homography Transform
    -> Metric Calculation (speed, distance, spacing)
    -> Structured Output to DB
```

**Technology choices:**
- **Detection:** YOLOv8l (best accuracy/speed tradeoff, pretrained on COCO, fine-tune on basketball data)
- **Tracking:** ByteTrack (state-of-the-art MOT, handles occlusions well). Basketball-SORT is basketball-specific but less mature.
- **Team classification:** Zero-shot with CLIP/Fashion-CLIP on cropped jersey regions. No manual labeling needed.
- **Court mapping:** Keypoint detection model + homography to convert broadcast view to top-down coordinates
- **Pose estimation (optional v2):** HRNet for shot form analysis, fatigue detection

**Processing mode:** Batch (not real-time). Process game footage after it becomes available. ~2-5 minutes per game on a modern GPU.

**IMPORTANT: This is the highest-risk component.** Footage sourcing (League Pass, YouTube, public broadcasts) has legal and practical uncertainty. Build the pipeline to work with whatever footage is available, but do not block other components on CV availability. The system must produce useful predictions without CV data -- CV enriches predictions, it doesn't gate them.

### 5. Hermes Agent (Orchestration Layer)

| Aspect | Detail |
|--------|--------|
| **Responsibility** | Natural language interface, tool orchestration, memory/learning, scheduling, daily briefings |
| **Inputs** | User queries (CLI/TUI, messaging platforms), scheduled triggers |
| **Outputs** | Natural language responses, triggered actions (data sync, predictions, analysis) |
| **Communicates With** | All other components via tool calls |

**Hermes Agent is the brain, not the muscle.** It does not do math, run models, or process video. It orchestrates tools that do those things.

**Tool registration -- expose system capabilities as Hermes tools:**

| Tool Name | Maps To | Description |
|-----------|---------|-------------|
| `get_player_stats` | DB query | Fetch player stats for date range |
| `get_team_stats` | DB query | Fetch team stats and standings |
| `predict_game` | ML model inference | Run prediction for a specific game |
| `predict_player` | ML model inference | Predict player performance |
| `get_schedule` | DB query | Today's games, upcoming schedule |
| `run_data_sync` | Ingestion pipeline | Trigger manual data update |
| `analyze_matchup` | Feature engine + ML | Deep matchup analysis |
| `get_prediction_accuracy` | DB query | How accurate have predictions been |
| `process_game_footage` | CV pipeline | Run CV analysis on video file |
| `get_movement_data` | DB query | Player tracking/movement stats |

**Memory/learning integration:**
- Hermes stores prediction outcomes in its persistent memory
- Builds skills for common query patterns ("How will X do against Y?")
- Learning loop: compares predictions to outcomes, notes patterns in misses
- Daily briefing is a scheduled skill that chains multiple tools

**MCP server approach:** Register tools via MCP so Hermes can discover and call them. This keeps the agent decoupled from implementation details.

### 6. Presentation Layer (Web Dashboard + CLI)

| Aspect | Detail |
|--------|--------|
| **Responsibility** | Visual display of predictions, stats, analysis; interactive queries |
| **Inputs** | Query API layer, Hermes Agent responses |
| **Outputs** | Rendered HTML pages, CLI responses |

**Web Dashboard (Flask):**
- Today's games with predictions and confidence
- Player cards with stats, trends, prediction history
- Prediction accuracy tracker (calibration over time)
- Matchup breakdowns with key factors
- Charts: scoring trends, feature importance, prediction confidence

**CLI (Hermes TUI):**
- Natural language queries: "How will Luka do tonight?"
- Deep analysis: "Compare Celtics vs Lakers matchup history"
- System control: "Run data sync", "Retrain models"
- Daily briefing on demand

**Build order note:** Web dashboard is a Flask app reading from the same SQLite database. It does not need Hermes Agent to function -- it can serve predictions and stats independently. Hermes adds the natural language and orchestration layer on top.

## Data Flow

### Daily Automated Flow
```
1. Scheduler triggers (e.g., 6 AM daily)
2. Data Ingestion: Sync schedule, box scores, injuries from nba_api
3. Feature Engine: Recompute features for new games
4. ML Models: Generate predictions for today's games
5. Hermes Agent: Generate daily briefing
6. Dashboard: Auto-refreshes with new data
```

### Post-Game Flow
```
1. Game completes
2. Data Ingestion: Fetch final box scores
3. Feature Engine: Update rolling stats
4. Prediction Tracker: Backfill actual outcomes, compute accuracy
5. Hermes Agent: Log prediction results in memory, note hits/misses
```

### On-Demand Query Flow
```
1. User asks "How will Jokic do tonight?"
2. Hermes Agent parses query -> calls get_player_stats + predict_player tools
3. ML model runs inference on current features
4. Hermes formats response with stats, prediction, confidence, reasoning
5. Response delivered via CLI or web
```

### CV Enrichment Flow (when available)
```
1. Game footage obtained
2. CV Pipeline: Detect, track, classify, extract metrics
3. Feature Engine: Incorporate movement features into feature set
4. ML Models: Retrain/predict with enriched features
```

## Database Schema (SQLite)

**Core tables:**

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `schedule` | Game schedule | game_id, date, home_team_id, away_team_id, status |
| `players` | Player reference | player_id, name, team_id, position, is_active |
| `teams` | Team reference | team_id, name, abbreviation, conference, division |
| `player_boxscores` | Per-game player stats | game_id, player_id, minutes, points, rebounds, assists, ... |
| `team_boxscores` | Per-game team stats | game_id, team_id, points, fg_pct, rebounds, ... |
| `play_by_play` | Play-level data | game_id, event_num, period, clock, event_type, player_id |
| `injuries` | Injury reports | player_id, status, return_date, report_date |
| `features` | ML-ready features | game_id, team_id, feature_1, feature_2, ... |
| `predictions` | Model predictions | game_id, prediction_type, predicted_value, confidence, actual_value |
| `prediction_log` | Accuracy tracking | prediction_id, timestamp, was_correct, error_magnitude |
| `tracking_data` | CV-derived metrics | game_id, player_id, speed_avg, distance_total, ... |

**Why SQLite:** Zero-config, single-file, perfect for local-first development. The dataset (3 seasons ~4K games, ~50K player-game rows) is well within SQLite's sweet spot. PostgreSQL is overkill unless deploying multi-user cloud service. Migrate to PostgreSQL only if needed for concurrent access or cloud deployment.

## Patterns to Follow

### Pattern 1: Pipeline-as-DAG
**What:** Each pipeline step is an independent function that reads from and writes to the database. Steps are ordered by dependency, not coupled by function calls.
**When:** Always, for the entire data pipeline.
**Why:** Enables re-running individual steps, debugging in isolation, and adding new steps without touching existing code.
```python
# Each step is independent, communicates via database
def sync_schedule(db): ...     # writes to schedule table
def sync_boxscores(db): ...    # reads schedule, writes boxscores
def compute_features(db): ...  # reads boxscores, writes features
def run_predictions(db): ...   # reads features, writes predictions

PIPELINE = [sync_schedule, sync_boxscores, compute_features, run_predictions]
for step in PIPELINE:
    step(db)
```

### Pattern 2: Feature Registry
**What:** All features are defined in a registry (dict/config) with name, computation function, and dependencies. Models reference features by name, not by column index.
**When:** Feature engineering and model training.
**Why:** Prevents feature/column mismatch bugs. Makes it easy to add/remove features without breaking models.
```python
FEATURE_REGISTRY = {
    "pts_rolling_10": {
        "compute": lambda df: df.groupby("player_id")["points"].transform(
            lambda x: x.shift(1).rolling(10).mean()
        ),
        "depends_on": ["player_boxscores"],
        "category": "offensive"
    },
    # ...
}
```

### Pattern 3: Prediction Logging with Backfill
**What:** Every prediction is immediately logged. After the game, actual outcomes are backfilled. Never overwrite -- append.
**When:** All prediction generation and outcome tracking.
**Why:** Enables accuracy analysis, model comparison, and the Hermes learning loop.

### Pattern 4: Tool-Based Agent Integration
**What:** Expose all system capabilities as discrete tools with clear input/output contracts. Hermes Agent calls tools, never touches the database directly.
**When:** All Hermes Agent interactions.
**Why:** Decouples agent from implementation. Tools can be tested independently. Agent can be swapped without changing the system.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Monolithic Notebook
**What:** Putting data fetching, feature engineering, model training, and prediction in one Jupyter notebook.
**Why bad:** Impossible to schedule, version, test, or debug. State leaks between cells. Can't run individual steps.
**Instead:** Modular Python package with clear entry points. Notebooks for exploration only, then extract to modules.

### Anti-Pattern 2: In-Memory Feature Pipeline
**What:** Computing features in pandas DataFrames that never persist to disk/database.
**Why bad:** Must recompute from scratch every time. Can't inspect intermediate results. Slow iteration.
**Instead:** Write features to database after computation. Read from features table for model training.

### Anti-Pattern 3: Data Leakage via Rolling Stats
**What:** Computing rolling averages that include the current game's stats in the prediction for that game.
**Why bad:** Model appears 10-15% more accurate during development but completely fails in production.
**Instead:** Always use `.shift(1)` on rolling calculations. Test by verifying that features for game N use only data from games before N.

### Anti-Pattern 4: Hermes Agent as Database
**What:** Storing stats, predictions, or system state in Hermes Agent memory instead of SQLite.
**Why bad:** Agent memory is fuzzy, not queryable, not structured. Leads to hallucinated stats.
**Instead:** Agent memory stores meta-knowledge (prediction patterns, user preferences). All data lives in SQLite.

### Anti-Pattern 5: Coupling CV Pipeline to Predictions
**What:** Requiring CV data for predictions to work. If footage isn't available, predictions fail.
**Why bad:** CV has the highest uncertainty (footage sourcing). Must not block core functionality.
**Instead:** CV features are optional enrichment. Models trained with and without CV features. Graceful degradation when CV data is missing.

## Suggested Build Order

The architecture has clear dependency layers. Build bottom-up.

```
Phase 1: Foundation
  ├── SQLite schema + migrations
  ├── Data ingestion pipeline (nba_api sync)
  └── Basic feature engineering (rolling stats, advanced metrics)

Phase 2: Prediction Core
  ├── ML models (XGBoost game winner, player points)
  ├── Prediction logging + backfill
  └── Accuracy tracking

Phase 3: Interfaces
  ├── Flask web dashboard (read from DB, display predictions)
  ├── CLI entry points for manual operations
  └── Scheduler (cron-based daily pipeline)

Phase 4: Hermes Integration
  ├── Tool registration (expose DB queries + ML as tools)
  ├── Natural language query support
  ├── Daily briefing generation
  └── Memory/learning loop for prediction tracking

Phase 5: CV Pipeline
  ├── YOLOv8 player detection + ByteTrack tracking
  ├── Court homography + team classification
  ├── Movement metric extraction
  └── CV feature integration into ML models

Phase 6: Polish + Expansion
  ├── Additional prediction types (props, totals)
  ├── Model ensembles (XGBoost + LightGBM + MLP)
  ├── Enhanced dashboard (charts, matchup views)
  └── Prediction accuracy optimization
```

**Why this order:**
1. **Data must come first** -- nothing works without data in the database
2. **Features before models** -- models consume features, not raw stats
3. **Models before interfaces** -- dashboard needs predictions to display
4. **Hermes after models** -- agent orchestrates tools that must already exist
5. **CV last** -- highest risk, longest research tail, optional enrichment
6. **Polish after everything works** -- expand prediction types and accuracy once the core loop is proven

## Scalability Considerations

| Concern | At 1 User (Local) | At 10 Users (Shared) | At 100+ Users (Cloud) |
|---------|-------------------|---------------------|----------------------|
| Database | SQLite (single file) | SQLite with WAL mode | Migrate to PostgreSQL |
| ML Inference | On-demand, <1s | Pre-compute daily, cache | Redis cache + async workers |
| CV Processing | Local GPU, batch | Dedicated GPU worker | Cloud GPU (Lambda/RunPod) |
| Web Dashboard | Flask dev server | Gunicorn + nginx | Cloud deploy (Fly.io/Railway) |
| Data Sync | Single cron job | Single cron job | Celery task queue |
| Hermes Agent | Local CLI | Gateway mode (multi-platform) | Gateway + rate limiting |

**Start local, stay local until there's a reason to scale.** SQLite handles the data volume of 3 NBA seasons with ease. The prediction models are lightweight (XGBoost inference is <100ms). The dashboard is a simple Flask app. Only the CV pipeline needs GPU, and it runs in batch mode.

## Sources

- [NBA_AI - Complete NBA prediction system](https://github.com/NBA-Betting/NBA_AI) - Architecture reference, pipeline design, SQLite schema
- [nba_api Python library](https://github.com/swar/nba_api) - Primary data source, endpoint documentation
- [Hermes Agent - Nous Research](https://nousresearch.com/hermes-agent/) - Agent architecture, tool system, memory
- [Hermes Agent GitHub](https://github.com/NousResearch/hermes-agent) - Implementation details, MCP support
- [XGBoost + SHAP for NBA prediction](https://pmc.ncbi.nlm.nih.gov/articles/PMC11265715/) - Model architecture, feature engineering
- [NBA Player Performance with XGBoost](https://medium.com/ai-builder/predicting-nba-player-performance-with-xgboost-a-time-series-approach-7affce3ef614) - Time series feature engineering
- [Basketball CV Analytics Pipeline](https://github.com/RidwanHaque/AI-ML-CV-NBA-Basketball-Analytics-System-Interface) - YOLOv8 + ByteTrack + CLIP architecture
- [BGS-YOLO Basketball Detection](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0326964) - State-of-art basketball detection model
- [nba-sql Database Schema](https://github.com/mpope9/nba-sql) - Snowflake schema design for NBA data
- [NBA Stats MCP Server](https://skywork.ai/skypage/en/nba-stats-mcp-server-ai-engineer/1981535957210427392) - MCP integration pattern for NBA data
