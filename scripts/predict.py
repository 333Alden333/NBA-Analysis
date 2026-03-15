"""Prediction CLI for NBA games."""

import joblib
import numpy as np
import pandas as pd
from sportsprediction.data.models.base import create_db_engine
from sportsprediction.data.db import get_session
from sportsprediction.data.models import BoxScore, Game
from collections import defaultdict
from sqlalchemy import func


def precompute_team_stats(session, window: int = 10) -> dict:
    """Precompute rolling stats for ALL team-game combinations."""
    # Get all box scores with game dates
    bs_data = (
        session.query(
            BoxScore.team_id,
            BoxScore.game_id,
            Game.game_date,
            BoxScore.points,
            BoxScore.assists,
            BoxScore.rebounds,
        )
        .join(Game, BoxScore.game_id == Game.game_id)
        .order_by(Game.game_date.asc())
        .all()
    )
    
    # Group by team -> game
    team_games = defaultdict(list)
    for team_id, game_id, game_date, pts, ast, reb in bs_data:
        team_games[team_id].append({
            "game_id": game_id,
            "game_date": game_date,
            "pts": pts or 0,
            "ast": ast or 0,
            "reb": reb or 0,
        })
    
    # Compute rolling averages
    rolling_stats = {}
    for team_id, games in team_games.items():
        for i, game in enumerate(games):
            start = max(0, i - window)
            prior = games[start:i]
            
            if len(prior) >= 3:
                rolling_stats[(team_id, game["game_id"])] = {
                    "avg_pts": np.mean([g["pts"] for g in prior]),
                    "avg_ast": np.mean([g["ast"] for g in prior]),
                    "avg_reb": np.mean([g["reb"] for g in prior]),
                }
    
    return rolling_stats


def expected_score(rating_a, rating_b):
    """Calculate expected score for player A vs player B."""
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def predict_game(model_data, t1_id, t2_id, rolling_stats, elo_ratings):
    import json
    
    # Try to load ELO from file
    if not elo_ratings:
        try:
            with open("data/elo_ratings.json") as f:
                elo_ratings = json.load(f)
        except:
            elo_ratings = {}
    
    t1_elo = elo_ratings.get(str(t1_id), elo_ratings.get(t1_id, {}))
    t2_elo = elo_ratings.get(str(t2_id), elo_ratings.get(t2_id, {}))
    
    if not t1_elo or not t2_elo:
        return {"error": "No ELO data for teams"}
    
    # Get rolling stats if available
    t1_key = None
    t2_key = None
    
    for (tid, gid), stats in rolling_stats.items():
        if tid == t1_id and t1_key is None:
            t1_key = (tid, gid)
        if tid == t2_id and t2_key is None:
            t2_key = (tid, gid)
    
    pt_diff = 0
    if t1_key and t2_key:
        t1_stats = rolling_stats[t1_key]
        t2_stats = rolling_stats[t2_key]
        pt_diff = t1_stats["avg_pts"] - t2_stats["avg_pts"]
    
    # ELO prediction
    t1_elo_val = t1_elo.get("elo", 1500)
    t2_elo_val = t2_elo.get("elo", 1500)
    prob = expected_score(t1_elo_val, t2_elo_val)
    
    return {
        "team1_win_prob": round(prob, 3),
        "team2_win_prob": round(1 - prob, 3),
        "team1_avg_pts": round(t1_stats["avg_pts"], 1) if t1_key else 0,
        "team2_avg_pts": round(t2_stats["avg_pts"], 1) if t2_key else 0,
        "point_differential": round(pt_diff, 1),
    }


def list_recent_games(session, limit: int = 10):
    """List recent games with scores."""
    # Get games with scores from box scores
    game_teams = session.query(
        BoxScore.game_id,
        BoxScore.team_id,
        func.sum(BoxScore.points).label('pts'),
    ).group_by(BoxScore.game_id, BoxScore.team_id).all()
    
    games_data = defaultdict(dict)
    for game_id, team_id, pts in game_teams:
        games_data[game_id][team_id] = float(pts)
    
    # Filter to 2-team games
    valid = {k: v for k, v in games_data.items() if len(v) == 2}
    
    # Get ALL game dates in one query
    all_dates = {g.game_id: g.game_date for g in session.query(Game.game_id, Game.game_date).all()}
    
    # Sort by date (most recent first), only include games with dates
    sorted_games = sorted(
        [g for g in valid.keys() if g in all_dates and all_dates[g]],
        key=lambda g: all_dates[g],
        reverse=True
    )[:limit]
    
    # Build results
    results = []
    for gid in sorted_games:
        teams = valid[gid]
        tids = list(teams.keys())
        results.append({
            "game_id": gid,
            "date": all_dates.get(gid),
            "team1": tids[0],
            "team1_pts": teams[tids[0]],
            "team2": tids[1],
            "team2_pts": teams[tids[1]],
        })
    
    return results


