# Domain Pitfalls

**Domain:** NBA AI Analysis and Prediction Platform
**Researched:** 2026-03-07

## Critical Pitfalls

Mistakes that cause rewrites, wasted months, or fundamentally broken predictions.

---

### Pitfall 1: Feature Leakage Through Temporal Contamination

**What goes wrong:** The model uses data that would not be available at prediction time. Example: using a player's season average (which includes games after the target game) to predict that game's outcome. Or using the final box score stats of a game to predict who won that game. This inflates accuracy to 85-95% during development, then the model performs at ~55% in production.

**Why it happens:** Standard train/test splits shuffle data randomly. In sports, this means future games leak into training data. Pandas `.sample(frac=0.2)` for test sets is the most common culprit. Also, rolling averages computed on the entire dataset (not just prior games) introduce subtle leakage.

**Consequences:** Model appears excellent in evaluation, fails completely in production. Destroys trust in the entire system. Requires full pipeline rebuild once discovered.

**Prevention:**
- Always split data chronologically: train on seasons/dates before test dates
- Never use `sklearn.model_selection.train_test_split` with `shuffle=True` for game data
- Compute rolling features using only data available before the prediction timestamp
- Create a `FeatureValidator` that checks every feature's timestamp against the target game's timestamp
- Unit test: for any game in the test set, assert no training features reference data from on or after that game's date

**Detection:** If model accuracy exceeds 70% on game winner prediction, be suspicious. Academic literature consistently shows 65-68% as the ceiling for NBA game prediction with publicly available data. Anything above 72% almost certainly has leakage.

**Phase relevance:** Must be enforced from the very first ML model. Build temporal validation into the data pipeline before any model training begins.

---

### Pitfall 2: nba_api as a Single Point of Failure

**What goes wrong:** The entire data pipeline depends on `nba_api`, which is an unofficial wrapper around NBA.com's internal endpoints. These endpoints use Cloudflare rate limiting, browser fingerprinting, and can change without notice. Multiple breakage events occurred in late 2025 (November-December 2025, January 2026). The `BoxScoreSummaryV2` endpoint was deprecated after April 10, 2025 in favor of V3. Cloud-deployed instances (Heroku, DigitalOcean) get blocked more aggressively than residential IPs.

**Why it happens:** `nba_api` is free and comprehensive, making it the obvious choice. But it scrapes NBA.com's undocumented internal API -- NBA owes no stability guarantees. Rate limits are undocumented and enforced via IP bans. The library has ~70 open issues on GitHub at any given time.

**Consequences:** Daily data sync breaks silently. Models train on stale data. Predictions degrade without any error signal. Deploying to cloud makes the problem worse.

**Prevention:**
- Cache aggressively into a local SQLite/PostgreSQL database -- treat nba_api as a sync source, not a live query layer
- Build the data layer with an adapter pattern: `NBADataSource` interface with `NBAApiSource`, `BallDontLieSource`, `CachedSource` implementations
- Add request delays (minimum 2 seconds between calls, 5+ for bulk operations)
- Set proper headers: `User-Agent`, `Referer: https://www.nba.com/`
- Monitor sync failures with alerts -- don't assume nightly sync succeeded
- Pin `nba_api` version and test before upgrading (breaking changes are common)
- Have `balldontlie.io` (free tier) as a fallback for critical endpoints

**Detection:** Sync logs showing 429 errors, timeouts, or empty responses. Data freshness monitoring: if the latest game in DB is >24 hours behind the actual schedule, something is broken.

**Phase relevance:** Data pipeline phase (Phase 1). Build the caching/adapter pattern from day one. Do not build ML models directly on live nba_api calls.

---

### Pitfall 3: Game Footage CV Pipeline is a Legal and Technical Quagmire

**What goes wrong:** The project plans CV analysis as a core v1 feature, but NBA game footage is copyrighted by NBA Properties, Inc. and licensed broadcasters. There is no legal free source of full game footage. YouTube highlights get DMCA'd. League Pass terms prohibit automated downloading or analysis. Even if footage is obtained, single-camera broadcast angles make player tracking far harder than the NBA's own 50+ camera SportVU/Hawk-Eye system.

**Why it happens:** CV demos using controlled datasets (COCO, custom basketball courts) look impressive. The gap between "detect a basketball in a controlled video" and "track all 10 players + ball through broadcast footage with camera cuts, replays, and overlays" is enormous. Teams underestimate this gap and the legal exposure.

