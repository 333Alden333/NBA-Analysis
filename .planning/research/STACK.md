# Technology Stack

**Project:** HermesAnalysis - NBA AI Analysis & Prediction Platform
**Researched:** 2026-03-07

## Recommended Stack

### Data Sources

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| nba_api | 1.11.3 | Primary NBA stats (player, team, game, play-by-play, shot charts) | Free, comprehensive, actively maintained (Feb 2026 release), pulls from NBA.com internal APIs. BoxScoreSummaryV3 is current. Cache aggressively to handle rate limits. | HIGH |
| balldontlie API | v2 (free tier) | Supplemental real-time stats, lineup data, play-by-play (2025+ seasons) | Free tier with API key. Covers gaps nba_api may have -- real-time scores (10min delay on free), lineup data only available from 2025 season. Has an official MCP server at mcp.balldontlie.io for direct Hermes Agent integration. | HIGH |

**Do NOT use:** sportsdata.io ($25/mo) -- unnecessary cost when nba_api + balldontlie cover the same ground for free. Only revisit if specific data gaps emerge in v2.

### ML / Prediction

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| XGBoost | 3.2.0 | Primary prediction model (game outcomes, player props, spreads, totals) | Gold standard for NBA prediction per published research. Handles structured tabular data with nonlinear relationships. Second-order Taylor expansion for accuracy. Regularization prevents overfitting. Best performer in 10-fold cross-validation across multiple NBA studies. | HIGH |
| LightGBM | 4.6.0 | Secondary/ensemble model | Close second to XGBoost in NBA prediction benchmarks. Faster training via histogram-based learning. Use for ensemble voting or when training speed matters on larger feature sets. | HIGH |
| scikit-learn | >=1.5 | Feature engineering, preprocessing, model evaluation, cross-validation | Standard ML toolkit. Provides pipelines, scalers, encoders, train/test split, GridSearchCV, cross_val_score. Foundation for everything else. | HIGH |
| SHAP | 0.51.0 | Model interpretability -- which features drive predictions | Game-theoretic feature importance. Essential for understanding WHY the model predicts a win/loss. Surfaces key indicators (FG%, defensive rebounds, turnovers, VORP, PER). Requires Python >=3.11. | HIGH |
| Optuna | >=3.6 | Bayesian hyperparameter optimization | Better than GridSearchCV for XGBoost/LightGBM tuning. Pruning support for early stopping of bad trials. More efficient than manual grid search. | MEDIUM |

**Do NOT use:** Deep neural networks for tabular prediction. XGBoost/LightGBM consistently outperform neural nets on structured sports data. Neural nets add complexity without accuracy gains here. Save deep learning for the CV pipeline.

**Do NOT use:** CatBoost as primary. While CatBoost showed strong results for MVP prediction specifically, XGBoost is the better general-purpose choice for game/player/props prediction. CatBoost can be added to an ensemble later if needed.

### Feature Engineering Strategy

| Technique | Purpose |
|-----------|---------|
| Lag features | Player performance from 1, 2, 3 games/seasons ago |
| Rolling averages | Average over last 5, 10, 20 games |
| Trend features | Performance delta between periods |
| Matchup features | Head-to-head historical stats, pace adjustments |
| Rest/travel | Days of rest, back-to-back detection, travel distance |

### Computer Vision

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Ultralytics (YOLO11) | 8.4.21 (pip package) | Player detection, ball detection, court detection | YOLO11 achieves higher mAP with 22% fewer parameters than YOLOv8. Supports detection, segmentation, pose estimation, and tracking natively. C3k2 blocks + C2PSA spatial attention. Actively maintained by Ultralytics. | HIGH |
| supervision | 0.26.1 | Detection handling, tracking visualization, zone analytics, annotation | Roboflow's CV toolkit -- model-agnostic, handles ByteTrack integration, video processing, zone counting, annotators. Decouples detection from visualization. MIT licensed. | HIGH |
| ByteTrack | (via ultralytics) | Multi-object tracking across frames | Best tracker for sports -- uses low-confidence detections others discard, maintaining IDs through occlusion. Built into ultralytics `model.track()`. Also available via supervision. | HIGH |
| OpenCV | >=4.9 | Video I/O, frame processing, image manipulation | Standard for video read/write, frame extraction, color conversion, homography transforms. Required by both ultralytics and supervision. | HIGH |

**Architecture note:** YOLO11 is the recommendation over YOLO26. While YOLO26 (Jan 2026) is newer with NMS-free inference, it is optimized for edge/embedded deployment. YOLO11 has more community examples, basketball-specific fine-tuning guides, and proven stability. Revisit YOLO26 when more basketball-specific benchmarks exist.