if __name__ == "__main__":
    import sys
    import json
    
    # Load model
    model_data = joblib.load("data/poc_model_v2.pkl")
    print("✓ Loaded model v2")
    
    # Load ELO ratings
    try:
        with open("data/elo_ratings.json") as f:
            elo_ratings = json.load(f)
        print("✓ Loaded ELO ratings")
    except FileNotFoundError:
        elo_ratings = {}
        print("⚠ ELO ratings not found (run compute_elo.py first)")
    
    # Load team names
    from sportsprediction.data.models import Team
    team_names = {}
    
    # Load data
    engine = create_db_engine("data/hermes.db")
    
    with get_session(engine) as session:
        # Get team names
        for t in session.query(Team).all():
            team_names[t.team_id] = t.full_name
        
        # Precompute stats
        rolling_stats = precompute_team_stats(session)
        
        if len(sys.argv) > 1 and sys.argv[1] == "games":
            # List recent games
            games = list_recent_games(session)
            print("\nRecent games:")
            for g in games:
                t1_name = team_names.get(g['team1'], f"Team {g['team1']}")
                t2_name = team_names.get(g['team2'], f"Team {g['team2']}")
                print(f"  {g['date']}: {t1_name} {g['team1_pts']:.0f} - {t2_name} {g['team2_pts']:.0f}")
        
        elif len(sys.argv) > 1 and sys.argv[1] == "elo":
            # Show ELO standings
            print("\n=== ELO RANKINGS ===")
            sorted_elo = sorted(elo_ratings.items(), key=lambda x: x[1]["elo"], reverse=True)
            print(f"{'Rank':<5} {'Team':<25} {'ELO':<8} {'Record':<12} {'Win%'}")
            print("-" * 60)
            for i, (tid, data) in enumerate(sorted_elo[:15], 1):
                name = team_names.get(int(tid), f"Team {tid}")[:24]
                print(f"{i:<5} {name:<25} {data['elo']:<8.0f} {data['wins']}-{data['losses']:<6} {data['win_pct']}%")
        
        elif len(sys.argv) >= 3:
            # Predict specific matchup
            t1 = int(sys.argv[1])
            t2 = int(sys.argv[2])
            
            t1_name = team_names.get(t1, f"Team {t1}")
            t2_name = team_names.get(t2, f"Team {t2}")
            
            result = predict_game(model_data, t1, t2, rolling_stats, elo_ratings)
            if "error" in result:
                print(f"Error: {result['error']}")
            else:
                print(f"\n=== PREDICTION ===")
                print(f"{t1_name} vs {t2_name}")
                print(f"\nML Model:")
                print(f"  {t1_name} win probability: {result['team1_win_prob']:.1%}")
                print(f"  {t2_name} win probability: {result['team2_win_prob']:.1%}")
                print(f"  Point differential: {result['point_differential']:+.1f}")
                
                # Show ELO ratings
                t1_elo = elo_ratings.get(str(t1), elo_ratings.get(t1, {}))
                t2_elo = elo_ratings.get(str(t2), elo_ratings.get(t2, {}))
                
                if t1_elo and t2_elo:
                    print(f"\nELO Ratings:")
                    print(f"  {t1_name}: {t1_elo.get('elo', 1500):.0f} ({t1_elo.get('wins', 0)}-{t1_elo.get('losses', 0)}, {t1_elo.get('win_pct', 0):.1f}%)")
                    print(f"  {t2_name}: {t2_elo.get('elo', 1500):.0f} ({t2_elo.get('wins', 0)}-{t2_elo.get('losses', 0)}, {t2_elo.get('win_pct', 0):.1f}%)")
                    
                    # ELO prediction
                    prob = expected_score(t1_elo.get('elo', 1500), t2_elo.get('elo', 1500))
                    print(f"  ELO-based win probability: {prob:.1%}")
        else:
            print("Usage:")
            print("  python scripts/predict.py games           # List recent games")
            print("  python scripts/predict.py elo             # Show ELO rankings")
            print("  python scripts/predict.py <team1> <team2> # Predict matchup")