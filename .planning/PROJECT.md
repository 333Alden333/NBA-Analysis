# HermesAnalysis

## What This Is

An AI-powered NBA analysis and prediction platform that combines custom ML models, computer vision game footage analysis, and Nous Research's Hermes Agent for intelligent orchestration. It provides automated daily briefings, pre-game predictions, and on-demand natural language queries across player performance, game outcomes, totals, and player props — accessible through both a web dashboard and CLI.

## Core Value

Accurate, current predictions backed by real data — the model's quality and data freshness are everything. If the predictions aren't trustworthy, nothing else matters.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Comprehensive NBA stats pipeline (player, team, game data) with daily auto-sync
- [ ] Custom ML models for: player points/stats, game winner/spread, over/under totals, player props
- [ ] Computer vision pipeline for game footage analysis (player tracking, shot detection, movement patterns)
- [ ] Hermes Agent integration for orchestration, natural language queries, tool chaining, and learning from outcomes
- [ ] Local database with historical and current season data, updated daily
- [ ] Web dashboard with charts, predictions, and game cards
- [ ] CLI interface via Hermes Agent TUI for deep queries
- [ ] Automated daily briefing generation (today's slate with picks and analysis)
- [ ] Pre-game analysis with matchup breakdowns and predictions
- [ ] On-demand query support ("How will Luka do tonight?")
- [ ] Prediction tracking — log predictions vs actual outcomes for model improvement
- [ ] Hermes Agent memory/learning loop — remembers past predictions, learns from hits and misses

### Out of Scope

- Sports betting odds integration — future consideration, not v1 priority
- Mobile app — web-first
- Real-time in-game live updates — focus on pre-game and post-game analysis
- Paid data APIs — start free (nba_api + caching), upgrade only if gaps found

## Context

- Existing partial codebase at github.com/333Alden333/NBA-ML-PROJECT (13 Jupyter notebooks covering data pulls, player comparison, shot charts, dashboards, efficiency, trends, clutch, home/away)
- That code serves as style/approach reference — HermesAnalysis gets its own repo on the 333Alden333 GitHub account
- Hermes Agent (Nous Research) — self-improving AI agent with built-in learning loop, 40+ tools, MCP server support, persistent memory, scheduling, and multi-backend support. MIT licensed. Installed via curl script.
- Computer vision approach inspired by Roboflow basketball player detection/tracking (YOLO-based)
- nba_api is the primary data source — free, pulls from NBA.com internal endpoints, covers play-by-play, shot charts, tracking data. Rate-limited but manageable with caching.
- balldontlie.io (free tier) and sportsdata.io ($25/mo) as potential supplements if nba_api has gaps
- Game footage sources for CV need research — League Pass replays, YouTube highlights, public broadcast clips. Legal and practical availability TBD.
- Deployment target TBD — start local, deploy when ready
- Free/cost-efficient tooling is strongly preferred throughout

## Constraints

- **Budget**: Free tools preferred. Minimize or eliminate recurring costs.
- **Data source**: nba_api as primary — work around rate limits with caching and a local sync database
- **GitHub account**: Repository lives on 333Alden333 account, not ClarityProtocol
- **ML approach**: Hybrid — custom trained models (XGBoost/LightGBM/neural nets) for probabilistic predictions, Hermes Agent for orchestration and reasoning
- **CV feasibility**: Game footage sourcing needs research before committing to specific pipeline

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Hybrid ML + Hermes Agent | Custom models for math/predictions, Hermes for orchestration/reasoning/memory | — Pending |
| nba_api as primary data source | Free, comprehensive, current — cache aggressively to handle rate limits | — Pending |
| CV as core v1 feature | User priority — player tracking and movement analysis integral to prediction quality | — Pending |
| Dual interface (web + CLI) | Dashboard for visuals/daily use, Hermes TUI for deep interactive queries | — Pending |
| Separate repo from NBA-ML-PROJECT | Clean start, use old notebooks as style reference only | — Pending |

---
*Last updated: 2026-03-07 after initialization*
