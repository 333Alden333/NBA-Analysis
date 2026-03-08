# Project Research Summary

**Project:** HermesAnalysis - NBA AI Analysis & Prediction Platform
**Domain:** Sports analytics / ML prediction / Computer vision
**Researched:** 2026-03-07
**Confidence:** HIGH

## Executive Summary

HermesAnalysis is a local-first NBA analysis and prediction platform combining statistical ML models, computer vision, and an AI agent orchestration layer (Hermes Agent by Nous Research). The well-established approach for this domain is a layered pipeline: ingest NBA data from free APIs (nba_api, balldontlie), engineer temporal features with strict anti-leakage discipline, train gradient boosting models (XGBoost/LightGBM) for game and player predictions, and surface results through a Streamlit dashboard and natural language CLI. Academic research consistently validates XGBoost as the gold standard for NBA prediction on structured data, outperforming neural nets. The entire stack stays in Python, uses SQLite for storage, and runs on a single machine.

The recommended approach is bottom-up construction: data pipeline and database first, then feature engineering, then ML models, then interfaces (dashboard + Hermes Agent), and finally the computer vision pipeline as an optional enrichment layer. This ordering is dictated by hard dependencies -- models need features, features need data, interfaces need predictions. The CV pipeline is deliberately last because it carries the highest risk (footage sourcing is legally and practically uncertain) and the core system must deliver value without it.

The primary risks are: (1) temporal data leakage silently inflating model accuracy during development, (2) nba_api instability as a single point of failure for data ingestion, (3) the CV pipeline consuming disproportionate effort with uncertain payoff, and (4) model overfitting to historical seasons that no longer reflect current NBA play. All four are well-understood and preventable with the patterns documented in the architecture research -- the key is building the safeguards into the pipeline from day one, not bolting them on later.

## Key Findings

### Recommended Stack

The stack is entirely Python-based, avoiding frontend JavaScript complexity. Data comes from two free sources (nba_api as primary, balldontlie as fallback/supplement). ML uses XGBoost (primary) and LightGBM (ensemble), both validated by published NBA prediction research. Computer vision uses YOLO11 + ByteTrack + supervision from Roboflow. The presentation layer is Streamlit for the dashboard and Hermes Agent for NL queries/orchestration. See [STACK.md](STACK.md) for full details.

**Core technologies:**
- **nba_api + balldontlie**: NBA data ingestion -- free, comprehensive, with balldontlie as fallback and MCP server for agent integration
- **XGBoost 3.2 + LightGBM 4.6**: Prediction models -- gold standard for tabular sports data per peer-reviewed research
- **SHAP 0.51**: Model interpretability -- explains why predictions are made, surfaces key features
- **YOLO11 + ByteTrack + supervision**: CV pipeline -- player detection, multi-object tracking, zone analytics
- **SQLite + SQLAlchemy**: Local database -- zero-config, single-file, handles 3+ seasons of NBA data easily
- **Streamlit 1.55**: Dashboard -- fastest path from Python data to interactive web app, no frontend code
- **Hermes Agent**: AI orchestration -- NL queries, tool chaining, persistent memory, daily briefings, MCP support

**Critical version requirement:** Python 3.11+ (required by SHAP >= 0.50).

### Expected Features

**Must have (table stakes):**
- Daily automated stats sync from nba_api
- Game winner/spread and over/under predictions via ML
- Player and team dashboards with stats/trends
- Injury report integration affecting predictions
- Prediction tracking with accuracy metrics
- Today's games slate with matchup info

**Should have (differentiators):**
- Player prop predictions (individual stat lines)
- Hermes Agent natural language queries
- Automated daily briefings with picks
- Agent learning loop (improves from prediction outcomes)
- Matchup-specific analysis (Player X vs Team Y)
- Confidence calibration (model communicates uncertainty)

**Defer to v2+:**
- Computer vision footage analysis (highest complexity, legal uncertainty)
- Live in-game predictions (requires real-time feeds)
- Betting odds integration (focus on model accuracy first)
- Rolling model retraining (needs prediction history to learn from)
- Multi-factor synthesis combining stats + CV + context

See [FEATURES.md](FEATURES.md) for full feature dependency graph.

### Architecture Approach

The system follows a layered pipeline architecture with six subsystems: Data Ingestion, Feature Engineering, ML Models, CV Pipeline, Hermes Agent (orchestrator), and Presentation Layer. Each subsystem communicates through SQLite -- no direct coupling between components. The pipeline-as-DAG pattern means each step reads from and writes to the database independently, enabling re-running individual steps and debugging in isolation. Hermes Agent sits on top as an orchestrator, calling tools exposed via MCP but never touching the database directly. See [ARCHITECTURE.md](ARCHITECTURE.md) for component diagrams and data flow.

**Major components:**
1. **Data Ingestion Pipeline** -- ETL from nba_api with rate limiting, caching, and adapter pattern for source flexibility
2. **Feature Engineering Engine** -- Transforms raw stats into ML features with strict temporal anti-leakage via `.shift(1)`
3. **ML Model Layer** -- Multi-head XGBoost/LightGBM models for different prediction types with TimeSeriesSplit validation
4. **Hermes Agent** -- NL interface, tool orchestration, memory/learning loop, daily briefing generation
5. **Presentation Layer** -- Streamlit dashboard + Hermes CLI/TUI for consuming predictions
6. **CV Pipeline** -- Optional enrichment layer for player tracking from game footage (deferred)