**Consequences:** Months spent on a CV pipeline that either (a) has no legal footage to process, (b) produces low-quality tracking from broadcast angles, or (c) both. This is the highest-risk feature in the entire project and could consume disproportionate engineering time with minimal prediction value.

**Prevention:**
- Do NOT make CV a v1 blocker. Defer to v2 or later, after statistical models are proven
- If pursuing CV, start with the NBA's own tracking data available through `nba_api` endpoints (`PlayerDashPtShots`, `ShotChartDetail`, tracking stats) -- this is what the CV pipeline would produce anyway, and it's already computed
- For custom CV work, use only: (a) your own recorded footage of amateur games, (b) explicitly licensed datasets, or (c) synthetic data from game simulators like Unity
- If using YouTube clips for research/prototyping, keep it offline and never deploy publicly
- Consider Roboflow's pre-trained basketball models for prototyping, but don't build production systems around scraped footage

**Detection:** If the team is spending more time sourcing footage than building models, the CV feature is off track. If legal review hasn't happened before writing the first line of CV code, that's a red flag.

**Phase relevance:** Should be deferred to a late phase (Phase 4+). Statistical prediction models should be built and validated first. CV should only be pursued once the core product is delivering value without it.

---

### Pitfall 4: Overfitting to Historical Seasons

**What goes wrong:** A model trained on 2015-2024 data performs well on held-out 2024 data but poorly on live 2025-26 games. The NBA evolves: three-point revolution, pace changes, rule modifications (challenge system, in-play tournament), roster turnover, and coaching changes make historical patterns decay. A model memorizes "teams that shoot 38%+ from three win 62% of the time" but the league-wide average shifts.

**Why it happens:** More data feels better. Ten seasons of data means more rows. But the NBA of 2016 is a different sport than 2026 in terms of pace, style, and rules. Feature distributions shift (non-stationarity). Models trained on large historical windows learn dead patterns.

**Consequences:** Model accuracy degrades through the season. Predictions get worse exactly when you want them to get better (playoffs, when stakes are highest and meta shifts most).

**Prevention:**
- Weight recent seasons more heavily (exponential decay weighting)
- Use rolling training windows: train on last 2-3 seasons max, not all available history
- Implement drift detection: monitor feature distributions monthly, retrain when distributions shift
- Track prediction accuracy over time (calibration plots by month) -- if accuracy drops, the model is stale
- Use regularization (L1/L2) and limit tree depth in gradient boosting models to prevent memorization
- Ensemble models with different temporal windows to capture both long-term and short-term patterns

**Detection:** Plot accuracy by week. If accuracy declines monotonically from season start, the model is overfitting to historical patterns. Compare model accuracy to a simple "home team wins 58% of the time" baseline -- if your model barely beats this, it's not learning useful patterns.

**Phase relevance:** ML model training phase. Build drift detection and temporal evaluation into the model evaluation pipeline from the start.

---

## Moderate Pitfalls

---

### Pitfall 5: Multicollinearity in Basketball Statistics

**What goes wrong:** Basketball stats are highly correlated. Points correlate with field goal attempts. Assists correlate with teammate scoring. Rebounds correlate with missed shots. Feeding correlated features into a model inflates feature importance estimates, makes the model unstable (small changes in data cause large coefficient swings), and makes SHAP/feature importance analysis misleading.

**Prevention:**
- Compute correlation matrix before model training. Drop features with >0.85 correlation
- Use engineered ratio features instead of raw counts: TS% (true shooting), AST%, USG%, net rating
- Use PCA or domain-driven feature reduction for highly correlated groups
- Prefer "differential" features (Team A stat minus Team B stat) over absolute values -- this also reduces feature count by half

**Phase relevance:** Feature engineering phase. Do this before training any model.

---

### Pitfall 6: Hermes Agent Memory Bloat and Skill Quality Degradation

**What goes wrong:** Hermes Agent's persistent memory grows indefinitely. After months of daily briefings and queries, the memory fills with outdated predictions, stale player assessments, and contradictory skills. The agent loads irrelevant skills because keyword matching pulls in old context. Response quality degrades as the agent's "knowledge" becomes a mix of current and outdated information.

