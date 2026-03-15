# SportsPrediction

NBA analytics and prediction platform. Python 3.10, SQLAlchemy 2.x, SQLite, Alembic.

## Stack
- **Python 3.10** (system Python — no 3.11+ syntax like `ExceptionGroup`)
- **SQLAlchemy 2.0** with `Mapped`/`mapped_column` declarative style
- **SQLite** with `PRAGMA foreign_keys=ON` (set via engine event listener)
- **Alembic** for schema migrations
- **pandas/numpy** for data manipulation
- **nba_api** for NBA data (rate-limited, needs `RateLimiter`)
- **pytest** for tests (in-memory SQLite, `conftest.py` provides `engine`/`session` fixtures)
- **argparse** for CLI (subcommands pattern)
- **python-dotenv** for env config
- **Hermes Agent** (Nous Research) for natural language orchestration via MCP

## Project Layout
```
src/sportsprediction/
  config.py          — Settings dataclass, env vars, singleton `settings`
  cli.py             — argparse CLI, `sportspred sync --daily|--historical|--status`
  data/
    models/          — SQLAlchemy models (Base, Player, Team, Game, BoxScore, Injury, etc.)
    adapters/        — ABC interfaces (NBADataAdapter, InjuryDataAdapter) + implementations
    ingestion/       — Sync modules (player_sync, team_sync, game_sync, daily_sync, historical)
    features/        — Feature engineering (rolling, advanced, matchup, team)
    db.py            — DB utilities
  models/            — ML prediction models (game, player, totals)
  dashboard/         — Streamlit web UI (5 pages)
  agent/
    data_queries.py  — Streamlit-free DB query functions (for MCP/Hermes Agent)
    formatters.py    — LLM-readable text formatters
tests/
  conftest.py        — engine/session fixtures (in-memory SQLite)
  data/              — Mirrors src/sportsprediction/data/ structure
    fixtures/        — sample_responses.py with mock API data
    conftest.py      — Data-layer specific fixtures
```

## Patterns

### Models
- Inherit from `Base` (DeclarativeBase)
- Use `Mapped[type]` / `Mapped[type | None]` with `mapped_column()`
- Nullable fields: `Mapped[int | None] = mapped_column(Integer, nullable=True)`
- ForeignKey: `ForeignKey("table_name.column_name")`
- Every model stores `raw_json: Mapped[str | None]` for debugging

### Adapters
- `NBADataAdapter(ABC)` — abstract interface for NBA data
- `InjuryDataAdapter(ABC)` — abstract interface for injuries
- Implementations accept a `RateLimiter` instance
- Returns `pd.DataFrame` or `dict[str, Any]`

### Ingestion
- Each entity type has its own sync module (`player_sync.py`, `team_sync.py`, etc.)
- `daily_sync.py` orchestrates all syncs
- `historical.py` handles 3-season backfill with checkpoint/resume via `SyncLog`
- `SyncLog` tracks entity_type + last_sync_at + records_synced per entity

### CLI
- Entry point: `sportspred = "sportsprediction.cli:main"`
- Subcommand pattern: `sportspred sync --daily`, `sportspred sync --historical`
- Lazy imports inside command handlers (avoids import-time side effects)

### Tests
- In-memory SQLite (`sqlite:///:memory:`)
- `engine` and `session` fixtures in `tests/conftest.py`
- FK constraints ON (matches production)
- `flush()` between parent/child inserts (SQLite FK constraint)
- Mock external APIs — never call nba_api in tests

### Config
- `Settings` dataclass with env var defaults
- `settings = Settings()` singleton in `config.py`
- DB path: `SPORTSPRED_DB_PATH` env var, defaults to `data/hermes.db`

## Constraints
- No paid APIs — nba_api (free) is the primary data source
- Rate limit nba_api calls (1-2s delay via `RateLimiter` using `time.monotonic()`)
- Broad exception catch on `nbainjuries` import (`JVMNotFoundException`, not `ImportError`)
- Game IDs tracked per-game in SyncLog for checkpoint/resume
- Seasons: `["2022-23", "2023-24", "2024-25"]`

## Key Commands
```bash
pytest                              # Run all tests (212 passing)
sportspred sync --historical        # Backfill 3 seasons
sportspred sync --daily             # Incremental daily sync
sportspred sync --status            # Print sync summary
sportspred predict --train          # Train ML models
sportspred predict --today          # Generate predictions
sportspred dashboard                # Launch Streamlit dashboard
alembic upgrade head                # Run migrations
```

## Hermes Agent Integration
See HANDOFF.md for full context on the Hermes Agent (Nous Research) integration plan, including MCP server config, skill creation, and what's left to build.