**Do NOT use:** Custom-trained BGS-YOLO or IBN-YOLOv5s. These are research models from papers -- not production-ready packages. Use standard YOLO11 with fine-tuning on basketball datasets from Roboflow Universe instead.

### Video/Footage Sources

| Source | Viability | Legal Status | Notes |
|--------|-----------|-------------|-------|
| Self-recorded footage | Best | Clean | Use personal recordings of games, pickup games for initial training |
| Roboflow Universe datasets | Good | Clean (CC licensed) | Pre-annotated basketball player detection datasets exist. Search "basketball players" on universe.roboflow.com |
| YouTube highlights | Usable for research | Gray area | NBA tolerates highlights as marketing. Do NOT redistribute. Use for personal model training only. yt-dlp for download. |
| NBA League Pass | Full games | Copyrighted | All footage is NBA property. Personal research use only. Do not redistribute or commercialize CV results from this footage. |

**Recommendation:** Start with Roboflow Universe annotated datasets for model fine-tuning. Use self-recorded or YouTube highlights for inference testing. League Pass for full-game analysis once pipeline is proven.

### Database

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| SQLite | 3.x (built-in) | Local stats database, prediction logs, model metadata | Zero config, single file, built into Python. Perfect for single-user local-first analytics. Read-heavy workload (daily sync, then queries). No server to manage. Portable -- entire DB is one file. | HIGH |
| SQLAlchemy | >=2.0 | ORM / query builder | Abstracts SQLite access. If you ever need to migrate to PostgreSQL, change one connection string. Provides schema management and migrations via Alembic. | HIGH |

**Do NOT use:** PostgreSQL for v1. Overkill for a local single-user platform. SQLite handles the data volume (decades of NBA stats = ~2-5GB) easily. PostgreSQL adds server management overhead for zero benefit at this scale. Migrate later only if multi-user dashboard is needed.

**Do NOT use:** MongoDB or other NoSQL. NBA stats are inherently tabular/relational. Player -> Team -> Game -> Stats is a textbook relational schema.

### Web Dashboard

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Streamlit | 1.55.0 | Web dashboard framework | Fastest path from Python data to interactive web app. Native Plotly support. Perfect for single-user analytics dashboards. v1.55 adds dynamic containers, widget binding, and CSS color support. No frontend code needed. | HIGH |
| Plotly | >=5.22 | Interactive charts (shot charts, player comparisons, prediction confidence) | Best-in-class interactive charting for Python. Native Streamlit integration via `st.plotly_chart`. Supports scatter, heatmaps, radar charts, court visualizations. | HIGH |
| streamlit-autorefresh | latest | Auto-refresh for daily briefings | Enables periodic page refresh for live dashboard updates without manual reload. | MEDIUM |

**Do NOT use:** Plotly Dash for v1. Dash requires callback architecture and more boilerplate. Streamlit gets you from notebook to dashboard in hours, not days. Migrate to Dash only if you need multi-user concurrent access or enterprise deployment.

**Do NOT use:** React/Next.js frontend. The project owner has Python ML expertise, not frontend dev. Streamlit keeps the entire stack in Python. A JS frontend adds a build step, API layer, and maintenance burden for minimal UX gain.

### AI Agent / Orchestration

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Hermes Agent | latest (via install script) | Orchestration, NL queries, tool chaining, memory, learning loop, daily briefings, CLI TUI | MIT licensed. 40+ built-in tools. Persistent memory across sessions. Skills system for recurring tasks. MCP support for connecting to custom tools and balldontlie API. Cron scheduling for daily briefings. Multi-backend (OpenRouter, OpenAI, local models). Self-improving -- learns from prediction hits/misses. | HIGH |
| FastMCP (Python) | latest | Custom MCP server for exposing NBA tools to Hermes | Build MCP tools that Hermes auto-discovers: query stats, run predictions, fetch game schedules, trigger CV analysis. Python-native, simple decorator API. Configured in ~/.hermes/config.yaml. | MEDIUM |

**Integration pattern:** Build Python MCP servers that expose NBA-specific tools (get_player_stats, predict_game, analyze_footage, get_daily_slate). Hermes Agent connects to these via stdio transport, auto-discovers tools, and can chain them in natural language queries like "How will Luka do tonight?" -> [get_player_stats -> get_matchup_history -> run_prediction -> format_response].

