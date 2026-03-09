"""Agent factory -- creates a ToolCallingAgent with Ollama LLM backend."""

import logging

import requests
from smolagents import ToolCallingAgent, LiteLLMModel
from sqlalchemy.orm import Session

from hermes.config import settings
from hermes.agent.tools import (
    SearchPlayer,
    GetPlayerStats,
    GetPlayerPredictions,
    GetTeamInfo,
    GetTodayGames,
    GetPredictionAccuracy,
    GetPredictionHistory,
    GetMatchupAnalysis,
)

logger = logging.getLogger(__name__)

HERMES_SYSTEM_PROMPT = """\
You are Hermes, an NBA analytics assistant powered by machine learning models.
Today's date is {today}. Model version: {model_version}.

You have access to tools that query a comprehensive NBA database with:
- Player stats (recent box scores, rolling averages)
- Team standings and records
- Game schedules with predictions (win probability, spread, total)
- Prediction history with HIT/MISS accuracy tracking
- Player vs team matchup analysis

GUIDELINES:
1. Always use tools to look up data -- never guess stats or records.
2. When asked about a player, search for them first if you're unsure of the exact name.
3. Present data concisely. Highlight key insights and trends.
4. When discussing predictions, always mention the model's confidence and track record.
5. If a tool returns no data, explain what's missing and suggest alternatives.
6. Use the prediction accuracy tool to back up claims about model performance.

You are direct, data-driven, and honest about uncertainty. If the model's accuracy
is low for a prediction type, say so.
"""


def create_agent(session: Session) -> ToolCallingAgent:
    """Create a Hermes agent with all NBA tools registered.

    Args:
        session: SQLAlchemy session for database queries.

    Returns:
        ToolCallingAgent ready to handle natural language queries.
    """
    model = LiteLLMModel(
        model_id=f"ollama_chat/{settings.ollama_model}",
        api_base=settings.ollama_base_url,
        api_key="ollama",
        num_ctx=8192,
    )

    tools = [
        SearchPlayer(db_session=session),
        GetPlayerStats(db_session=session),
        GetPlayerPredictions(db_session=session),
        GetTeamInfo(db_session=session),
        GetTodayGames(db_session=session),
        GetPredictionAccuracy(db_session=session),
        GetPredictionHistory(db_session=session),
        GetMatchupAnalysis(db_session=session),
    ]

    from datetime import date

    agent = ToolCallingAgent(
        tools=tools,
        model=model,
        instructions=HERMES_SYSTEM_PROMPT.format(
            today=date.today(), model_version="v1"
        ),
    )

    return agent


def check_ollama_connection() -> bool:
    """Check if Ollama is running and accessible.

    Returns True if connection succeeds, False otherwise.
    """
    try:
        resp = requests.get(
            f"{settings.ollama_base_url}/api/version", timeout=5
        )
        if resp.status_code == 200:
            return True
        logger.warning("Ollama returned status %d", resp.status_code)
        return False
    except Exception as e:
        logger.warning(
            "Cannot connect to Ollama at %s: %s",
            settings.ollama_base_url, e,
        )
        print(
            f"Ollama is not running at {settings.ollama_base_url}.\n"
            f"Start it with: ollama serve\n"
            f"Then pull a model: ollama pull {settings.ollama_model}"
        )
        return False
