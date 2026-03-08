# Features Research: HermesAnalysis

## Table Stakes

Features users expect from any NBA analysis/prediction platform. Missing these = unusable.

| Feature | Complexity | Dependencies |
|---------|-----------|-------------|
| **Daily stats sync** — Automated ingestion of player/team/game stats from nba_api | Medium | Data pipeline, database |
| **Game winner/spread predictions** — ML model predicts which team wins and by how much | High | Historical data, trained models |
| **Over/under totals predictions** — Predict combined game score | High | Historical data, trained models |
| **Player dashboard** — View any player's stats, trends, recent performance | Medium | Data pipeline, web framework |
| **Team dashboard** — Team-level stats, standings, strength of schedule | Medium | Data pipeline, web framework |
| **Injury report integration** — Current injury status affects predictions | Low | Data source for injuries |
| **Prediction tracking** — Log predictions vs actual outcomes | Medium | Database, post-game data sync |
| **Today's games slate** — Show upcoming games with basic matchup info | Low | Schedule data from nba_api |
| **Historical data (3+ seasons)** — Enough data for meaningful ML training | Medium | Bulk data ingestion, storage |
| **Basic model accuracy metrics** — Show how well the model is performing | Low | Prediction tracking |

## Differentiators

Features that set HermesAnalysis apart from typical NBA prediction tools.

| Feature | Complexity | Dependencies |
|---------|-----------|-------------|
| **Player prop predictions** — Predict individual stat lines (points, rebounds, assists, etc.) | High | Player-level models, granular historical data |
| **Computer vision footage analysis** — Track player movement, shot mechanics, defensive positioning from game video | Very High | CV pipeline, footage source, GPU compute |
| **Hermes Agent natural language queries** — Ask questions in plain English, get data-backed analysis | High | Hermes Agent setup, tool definitions, all data tools |
| **Automated daily briefings** — Wake up to a generated analysis of today's slate with picks | Medium | Scheduling, all prediction models, template system |
| **Agent learning loop** — Hermes remembers past predictions, learns from hits/misses, improves recommendations | High | Hermes Agent memory, prediction tracking |
| **Matchup-specific analysis** — How Player X performs vs Team Y's defense historically | Medium | Matchup data, historical cross-referencing |
| **Rolling model retraining** — Models update as new games are played, not static | High | Training pipeline, data freshness |
| **CLI TUI via Hermes** — Deep interactive queries through terminal interface | Medium | Hermes Agent TUI |
| **Confidence calibration** — Model knows when it's uncertain and says so | High | Calibration analysis, ensemble methods |
| **Multi-factor analysis synthesis** — Combine stats + CV + context into unified recommendations | Very High | All subsystems working together |

## Anti-Features

Things to deliberately NOT build. Including reasoning to prevent scope creep.

| Anti-Feature | Why Not |
|-------------|---------|
| **Live in-game predictions** | Requires real-time data feeds, extreme complexity, not core to pre-game analysis focus |
| **Odds/betting integration (v1)** | User deprioritized — focus on model accuracy first, add betting layer later |
| **Mobile native app** | Web-first approach — responsive dashboard covers mobile use cases |
| **Social features** | Not a community platform — single-user analysis tool |
| **Paid data APIs in v1** | Free-first constraint — nba_api with caching is sufficient |
| **Fantasy sports optimization** | Different problem domain — fantasy scoring != real game prediction |
| **Historical game simulation** | Cool but not core — "what if" scenarios don't improve prediction accuracy |
| **Automated bet placement** | Legal/ethical concerns, massive liability, never auto-bet |

## MVP Feature Ordering

1. **Data pipeline + database** — Everything depends on having clean, current data
2. **Core ML models** (game winner, totals) — The fundamental value proposition
3. **Player prop models** — Extends prediction to individual level
4. **Web dashboard** — Visual interface for consuming predictions
5. **Hermes Agent integration** — NL queries, tool orchestration, memory
6. **Daily briefings + scheduling** — Automation layer
7. **CV pipeline** — Deferred until footage sourcing is resolved, highest complexity
8. **Learning loop + retraining** — Requires enough prediction history to learn from

## Feature Dependencies

```
Data Pipeline ──→ ML Models ──→ Predictions
     │                │              │
     ▼                ▼              ▼
  Database      Model Store    Pred Tracking
     │                              │
     ▼                              ▼
 Dashboard ◄──── Hermes Agent ──→ Learning Loop
                      │
                      ▼
               Daily Briefings

CV Pipeline (independent until integration)
  Footage Source → Detection → Tracking → Feature Extraction → Model Input
```

---
*Researched: 2026-03-07*
