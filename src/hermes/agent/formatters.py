"""Text formatters for agent tool output.

Convert query results into concise, LLM-readable strings.
Max ~20 rows in any table to respect context limits.
"""


def format_player_games(games: list[dict]) -> str:
    """Format recent games as a text table."""
    if not games:
        return "No recent games found."

    lines = []
    lines.append(f"{'Date':<12} {'vs':<8} {'PTS':>4} {'REB':>4} {'AST':>4} {'3PM':>4} {'MIN':>5} {'+/-':>5}")
    lines.append("-" * 50)

    for g in games[:20]:
        date_str = str(g.get("game_date", ""))[:10]
        # Determine opponent
        opp = g.get("away_abbr", "?")
        if g.get("home_abbr"):
            # If player's team is home, opponent is away
            opp = f"vs {g.get('away_abbr', '?')}"
        pts = g.get("points", 0) or 0
        reb = g.get("rebounds", 0) or 0
        ast = g.get("assists", 0) or 0
        fg3 = g.get("fg3m", 0) or 0
        mins = g.get("minutes", 0) or 0
        pm = g.get("plus_minus", 0) or 0

        lines.append(
            f"{date_str:<12} {opp:<8} {pts:>4} {reb:>4} {ast:>4} {fg3:>4} {mins:>5.0f} {pm:>+5.0f}"
        )

    return "\n".join(lines)


def format_standings(standings: list[dict]) -> str:
    """Format standings grouped by conference."""
    if not standings:
        return "No standings data available."

    lines = []
    current_conf = None

    for t in standings:
        conf = t.get("conference", "Unknown")
        if conf != current_conf:
            if current_conf is not None:
                lines.append("")
            lines.append(f"--- {conf} Conference ---")
            lines.append(f"{'#':<3} {'Team':<28} {'W':>4} {'L':>4} {'PCT':>6}")
            lines.append("-" * 48)
            current_conf = conf
            rank = 1

        w = t.get("wins", 0) or 0
        l = t.get("losses", 0) or 0
        pct = w / (w + l) if (w + l) > 0 else 0.0
        name = t.get("full_name", "Unknown")[:26]
        lines.append(f"{rank:<3} {name:<28} {w:>4} {l:>4} {pct:>6.3f}")
        rank += 1

    return "\n".join(lines)


def format_games_slate(games: list[dict]) -> str:
    """Format today's games with predictions."""
    if not games:
        return "No games scheduled."

    lines = []
    for g in games[:20]:
        home = g.get("home_abbr", "???")
        away = g.get("away_abbr", "???")
        status = g.get("status", "")
        home_score = g.get("home_score")
        away_score = g.get("away_score")

        game_line = f"{away} @ {home}"
        if home_score is not None and away_score is not None:
            game_line += f"  ({away_score}-{home_score})"
        if status:
            game_line += f"  [{status}]"

        # Predictions
        wp = g.get("win_probability")
        spread = g.get("predicted_spread")
        total = g.get("predicted_total")

        pred_parts = []
        if wp is not None:
            pred_parts.append(f"Home Win: {wp:.0%}")
        if spread is not None:
            pred_parts.append(f"Spread: {spread:+.1f}")
        if total is not None:
            pred_parts.append(f"Total: {total:.1f}")

        if pred_parts:
            game_line += "\n  Predictions: " + " | ".join(pred_parts)

        lines.append(game_line)

    return "\n\n".join(lines)


def format_predictions(predictions: list[dict]) -> str:
    """Format prediction list with HIT/MISS/PENDING status."""
    if not predictions:
        return "No predictions found."

    lines = []
    lines.append(f"{'Date':<12} {'Game':<12} {'Type':<14} {'Pred':>6} {'Actual':>7} {'Status':>8}")
    lines.append("-" * 62)

    for p in predictions[:20]:
        date_str = str(p.get("game_date", ""))[:10]
        home = p.get("home_abbr", "?")
        away = p.get("away_abbr", "?")
        game_str = f"{away}@{home}"
        ptype = p.get("prediction_type", "?")[:13]
        pred_val = p.get("predicted_value")
        actual = p.get("actual_value")
        status = p.get("status", "PENDING")

        pred_str = f"{pred_val:.1f}" if pred_val is not None else "N/A"
        actual_str = f"{actual:.1f}" if actual is not None else "---"

        lines.append(
            f"{date_str:<12} {game_str:<12} {ptype:<14} {pred_str:>6} {actual_str:>7} {status:>8}"
        )

    return "\n".join(lines)


