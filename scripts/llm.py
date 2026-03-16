#!/usr/bin/env python3
"""NBA Analyst - LLM client for natural language queries."""

import os
import json
import requests

# Load API key from .env
def get_api_key():
    """Get OpenRouter API key."""
    env_path = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith("OPENROUTER_API_KEY="):
                    return line.split("=", 1)[1].strip()
    return None

# Default model
DEFAULT_MODEL = "anthropic/claude-3-haiku"

def chat(messages, model=DEFAULT_MODEL):
    """Send chat request to OpenRouter."""
    api_key = get_api_key()
    if not api_key:
        return "Error: No API key found. Set OPENROUTER_API_KEY in ~/.hermes/.env"
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/NousResearch/HermesAgent",
        "X-Title": "NBA Analyst"
    }
    
    data = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1024
    }
    
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        return result["choices"][0]["message"]["content"]
    except requests.exceptions.Timeout:
        return "Error: Request timed out. Try again."
    except requests.exceptions.RequestException as e:
        return f"Error: {e}"
    except json.JSONDecodeError:
        return "Error: Invalid response from API"
    except KeyError:
        return "Error: Unexpected response format"

# NBA tools description for the LLM
NBA_TOOLS_CONTEXT = """
You are NBA Analyst, an expert NBA prediction assistant with access to the following tools:

Tools:
- /elo: Show ELO rankings (best teams)
- /games: Recent game scores
- /predict <team1> <team2>: Predict winner between two teams
- /odds: Polymarket championship odds
- /teams: List all teams
- /player <name>: Player stats
- /team <name>: Team stats
- /compare <p1> vs <p2>: Compare players
- /trend <player>: PPG trend
- /top <pts|reb|ast|stl|blk|3pm>: League leaders
- /heatmap: Stats correlation
- /shot <player>: Shot chart
- /pattern <player> vs <team>: Player vs team analysis
- /matchup <player> vs <team>: Matchup classification
- /edge: Betting edges
- /momentum: Who's hot/cold

When user asks about predictions, betting, or analysis, provide thoughtful answers based on the data. If they want specific data, suggest using the appropriate /command.
"""

def ask(prompt):
    """Ask a natural language question about the NBA."""
    messages = [
        {"role": "system", "content": NBA_TOOLS_CONTEXT},
        {"role": "user", "content": prompt}
    ]
    return chat(messages)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(ask(" ".join(sys.argv[1:])))
    else:
        print("Usage: python llm.py <question>")
