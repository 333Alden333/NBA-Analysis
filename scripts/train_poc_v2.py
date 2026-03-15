"""Ultra-minimal training pipeline - derive everything from box scores.

Since game table has NULL home/away, we derive from box scores directly.
"""

import numpy as np
import pandas as pd
from collections import defaultdict
from sportsprediction.data.models.base import create_db_engine
from sportsprediction.data.db import get_session
from sportsprediction.data.models import Game, BoxScore


def derive_game_scores(session) -> dict:
    """Derive game scores and teams from box scores."""
    # Get total points per team per game
    game_teams = session.query(
        BoxScore.game_id,
        BoxScore.team_id,
        func.sum(BoxScore.points).label('team_points')
    ).group_by(BoxScore.game_id, BoxScore.team_id).all()
    
    games = {}
    for game_id, team_id, pts in game_teams:
        if game_id not in games:
            games[game_id] = {}
        games[game_id][team_id] = pts
    
    return games


def get_team_stats_prior(session, team_id: int, before_game_id: str, window: int = 10) -> dict:
    """Get team's avg stats in prior games (by game_id ordering)."""
    # Find game date for comparison
    current_game = session.query(Game).filter_by(game_id=before_game_id).first()
    if not current_game:
        return {}
    
    # Get prior games for this team
    prior_bs = (
        session.query(BoxScore)
        .join(Game, BoxScore.game_id == Game.game_id)
        .filter(
            BoxScore.team_id == team_id,
            Game.game_id < before_game_id
        )
        .order_by(Game.game_id.desc())
        .limit(window)
        .all()
    )
    
    if not prior_bs:
        return {}
    
    return {
        "avg_pts": np.mean([bs.points or 0 for bs in prior_bs]),
        "avg_ast": np.mean([bs.assists or 0 for bs in prior_bs]),
        "avg_reb": np.mean([bs.rebounds or 0 for bs in prior_bs]),
    }


def build_dataset(session) -> pd.DataFrame:
    """Build training data from box scores."""
    print("Loading game scores from box scores...")
    
    # Get all games with 2 teams (regular games)
    game_teams = session.query(
        BoxScore.game_id,
        BoxScore.team_id,
        func.sum(BoxScore.points).label('pts'),
        func.sum(BoxScore.assists).label('ast'),
        func.sum(BoxScore.rebounds).label('reb'),
    ).group_by(BoxScore.game_id, BoxScore.team_id).all()
    
    # Organize by game
    games_data = defaultdict(list)
    for game_id, team_id, pts, ast, reb in game_teams:
        games_data[game_id].append({
            "team_id": team_id,
            "pts": float(pts),
            "ast": float(ast),
            "reb": float(reb),
        })
    
    # Only keep games with exactly 2 teams
    valid_games = {k: v for k, v in games_data.items() if len(v) == 2}
    print(f"Found {len(valid_games)} valid games")
    
    # Get game dates
    game_dates = {g.game_id: g.game_date for g in session.query(Game).all()}
    
    # Build features
    print("Building features...")
    features = []
    
    # Sort game IDs by some ordering (they're already roughly chronological)
    sorted_game_ids = sorted(valid_games.keys())
    
    for i, game_id in enumerate(sorted_game_ids):
        if i % 500 == 0:
            print(f"  Game {i}/{len(sorted_game_ids)}")
        
        teams = valid_games[game_id]
        t1, t2 = teams[0], teams[1]
        
        # Skip first 20 games (not enough history)
        if i < 20:
            continue
        
        # Get prior stats for both teams
        t1_prior = get_team_stats_prior(session, t1["team_id"], game_id, 10)
        t2_prior = get_team_stats_prior(session, t2["team_id"], game_id, 10)
        
        if not t1_prior or not t2_prior:
            continue
        
        # Target: did team 1 win?
        target = 1 if t1["pts"] > t2["pts"] else 0
        
        features.append({
            "game_id": game_id,
            "game_date": game_dates.get(game_id),
            "t1_team_id": t1["team_id"],
            "t2_team_id": t2["team_id"],
            "t1_pts": t1["pts"],
            "t2_pts": t2["pts"],
            "target": target,
            # Team 1 features
            "t1_avg_pts": t1_prior["avg_pts"],
            "t1_avg_ast": t1_prior["avg_ast"],
            "t1_avg_reb": t1_prior["avg_reb"],
            # Team 2 features  
            "t2_avg_pts": t2_prior["avg_pts"],
            "t2_avg_ast": t2_prior["avg_ast"],
            "t2_avg_reb": t2_prior["avg_reb"],
            # Differential
            "pt_diff": t1_prior["avg_pts"] - t2_prior["avg_pts"],
            "ast_diff": t1_prior["avg_ast"] - t2_prior["avg_ast"],
            "reb_diff": t1_prior["avg_reb"] - t2_prior["avg_reb"],
        })
    
    return pd.DataFrame(features)


from sqlalchemy import func


if __name__ == "__main__":
    engine = create_db_engine("data/hermes.db")
    
    with get_session(engine) as session:
        df = build_dataset(session)
        
        # Save
        df.to_csv("data/poc_training_data.csv", index=False)
        
        print(f"\n=== Dataset Summary ===")
        print(f"Shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        print(f"\nTarget distribution:\n{df['target'].value_counts()}")
        print(f"\nSample data:")
        print(df.head(10).to_string())
        
        # Quick stats
        print(f"\n=== Feature Stats ===")
        for col in ["pt_diff", "ast_diff", "reb_diff"]:
            print(f"{col}: mean={df[col].mean():.2f}, std={df[col].std():.2f}")