**Why it happens:** Hermes Agent automatically writes skill documents when it solves problems. There is no built-in mechanism for pruning outdated skills, resolving contradictions between old and new skills, or weighting recency. The skill library (44 GitHub stars at launch) is young and has not been stress-tested at scale.

**Prevention:**
- Implement a skill/memory TTL: auto-archive predictions and player assessments older than 30 days
- Tag all memory entries with timestamps and season context
- Build a nightly cleanup job that removes or archives stale entries
- Use structured memory (database) for predictions and outcomes, not free-text memory
- Test Hermes Agent with multiple LLM backends early -- the 40+ tool system may not work well with all models
- Keep the agent's role narrow: orchestration and NL queries, not as a data store

**Detection:** If the agent starts referencing traded players as still on their old team, or citing predictions from months ago as current, memory quality has degraded.

**Phase relevance:** Hermes Agent integration phase. Design the memory management strategy before deploying the agent for daily use.

---

### Pitfall 7: Evaluating Models on Accuracy Instead of Calibration

**What goes wrong:** The model predicts "Team A wins with 75% probability" but Team A actually wins only 55% of the time when the model says 75%. The model is poorly calibrated. Accuracy (did the predicted winner win?) looks fine, but the probability estimates are meaningless. This matters enormously for props and totals predictions where confidence-weighted decisions are critical.

**Why it happens:** Tutorials and academic papers report accuracy as the primary metric. Calibration requires reliability diagrams and Brier scores, which are less intuitive. XGBoost and neural nets are particularly prone to overconfident probability estimates out of the box.

**Prevention:**
- Use Brier score and log-loss as primary metrics, not accuracy
- Generate calibration plots (reliability diagrams) for every model
- Apply Platt scaling or isotonic regression for probability calibration
- Track Expected Calibration Error (ECE) across probability buckets
- For game winner prediction, a well-calibrated model at 65% accuracy is more useful than an uncalibrated model at 68% accuracy

**Detection:** Calibration plot showing predicted probabilities don't match observed frequencies. If the model says 80% confidence on 100 games but only wins 60 of them, calibration is broken.

**Phase relevance:** Model evaluation phase. Add calibration metrics alongside accuracy from the first model evaluation.

---

### Pitfall 8: Prediction Tracking Without Proper Outcome Matching

**What goes wrong:** The project plans to "log predictions vs actual outcomes for model improvement." But matching predictions to outcomes is harder than it sounds. Games get postponed. Players get scratched after predictions are made. Props lines change. If the prediction was "Luka scores 30+" but Luka sits out, is that a miss? If the game goes to overtime, do totals predictions count differently?

**Prevention:**
- Define explicit outcome matching rules before logging any predictions
- Handle edge cases: postponements, player scratches (DNP), overtime, ejections
- Store prediction context (who was expected to play, injury report at prediction time)
- Separate prediction accuracy from model quality -- a correct model can make "wrong" predictions if inputs change after prediction time
- Build an `OutcomeResolver` class that handles all edge cases consistently

**Phase relevance:** Prediction tracking phase. Design the outcome matching system before the first prediction is logged.

---

### Pitfall 9: Building the Web Dashboard Before the Models Work

**What goes wrong:** Weeks spent on chart components, game cards, and responsive layouts before the prediction models produce meaningful output. Then the models need different data formats, different update frequencies, or different visualization types than what was built. Dashboard gets rewritten.

**Prevention:**
- Build models and validate predictions first (CLI/notebook)
- Dashboard comes after: models proven -> API layer -> dashboard
- Use a simple template (Streamlit or basic Flask) for initial visualization during model development
- Design the API schema based on what the models actually produce, not what the dashboard mockup assumed

**Detection:** If the dashboard is being built but `model.predict()` hasn't been called on real data yet, priorities are inverted.

**Phase relevance:** Phase ordering. Statistical models and data pipeline must precede dashboard development.

---

## Minor Pitfalls

---

### Pitfall 10: Ignoring Home/Away and Rest Day Features

**What goes wrong:** NBA home teams win approximately 58% of games. Teams on back-to-backs (second game in two nights) perform measurably worse. Travel distance between games matters. Ignoring these basic features means the model misses 5-8% of predictive signal.