### Critical Pitfalls

1. **Temporal data leakage** -- The single most common bug in NBA prediction. Rolling features must use `.shift(1)`. Never shuffle train/test splits. If accuracy exceeds 70%, suspect leakage. Build a `FeatureValidator` from day one.
2. **nba_api instability** -- Unofficial API with Cloudflare rate limiting, endpoint deprecations, and IP bans on cloud servers. Use adapter pattern with caching DB and balldontlie fallback. Monitor sync freshness.
3. **CV pipeline as a time sink** -- Footage sourcing is legally uncertain, broadcast angles produce inferior tracking vs NBA's own systems, and the feature is not needed for core predictions. Defer entirely until statistical models are proven.
4. **Overfitting to historical seasons** -- NBA evolves (pace, rules, style). Train on last 2-3 seasons max with exponential decay weighting. Monitor accuracy drift monthly.
5. **Evaluating accuracy instead of calibration** -- A well-calibrated 65% model is more useful than an uncalibrated 68% model. Use Brier score and calibration plots, not just accuracy.

See [PITFALLS.md](PITFALLS.md) for full list with detection and prevention strategies.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Data Foundation
**Rationale:** Everything depends on having clean, current data in a local database. This phase has zero dependencies and unblocks all subsequent work.
**Delivers:** SQLite schema, data ingestion pipeline from nba_api, schedule/player/team/boxscore sync, injury report integration, data freshness monitoring.
**Addresses:** Daily stats sync, historical data ingestion, injury reports (table stakes features).
**Avoids:** Pitfall 2 (nba_api as SPOF) by building adapter pattern and caching from day one.
**Stack:** nba_api, balldontlie, SQLite, SQLAlchemy, Python 3.11+

### Phase 2: Feature Engineering
**Rationale:** Models consume features, not raw stats. This phase transforms ingested data into ML-ready feature rows with strict temporal discipline.
**Delivers:** Feature registry, rolling averages, lag features, advanced stats (TS%, net rating, pace), matchup features, situational features (home/away, rest, travel).
**Addresses:** Feature computation infrastructure needed by all prediction models.
**Avoids:** Pitfall 1 (temporal leakage) by enforcing `.shift(1)` and building FeatureValidator. Pitfall 5 (multicollinearity) by computing correlation matrix and using ratio features.

### Phase 3: Prediction Models
**Rationale:** The core value proposition. With features ready, train and validate ML models for game and player predictions.
**Delivers:** XGBoost game winner/spread model, XGBoost over/under model, player points model, prediction logging with outcome backfill, accuracy tracking, calibration analysis.
**Addresses:** Game predictions, player props, prediction tracking, accuracy metrics (table stakes + differentiators).
**Avoids:** Pitfall 4 (overfitting) with rolling training windows and drift detection. Pitfall 7 (accuracy vs calibration) by using Brier score from the start. Pitfall 8 (outcome matching) by building OutcomeResolver with explicit edge case rules.
**Stack:** XGBoost, LightGBM, scikit-learn, SHAP, Optuna

