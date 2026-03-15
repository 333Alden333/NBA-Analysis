"""Optimized POC training - precompute all team stats once."""

import numpy as np
import pandas as pd
from collections import defaultdict
from sportsprediction.data.models.base import create_db_engine
from sportsprediction.data.db import get_session
from sportsprediction.data.models import Game, BoxScore
from sqlalchemy import func


def precompute_team_stats(session, window: int = 10) -> dict:
    """Precompute rolling stats for ALL team-game combinations.
    
    Returns: {(team_id, game_id): {"avg_pts": X, "avg_ast": Y, "avg_reb": Z}}
    """
    print("Precomputing team rolling stats...")
    
    # Get all team-game stats ordered by game
    # For each (team_id, game_id), get cumulative avg up to that point
    
    team_game_stats = defaultdict(lambda: {"pts": [], "ast": [], "reb": []})
    
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
    
    print(f"  Processing {len(bs_data)} box scores...")
    
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
    
    # Compute rolling averages for each team
    print("  Computing rolling averages...")
    rolling_stats = {}
    
    for team_id, games in team_games.items():
        for i, game in enumerate(games):
            # Get prior games (last `window` games)
            start = max(0, i - window)
            prior = games[start:i]
            
            if len(prior) >= 3:  # Need at least 3 games for reliable avg
                rolling_stats[(team_id, game["game_id"])] = {
                    "avg_pts": np.mean([g["pts"] for g in prior]),
                    "avg_ast": np.mean([g["ast"] for g in prior]),
                    "avg_reb": np.mean([g["reb"] for g in prior]),
                    "games_played": len(prior),
                }
    
    print(f"  Computed stats for {len(rolling_stats)} team-game combinations")
    return rolling_stats


def build_dataset(session, rolling_stats: dict) -> pd.DataFrame:
    """Build dataset using precomputed stats."""
    print("Building dataset...")
    
    # Get games with exactly 2 teams
    game_teams = session.query(
        BoxScore.game_id,
        BoxScore.team_id,
        func.sum(BoxScore.points).label('pts'),
    ).group_by(BoxScore.game_id, BoxScore.team_id).all()
    
    # Group by game
    games_data = defaultdict(dict)
    for game_id, team_id, pts in game_teams:
        games_data[game_id][team_id] = float(pts)
    
    # Filter to 2-team games
    valid_games = {k: v for k, v in games_data.items() if len(v) == 2}
    print(f"  Found {len(valid_games)} valid games")
    
    # Build features
    features = []
    game_ids = sorted(valid_games.keys())
    
    for i, game_id in enumerate(game_ids):
        if i % 1000 == 0:
            print(f"    Game {i}/{len(game_ids)}")
        
        teams = valid_games[game_id]
        team_ids = list(teams.keys())
        t1_id, t2_id = team_ids[0], team_ids[1]
        t1_pts, t2_pts = teams[t1_id], teams[t2_id]
        
        # Get precomputed stats
        t1_stats = rolling_stats.get((t1_id, game_id))
        t2_stats = rolling_stats.get((t2_id, game_id))
        
        if not t1_stats or not t2_stats:
            continue
        
        features.append({
            "game_id": game_id,
            "t1_team_id": t1_id,
            "t2_team_id": t2_id,
            "t1_pts": t1_pts,
            "t2_pts": t2_pts,
            "target": 1 if t1_pts > t2_pts else 0,
            # Team 1 features
            "t1_avg_pts": t1_stats["avg_pts"],
            "t1_avg_ast": t1_stats["avg_ast"],
            "t1_avg_reb": t1_stats["avg_reb"],
            # Team 2 features
            "t2_avg_pts": t2_stats["avg_pts"],
            "t2_avg_ast": t2_stats["avg_ast"],
            "t2_avg_reb": t2_stats["avg_reb"],
            # Differential
            "pt_diff": t1_stats["avg_pts"] - t2_stats["avg_pts"],
            "ast_diff": t1_stats["avg_ast"] - t2_stats["avg_ast"],
            "reb_diff": t1_stats["avg_reb"] - t2_stats["avg_reb"],
        })
    
    return pd.DataFrame(features)


if __name__ == "__main__":
    engine = create_db_engine("data/hermes.db")
    
    with get_session(engine) as session:
        rolling_stats = precompute_team_stats(session, window=10)
        df = build_dataset(session, rolling_stats)
        
        # Save
        df.to_csv("data/poc_training_data.csv", index=False)
        
        print(f"\n=== Dataset ===")
        print(f"Shape: {df.shape}")
        print(f"Target dist: {df['target'].value_counts().to_dict()}")
        print(f"\nFeatures:\n{df[['pt_diff', 'ast_diff', 'reb_diff', 'target']].head(10)}")