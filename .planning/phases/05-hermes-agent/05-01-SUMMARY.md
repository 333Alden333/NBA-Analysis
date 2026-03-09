---
phase: 05-hermes-agent
plan: 01
subsystem: agent-core
tags: [agent, smolagents, tools, nlp, ollama]
dependency_graph:
  requires: [dashboard-data-access, prediction-models, metrics]
  provides: [agent-tools, agent-factory, data-queries]
  affects: [05-02-tui, 05-03-learning-loop]
tech_stack:
  added: [smolagents, litellm, rich, prompt_toolkit]
  patterns: [tool-calling-agent, fuzzy-name-resolution, text-formatters]
key_files:
  created:
    - src/hermes/agent/__init__.py
    - src/hermes/agent/data_queries.py
    - src/hermes/agent/tools.py
    - src/hermes/agent/agent.py
    - src/hermes/agent/formatters.py
    - tests/agent/__init__.py
    - tests/agent/conftest.py
    - tests/agent/test_tools.py
    - tests/agent/test_agent.py
  modified:
    - src/hermes/config.py
    - pyproject.toml
decisions:
  - smolagents ToolCallingAgent with `instructions` parameter (not system_prompt)
  - difflib fuzzy matching with 0.4 cutoff for players, 0.5 for teams
  - agent.tools is a dict keyed by tool name (smolagents API)
  - LiteLLM wraps Ollama with ollama_chat/ prefix and api_key="ollama"
metrics:
  duration: 357s
  completed: "2026-03-09T04:32:37Z"
  tasks_completed: 2
  tasks_total: 2
  tests_passing: 22
  files_created: 9
  files_modified: 2
  lines_added: ~1400
---

# Phase 5 Plan 1: Hermes Agent Core Summary

8 smolagents Tool subclasses wrapping NBA data queries with Ollama LLM backend, fuzzy name resolution, and text formatters for concise tool output.

## What Was Built

### Data Queries Layer (`data_queries.py`, 394 lines)
Streamlit-free data access functions mirroring `dashboard/data_access.py`. Each function takes a SQLAlchemy Session and returns plain dicts/lists. Includes 12 query functions covering players, teams, games, predictions, accuracy metrics, and matchup analysis.

### Agent Tools (`tools.py`, 324 lines)
8 smolagents Tool subclasses:
1. **SearchPlayer** -- fuzzy name search via difflib
2. **GetPlayerStats** -- recent box scores with auto name resolution
3. **GetPlayerPredictions** -- predictions with HIT/MISS/PENDING outcomes
4. **GetTeamInfo** -- team record and conference info
5. **GetTodayGames** -- game slate with win probability, spread, total
6. **GetPredictionAccuracy** -- model accuracy metrics (Brier, MAE, RMSE)
7. **GetPredictionHistory** -- recent prediction outcomes
8. **GetMatchupAnalysis** -- player vs team historical performance

### Agent Factory (`agent.py`, 110 lines)
- `create_agent(session)` builds a ToolCallingAgent with all 8 tools
- LiteLLM model wrapping Ollama (configurable via env vars)
- System prompt with NBA analytics context and tool usage guidelines
- `check_ollama_connection()` for startup validation

### Text Formatters (`formatters.py`, 228 lines)
7 formatter functions producing concise LLM-readable text (max 20 rows per table).

### Tests (22 passing)
- Seeded in-memory DB fixture: 2 teams, 2 players, 3 games, box scores, predictions with outcomes, matchup stats
- Tool tests verify forward() with real data and graceful not-found handling
- Agent factory tests with mocked LiteLLM (no Ollama needed)
- System prompt validation tests

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] smolagents API uses `instructions` not `system_prompt`**
- **Found during:** Task 2
- **Issue:** `ToolCallingAgent.__init__()` got unexpected keyword argument 'system_prompt'
- **Fix:** Changed to `instructions=` parameter per smolagents v1.24 API
- **Files modified:** src/hermes/agent/agent.py

**2. [Rule 1 - Bug] agent.tools is dict, not list**
- **Found during:** Task 2
- **Issue:** Test assumed `agent.tools` is a list with `.name` attributes; it's a dict keyed by name
- **Fix:** Updated test to use `agent.tools.keys()`
- **Files modified:** tests/agent/test_agent.py

**3. [Rule 1 - Bug] Team fuzzy match cutoff too loose**
- **Found during:** Task 2
- **Issue:** cutoff=0.4 matched "Nonexistent FC" to "Boston Celtics"
- **Fix:** Tightened team search cutoff to 0.5
- **Files modified:** src/hermes/agent/data_queries.py

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 801e6bd | Data queries, formatters, dependencies |
| 2 (RED) | 860cf96 | Failing tests for tools and agent |
| 2 (GREEN) | 17293b7 | Implement tools, agent factory, pass all tests |