### Phase 4: Dashboard & Scheduling
**Rationale:** Models are proven -- now surface predictions through a visual interface and automate the daily pipeline.
**Delivers:** Streamlit dashboard (today's games, player cards, prediction history, accuracy charts), scheduled data sync and prediction generation, CLI entry points.
**Addresses:** Player dashboard, team dashboard, today's slate, basic accuracy metrics (table stakes).
**Avoids:** Pitfall 9 (building UI before models work) by coming after validated models.
**Stack:** Streamlit, Plotly, APScheduler

### Phase 5: Hermes Agent Integration
**Rationale:** All tools must exist before the orchestrator can call them. Hermes wraps the working system with NL queries and automation.
**Delivers:** MCP tool registration for all system capabilities, natural language query support, daily briefing generation, memory/learning loop for prediction tracking.
**Addresses:** Hermes Agent NL queries, daily briefings, agent learning loop, CLI TUI (differentiators).
**Avoids:** Pitfall 6 (memory bloat) by designing TTL and structured storage strategy upfront. Pitfall 12 (agent as oracle) by always surfacing probability ranges.
**Stack:** Hermes Agent, FastMCP

### Phase 6: Computer Vision Pipeline
**Rationale:** Highest risk, longest research tail, optional enrichment. Only pursue after core system delivers value independently. May be deferred indefinitely if footage sourcing remains unresolved.
**Delivers:** YOLO11 player detection, ByteTrack multi-object tracking, court homography, movement metric extraction, CV feature integration into ML models.
**Addresses:** CV footage analysis, multi-factor synthesis (differentiators, deferred).
**Avoids:** Pitfall 3 (CV as time sink) by isolating it as a late, optional phase that cannot block core functionality.
**Stack:** YOLO11, supervision, ByteTrack, OpenCV

### Phase Ordering Rationale

- **Bottom-up by dependency chain:** Data -> Features -> Models -> Interfaces -> Agent -> CV. Each layer consumes the output of the layer below it.
- **Risk-ordered:** Low-risk, well-documented work (data pipeline, feature engineering) comes first. High-risk, uncertain work (CV pipeline) comes last.
- **Value delivery:** The system becomes useful after Phase 3 (predictions exist). Phase 4 makes them visible. Phase 5 makes them conversational. Phase 6 is enrichment.
- **Pitfall avoidance:** The ordering ensures anti-leakage infrastructure exists before any model training, and models are validated before any UI work begins.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Feature Engineering):** Requires research into which specific features have the highest predictive value for NBA games. Academic papers provide guidance but optimal feature sets are domain-specific.
- **Phase 5 (Hermes Agent):** Hermes Agent is a young project (launched Feb 2026). MCP tool registration patterns, memory management at scale, and multi-backend LLM compatibility need hands-on validation.
- **Phase 6 (CV Pipeline):** Footage sourcing strategy, fine-tuning YOLO11 on basketball data, court homography approaches all need research. Highest uncertainty of any phase.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Data Foundation):** Well-documented. nba_api has extensive endpoint docs, SQLAlchemy/SQLite are mature, ETL patterns are standard.
- **Phase 3 (Prediction Models):** XGBoost for NBA prediction has multiple peer-reviewed papers with reproducible results. Feature importance via SHAP is well-documented.
- **Phase 4 (Dashboard):** Streamlit is mature with extensive docs and examples. Standard dashboard patterns apply.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All technologies are mature, well-documented, and validated by published research. Version pinning is clear. |
| Features | HIGH | Table stakes and differentiators are well-defined with clear dependency ordering. Anti-features are sensible. |
| Architecture | HIGH | Layered pipeline is the standard pattern for sports prediction systems. Multiple open-source references validate the approach. |
| Pitfalls | HIGH | Temporal leakage and nba_api instability are extensively documented in community issues and academic papers. Prevention strategies are concrete. |

**Overall confidence:** HIGH

### Gaps to Address

- **nba_api endpoint stability:** The V2-to-V3 boxscore migration shows endpoints can deprecate. Need to verify current endpoint availability during Phase 1 implementation and build fallback paths.
- **Hermes Agent maturity:** Released Feb 2026. The 40+ tool system, skill persistence, and memory management have not been stress-tested at the scale of daily NBA analysis. Plan for workarounds if features don't perform as documented.
- **Footage sourcing for CV:** No resolution on legal/practical source of game footage. Phase 6 may need to pivot to using NBA's own tracking data (available via nba_api endpoints) instead of processing raw video.
- **Prediction accuracy ceiling:** Academic literature suggests 65-68% accuracy ceiling for NBA game prediction with public data. User expectations should be calibrated accordingly -- this is a hard problem even for professional sports analytics teams.
- **balldontlie MCP server:** Listed as having an official MCP server at mcp.balldontlie.io for direct Hermes integration, but this is relatively new and needs validation during Phase 5.

## Sources

### Primary (HIGH confidence)
- [XGBoost + SHAP for NBA prediction (PLOS ONE)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11265715/) -- model architecture, feature engineering validation
- [nba_api on GitHub](https://github.com/swar/nba_api) -- data source documentation, known issues
- [Ultralytics YOLO11 docs](https://docs.ultralytics.com/models/yolo11/) -- CV model architecture
- [Hermes Agent on GitHub](https://github.com/NousResearch/hermes-agent) -- agent capabilities, MCP support
- [NBA_AI reference system](https://github.com/NBA-Betting/NBA_AI) -- architecture patterns, SQLite schema
- [Stacked Ensemble for NBA Prediction (Nature Scientific Reports 2025)](https://www.nature.com/articles/s41598-025-13657-1)

### Secondary (MEDIUM confidence)
- [ML for Sports Betting: Accuracy vs Calibration (ScienceDirect)](https://www.sciencedirect.com/science/article/pii/S266682702400015X) -- calibration methodology
- [balldontlie API docs](https://docs.balldontlie.io/) -- supplemental data source
- [supervision (Roboflow)](https://github.com/roboflow/supervision) -- CV toolkit
- [Streamlit vs Dash comparison 2025](https://www.squadbase.dev/en/blog/streamlit-vs-dash-in-2025-comparing-data-app-frameworks)
- [HoopsRadar - Stanford CS231n](https://cs231n.stanford.edu/2025/papers/text_file_840593527-LaTeXAuthor_Guidelines_for_CVPR_Proceedings%20(3).pdf)

### Tertiary (LOW confidence)
- [balldontlie MCP server](https://github.com/balldontlie-api/mcp) -- needs validation
- [Hermes Agent announcement (MarkTechPost)](https://www.marktechpost.com/2026/02/26/nous-research-releases-hermes-agent-to-fix-ai-forgetfulness-with-multi-level-memory-and-dedicated-remote-terminal-access-support/) -- marketing material, verify against actual docs

---
*Research completed: 2026-03-07*
*Ready for roadmap: yes*
