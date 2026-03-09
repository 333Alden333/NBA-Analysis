"""smolagents Tool subclasses wrapping NBA data queries.

Each tool:
- Inherits from smolagents.Tool
- Has name, description, inputs, output_type = "string"
- Stores db_session in __init__
- Calls data_queries + formatters in forward()
- Handles missing data gracefully
"""

from datetime import date

from smolagents import Tool

from hermes.agent.data_queries import (
    search_players,
    get_player_recent_games,
    get_player_predictions as query_player_predictions,
    get_today_games,
    get_team_standings,
    get_team_info_with_record,
    get_prediction_accuracy as query_prediction_accuracy,
    get_prediction_history as query_prediction_history,
    get_matchup_analysis as query_matchup_analysis,
    search_teams,
)
from hermes.agent.formatters import (
    format_player_games,
    format_player_search,
    format_predictions,
    format_games_slate,
    format_standings,
    format_metrics,
    format_matchup,
)


def _resolve_player(session, player_name: str):
    """Resolve a player name to player_id via fuzzy search.

    Returns (player_id, full_name) or (None, error_message).
    """
    results = search_players(session, player_name)
    if not results:
        return None, f"No matching players found for '{player_name}'."
    return results[0]["player_id"], results[0]["full_name"]


def _resolve_team(session, team_name: str):
    """Resolve a team name to team dict via fuzzy search.

    Returns (team_dict, None) or (None, error_message).
    """
    team = search_teams(session, team_name)
    if not team:
        return None, f"Team not found: '{team_name}'."
    return team, None


class SearchPlayer(Tool):
    name = "search_player"
    description = (
        "Search for an NBA player by name. Use partial names like 'LeBron' or "
        "'Curry'. Returns a list of matching players with their team and position."
    )
    inputs = {
        "player_name": {
            "type": "string",
            "description": "Player name or partial name to search for",
        }
    }
    output_type = "string"

    def __init__(self, db_session, **kwargs):
        self._session = db_session
        super().__init__(**kwargs)

    def forward(self, player_name: str) -> str:
        results = search_players(self._session, player_name)
        if not results:
            return f"No matching players found for '{player_name}'."
        return format_player_search(results)


class GetPlayerStats(Tool):
    name = "get_player_stats"
    description = (
        "Get recent game stats for an NBA player. Shows points, rebounds, assists, "
        "3-pointers, minutes, and plus-minus for the last 10 games. "
        "Example: 'LeBron James' or 'Tatum'"
    )
    inputs = {
        "player_name": {
            "type": "string",
            "description": "Player name to look up",
        }
    }
    output_type = "string"

    def __init__(self, db_session, **kwargs):
        self._session = db_session
        super().__init__(**kwargs)

    def forward(self, player_name: str) -> str:
        pid, name_or_err = _resolve_player(self._session, player_name)
        if pid is None:
            return name_or_err

        games = get_player_recent_games(self._session, pid)
        if not games:
            return f"No recent games found for {name_or_err}."

        header = f"Recent games for {name_or_err}:\n\n"
        return header + format_player_games(games)


class GetPlayerPredictions(Tool):
    name = "get_player_predictions"
    description = (
        "Get recent predictions for an NBA player with actual outcomes. "
        "Shows predicted vs actual values and HIT/MISS status. "
        "Example: 'LeBron James'"
    )
    inputs = {
        "player_name": {
            "type": "string",
            "description": "Player name to look up predictions for",
        }
    }
    output_type = "string"

    def __init__(self, db_session, **kwargs):
        self._session = db_session
        super().__init__(**kwargs)

    def forward(self, player_name: str) -> str:
        pid, name_or_err = _resolve_player(self._session, player_name)
        if pid is None:
            return name_or_err

        preds = query_player_predictions(self._session, pid)
        if not preds:
            return f"No predictions found for {name_or_err}."

        # Add status field
        for p in preds:
            if p.get("is_correct") is not None:
                p["status"] = "HIT" if p["is_correct"] == 1 else "MISS"
            else:
                p["status"] = "PENDING"

        header = f"Predictions for {name_or_err}:\n\n"
        return header + format_predictions(preds)