def format_player_search(results: list[dict]) -> str:
    """Format player search results."""
    if not results:
        return "No matching players found."

    lines = []
    for i, p in enumerate(results, 1):
        name = p.get("full_name", "Unknown")
        team = p.get("team_abbr", "???")
        pos = p.get("position", "?")
        lines.append(f"{i}. {name} ({team}, {pos})")

    return "\n".join(lines)


def format_metrics(metrics: dict) -> str:
    """Format prediction accuracy metrics."""
    if not metrics:
        return "No metrics data available."

    # If it's a by-type summary
    if "by_type" in metrics:
        lines = []
        lines.append(f"{'Type':<20} {'Hit Rate':>10} {'Score':>10} {'Resolved':>10}")
        lines.append("-" * 52)

        for ptype, m in sorted(metrics["by_type"].items()):
            hr = f"{m.get('hit_rate', 0):.1%}"
            resolved = str(m.get("total_resolved", 0))
            if "brier_score" in m:
                score = f"Brier {m['brier_score']:.4f}"
            elif "mae" in m:
                score = f"MAE {m['mae']:.2f}"
            else:
                score = "N/A"
            lines.append(f"{ptype:<20} {hr:>10} {score:>10} {resolved:>10}")

        return "\n".join(lines)

    # Single type
    ptype = metrics.get("prediction_type", "all")
    hr = f"{metrics.get('hit_rate', 0):.1%}"
    resolved = metrics.get("total_resolved", 0)
    total = metrics.get("total_predictions", 0)

    parts = [f"Type: {ptype}", f"Hit Rate: {hr}", f"Resolved: {resolved}/{total}"]

    if "brier_score" in metrics:
        parts.append(f"Brier Score: {metrics['brier_score']:.4f}")
    if "mae" in metrics:
        parts.append(f"MAE: {metrics['mae']:.2f}")
    if "rmse" in metrics:
        parts.append(f"RMSE: {metrics['rmse']:.2f}")
    if metrics.get("ci_coverage") is not None:
        parts.append(f"CI Coverage: {metrics['ci_coverage']:.1%}")

    return " | ".join(parts)


def format_matchup(data: dict) -> str:
    """Format matchup analysis summary."""
    if not data:
        return "No matchup history found."

    player = data.get("player_name", "Player")
    opponent = data.get("opponent_team", "Opponent")
    games = data.get("matchup_games_played", 0) or 0

    lines = [f"{player} vs {opponent} ({games} games)"]

    if games > 0:
        lines.append("")
        stats = [
            ("Points", "matchup_avg_points", "matchup_diff_points"),
            ("Rebounds", "matchup_avg_rebounds", "matchup_diff_rebounds"),
            ("Assists", "matchup_avg_assists", "matchup_diff_assists"),
            ("FG%", "matchup_avg_fg_pct", "matchup_diff_fg_pct"),
            ("+/-", "matchup_avg_plus_minus", "matchup_diff_plus_minus"),
        ]

        lines.append(f"{'Stat':<12} {'Avg':>8} {'vs Avg':>8}")
        lines.append("-" * 30)

        for label, avg_key, diff_key in stats:
            avg = data.get(avg_key)
            diff = data.get(diff_key)
            avg_str = f"{avg:.1f}" if avg is not None else "N/A"
            diff_str = f"{diff:+.1f}" if diff is not None else "N/A"
            lines.append(f"{label:<12} {avg_str:>8} {diff_str:>8}")
    else:
        lines.append("No matchup history available.")

    return "\n".join(lines)