**Prevention:**
- Include: home/away, days of rest, travel distance, timezone changes, altitude (Denver)
- Include schedule context: back-to-back, 3-in-4-nights, road trip length
- These features are easy to compute from the schedule and have strong, well-documented effects

**Phase relevance:** Feature engineering phase. Add these as baseline features before any advanced statistics.

---

### Pitfall 11: Not Handling Missing Player Data (Injuries, Rest, Trades)

**What goes wrong:** Model predicts based on season averages, but a team's best player is injured. The prediction doesn't account for this because the injury report wasn't incorporated. Mid-season trades create discontinuities: a player's stats reset with a new team, old team stats become stale.

**Prevention:**
- Integrate injury report data (available from NBA.com and `nba_api`)
- Use lineup-adjusted predictions: compute team strength based on expected lineup, not season totals
- Handle trade deadlines: when a player is traded, start a new statistical window for both the player and affected teams
- Weight recent games (last 10-15) more heavily than season averages

**Phase relevance:** Data pipeline and feature engineering phases. Injury report integration should be part of the daily data sync.

---

### Pitfall 12: Hermes Agent as Oracle Instead of Advisor

**What goes wrong:** Users ask "Who will win tonight?" and the agent gives a definitive answer without communicating uncertainty. When it's wrong, trust collapses. The agent's conversational fluency makes its predictions sound more authoritative than they are.

**Prevention:**
- Always surface probability ranges, not binary predictions
- Include model confidence and historical accuracy for similar predictions
- Hermes Agent should present the model's output with appropriate hedging, not add its own "reasoning" on top
- Track and display the agent's prediction track record transparently

**Phase relevance:** Hermes Agent integration and UX design phases.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Data Pipeline (Phase 1) | nba_api breaks mid-season, silent data staleness | Adapter pattern, caching DB, sync monitoring, fallback source |
| Feature Engineering (Phase 2) | Temporal leakage in rolling features, multicollinearity | FeatureValidator with timestamp checks, correlation analysis |
| ML Models (Phase 3) | Overfitting to historical seasons, evaluating on accuracy alone | Rolling training windows, calibration plots, Brier score |
| Computer Vision (Phase 4+) | Legal exposure, broadcast footage quality, massive scope | Defer to late phase, use existing tracking data from nba_api first |
| Hermes Agent Integration | Memory bloat, model compatibility, overconfident responses | Memory TTL, structured storage, probability-first UX |
| Web Dashboard | Building UI before models validated | Models first, dashboard after API schema is stable |
| Prediction Tracking | Edge cases in outcome matching (postponements, scratches) | OutcomeResolver with explicit rules for every edge case |
| Daily Briefings | Stale predictions if data sync failed overnight | Pre-briefing data freshness check, alert on stale data |

## Sources

- [nba_api Rate Limiting Issue #534](https://github.com/swar/nba_api/issues/534)
- [nba_api Request Rate Discussion #69](https://github.com/swar/nba_api/issues/69)
- [nba_api Timeout Issues #320](https://github.com/swar/nba_api/issues/320)
- [nba_api PyPI (v1.11.4, Feb 2026)](https://pypi.org/project/nba_api/)
- [NBA Terms of Use](https://www.nba.com/termsofuse)
- [Machine Learning for Basketball Game Outcomes (MDPI 2025)](https://www.mdpi.com/2079-3197/13/10/230)
- [Stacked Ensemble for NBA Prediction (Nature Scientific Reports 2025)](https://www.nature.com/articles/s41598-025-13657-1)
- [ML for Sports Betting: Accuracy vs Calibration (ScienceDirect)](https://www.sciencedirect.com/science/article/pii/S266682702400015X)
- [Predicting NBA Games with ML (Towards Data Science)](https://towardsdatascience.com/predicting-the-outcome-of-nba-games-with-machine-learning-a810bb768f20/)
- [Hermes Agent Documentation](https://hermes-agent.nousresearch.com/docs/)
- [Hermes Agent Announcement (MarkTechPost)](https://www.marktechpost.com/2026/02/26/nous-research-releases-hermes-agent-to-fix-ai-forgetfulness-with-multi-level-memory-and-dedicated-remote-terminal-access-support/)
- [AI in Basketball: NBA Innovations (Ultralytics)](https://www.ultralytics.com/blog/application-and-impact-of-ai-in-basketball-and-nba)
- [BallDontLie API](https://nba.balldontlie.io/)