class GetTeamInfo(Tool):
    name = "get_team_info"
    description = (
        "Get NBA team info and current season record. "
        "Accepts team name ('Lakers'), city ('Boston'), or abbreviation ('LAL'). "
        "Returns team details with wins, losses, and conference."
    )
    inputs = {
        "team_name": {
            "type": "string",
            "description": "Team name, city, or abbreviation",
        }
    }
    output_type = "string"

    def __init__(self, db_session, **kwargs):
        self._session = db_session
        super().__init__(**kwargs)

    def forward(self, team_name: str) -> str:
        team, err = _resolve_team(self._session, team_name)
        if team is None:
            return err

        info = get_team_info_with_record(self._session, team["team_id"])
        if not info:
            return f"Team not found: '{team_name}'."

        w = info.get("wins", 0) or 0
        l = info.get("losses", 0) or 0
        pct = w / (w + l) if (w + l) > 0 else 0.0

        lines = [
            f"{info['full_name']} ({info.get('abbreviation', '?')})",
            f"Conference: {info.get('conference', '?')} | Division: {info.get('division', '?')}",
            f"Record: {w}-{l} ({pct:.3f})",
        ]
        return "\n".join(lines)


class GetTodayGames(Tool):
    name = "get_today_games"
    description = (
        "Get today's NBA game schedule with predictions (win probability, spread, total). "
        "Shows matchups and current scores for games in progress."
    )
    inputs = {
        "date_str": {
            "type": "string",
            "description": "Date in YYYY-MM-DD format. Defaults to today if not provided.",
            "nullable": True,
        }
    }
    output_type = "string"

    def __init__(self, db_session, **kwargs):
        self._session = db_session
        super().__init__(**kwargs)

    def forward(self, date_str: str = None) -> str:
        if not date_str:
            date_str = str(date.today())

        games = get_today_games(self._session, date_str)
        if not games:
            return f"No games scheduled for {date_str}."

        header = f"Games for {date_str}:\n\n"
        return header + format_games_slate(games)


class GetPredictionAccuracy(Tool):
    name = "get_prediction_accuracy"
    description = (
        "Get model prediction accuracy metrics -- hit rate, Brier score, MAE, RMSE. "
        "Can filter by prediction type: 'game_winner', 'game_spread', 'game_total', "
        "'player_points', 'player_rebounds', 'player_assists', 'player_3pm'. "
        "Pass None for all types."
    )
    inputs = {
        "prediction_type": {
            "type": "string",
            "description": "Prediction type to filter by, or None for all types",
            "nullable": True,
        }
    }
    output_type = "string"

    def __init__(self, db_session, **kwargs):
        self._session = db_session
        super().__init__(**kwargs)

    def forward(self, prediction_type: str = None) -> str:
        metrics = query_prediction_accuracy(self._session, prediction_type)
        if not metrics:
            return "No accuracy data available yet."
        return format_metrics(metrics)


class GetPredictionHistory(Tool):
    name = "get_prediction_history"
    description = (
        "Get recent prediction outcomes showing HIT/MISS/PENDING status. "
        "Optionally filter by prediction type. Shows game date, matchup, "
        "predicted value, actual value, and result."
    )
    inputs = {
        "prediction_type": {
            "type": "string",
            "description": "Prediction type to filter by, or None for all",
            "nullable": True,
        }
    }
    output_type = "string"

    def __init__(self, db_session, **kwargs):
        self._session = db_session
        super().__init__(**kwargs)

    def forward(self, prediction_type: str = None) -> str:
        history = query_prediction_history(
            self._session, prediction_type=prediction_type
        )
        if not history:
            return "No prediction history available."
        return format_predictions(history)


class GetMatchupAnalysis(Tool):
    name = "get_matchup_analysis"
    description = (
        "Analyze a player's historical performance against a specific team. "
        "Shows matchup averages for points, rebounds, assists, FG%, and +/- "
        "compared to their overall averages. "
        "Example: player='LeBron James', team='Boston Celtics'"
    )
    inputs = {
        "player_name": {
            "type": "string",
            "description": "Player name to analyze",
        },
        "team_name": {
            "type": "string",
            "description": "Opponent team name or abbreviation",
        },
    }
    output_type = "string"

    def __init__(self, db_session, **kwargs):
        self._session = db_session
        super().__init__(**kwargs)

    def forward(self, player_name: str, team_name: str) -> str:
        pid, name_or_err = _resolve_player(self._session, player_name)
        if pid is None:
            return name_or_err

        team, err = _resolve_team(self._session, team_name)
        if team is None:
            return err

        data = query_matchup_analysis(self._session, pid, team["team_id"])
        if not data:
            return (
                f"No matchup history found for {name_or_err} "
                f"vs {team['full_name']}."
            )

        return format_matchup(data)