### Infrastructure / DevOps

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Python | 3.11+ | Runtime | Required by SHAP >=0.50 (Python >=3.11). Compatible with all other packages. 3.11 is the safe floor. | HIGH |
| uv | latest | Package manager | Fast, reliable Python package management. Handles venv creation and dependency resolution. Used by Hermes Agent itself. | HIGH |
| APScheduler | >=3.10 | Scheduled data sync, daily briefing generation | Lightweight Python scheduler. Run nba_api sync at 4 AM, generate briefings at 8 AM. Alternative: Hermes Agent's built-in cron. | MEDIUM |
| Git + GitHub | - | Version control | Repository on 333Alden333 account | HIGH |
| pytest | >=8.0 | Testing | Standard Python testing. Test data pipelines, model accuracy thresholds, MCP tool responses. | HIGH |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Data source | nba_api | basketball-reference scraping | nba_api is structured API, scraping is fragile and against ToS |
| Data source | balldontlie (free) | sportsdata.io ($25/mo) | Cost. Free tier sufficient for supplemental data |
| ML primary | XGBoost | PyTorch tabular | XGBoost outperforms neural nets on structured sports data |
| ML secondary | LightGBM | CatBoost | LightGBM has broader NBA research validation |
| CV model | YOLO11 | YOLO26 | YOLO26 is too new, optimized for edge. YOLO11 has basketball community examples |
| CV model | YOLO11 | Detectron2 | Detectron2 is heavier, slower inference, less active development |
| Tracking | ByteTrack | DeepSORT | ByteTrack uses low-confidence detections, better for occluded players |
| Database | SQLite | PostgreSQL | Overkill for single-user local app |
| Dashboard | Streamlit | Plotly Dash | Dash requires more boilerplate, callback architecture |
| Dashboard | Streamlit | Gradio | Gradio is ML-demo focused, not analytics dashboard |
| Agent | Hermes Agent | LangChain | Hermes has built-in memory, learning loop, skills. LangChain is a framework, not an agent |
| Package mgr | uv | pip/poetry | uv is faster, used by Hermes Agent itself |

## Installation

```bash
# Create project environment
uv venv .venv --python 3.11
source .venv/bin/activate

# Core data & ML
uv pip install nba_api==1.11.3 xgboost==3.2.0 lightgbm==4.6.0 scikit-learn shap==0.51.0 optuna pandas numpy

# Computer vision
uv pip install ultralytics==8.4.21 supervision==0.26.1 opencv-python

# Database
uv pip install sqlalchemy alembic

# Dashboard
uv pip install streamlit plotly streamlit-autorefresh

# Agent tools (MCP server)
uv pip install mcp fastmcp

# Scheduling & utilities
uv pip install apscheduler requests python-dotenv

# Dev dependencies
uv pip install pytest pytest-cov black ruff

# Hermes Agent (separate install)
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

## Version Pinning Strategy

Pin major.minor for stability, allow patch updates:

```
nba_api>=1.11,<1.12
xgboost>=3.2,<3.3
lightgbm>=4.6,<4.7
shap>=0.51,<0.52
ultralytics>=8.4,<8.5
supervision>=0.26,<0.27
streamlit>=1.55,<1.56
```

## Sources

- [nba_api on PyPI](https://pypi.org/project/nba_api/) - v1.11.3, Feb 2026
- [nba_api on GitHub](https://github.com/swar/nba_api) - BoxScoreSummaryV3 migration
- [balldontlie API docs](https://docs.balldontlie.io/) - Free tier, MCP server
- [balldontlie MCP server](https://github.com/balldontlie-api/mcp)
- [XGBoost + SHAP for NBA prediction (PLOS ONE)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11265715/) - Research validation
- [XGBoost on PyPI](https://pypi.org/project/xgboost/) - v3.2.0, Feb 2026
- [LightGBM on PyPI](https://pypi.org/project/lightgbm/) - v4.6.0
- [SHAP on PyPI](https://pypi.org/project/shap/) - v0.51.0, Mar 2026
- [Ultralytics YOLO11 docs](https://docs.ultralytics.com/models/yolo11/) - Architecture details
- [Ultralytics on PyPI](https://pypi.org/project/ultralytics/) - v8.4.21
- [supervision on GitHub](https://github.com/roboflow/supervision) - v0.26.1
- [ByteTrack for tracking](https://github.com/FoundationVision/ByteTrack)
- [Roboflow basketball datasets](https://universe.roboflow.com/yolo-onwlc/basketball-players-fy4c2-qllci)
- [Streamlit on PyPI](https://pypi.org/project/streamlit/) - v1.55.0, Mar 2026
- [Hermes Agent on GitHub](https://github.com/NousResearch/hermes-agent)
- [Hermes Agent docs](https://hermes-agent.nousresearch.com/docs/)
- [HoopsRadar - Stanford CS231n](https://cs231n.stanford.edu/2025/papers/text_file_840593527-LaTeXAuthor_Guidelines_for_CVPR_Proceedings%20(3).pdf)
- [NBA + AWS partnership 2025-26](https://www.tvtechnology.com/news/nba-aws-partner-to-take-game-insights-to-the-next-level)
- [Streamlit vs Dash comparison 2025](https://www.squadbase.dev/en/blog/streamlit-vs-dash-in-2025-comparing-data-app-frameworks)
