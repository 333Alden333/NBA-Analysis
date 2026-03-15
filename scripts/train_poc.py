"""Minimal training pipeline for NBA prediction POC.

Goal: Fast, accurate local predictions using rolling stats + team features.
Target: Predict game winners (binary classification).
"""

import numpy as np
import pandas as pd
from sqlalchemy import and_, func
from sportsprediction.data.models.base import create_db_engine
from sportsprediction.data.db import get_session
from sportsprediction.data.models import (
    Game, BoxScore, Team, PlayerRollingStats
)

# Windows to use for features
WINDOWS = [5, 10, 20]
STATS = ["points", "rebounds", "assists", "steals", "blocks", "turnovers", "fg_pct", "minutes"]


def compute_game_features(session, game_id: str) -> dict:
    """Compute features for a single game.
    
    Returns dict with:
    - home_team_* : home team rolling averages
    - away_team_* : away team rolling averages  
    - home_player_* : top home players avg stats
    - away_player_* : top away players avg stats
    - target: 1 if home team wins, 0 otherwise
    """
    game = session.query(Game).filter_by(game_id=game_id).first()
    if not game:
        return None
    
    features = {
        "game_id": game_id,
        "game_date": game.game_date,
        "home_team_id": game.home_team_id,
        "away_team_id": game.away_team_id,
        "home_score": game.home_score,
        "away_score": game.away_score,
        "target": 1 if game.home_score > game.away_score else 0,
    }
    
    # Get box scores for this game
    box_scores = session.query(BoxScore).filter_by(game_id=game_id).all()
    
    home_bs = [bs for bs in box_scores if bs.team_id == game.home_team_id]
    away_bs = [bs for bs in box_scores if bs.team_id == game.away_team_id]
    
    # Team-level: sum of stats from box scores
    for prefix, bs_list in [("home", home_bs), ("away", away_bs)]:
        features[f"{prefix}_total_points"] = sum(bs.points or 0 for bs in bs_list)
        features[f"{prefix}_total_rebounds"] = sum(bs.rebounds or 0 for bs in bs_list)
        features[f"{prefix}_total_assists"] = sum(bs.assists or 0 for bs in bs_list)
    
    # Player-level: get rolling stats for key players (top 5 by minutes)
    for prefix, bs_list in [("home", home_bs), ("away", away_bs)]:
        # Sort by minutes played
        sorted_bs = sorted(bs_list, key=lambda x: x.minutes or 0, reverse=True)[:5]
        
        # Get rolling stats for each player
        rolling_stats = []
        for bs in sorted_bs:
            roll = session.query(PlayerRollingStats).filter_by(
                player_id=bs.player_id, game_id=game_id
            ).first()
            if roll:
                rolling_stats.append(roll)
        
        # Average rolling stats across top 5 players
        if rolling_stats:
            for stat in STATS:
                vals = []
                for w in WINDOWS:
                    col = f"{stat}_avg_{w}"
                    vals.append(np.mean([getattr(r, col, None) for r in rolling_stats if getattr(r, col, None) is not None]))
                features[f"{prefix}_player_{stat}_avg"] = np.mean([v for v in vals if v is not None and not np.isnan(v)] or [0])
    
    return features


def build_dataset(session, season: str = "2024-25") -> pd.DataFrame:
    """Build training dataset for a season."""
    # Get all games in season
    games = session.query(Game).filter_by(season=season).order_by(Game.game_date).all()
    print(f"Building dataset for {len(games)} games in {season}...")
    
    features_list = []
    for i, game in enumerate(games):
        if i % 100 == 0:
            print(f"  Processing game {i+1}/{len(games)}...")
        
        # Only use games where we have rolling stats computed
        # (skip first ~20 games of season as they won't have full rolling window)
        feats = compute_game_features(session, game.game_id)
        if feats and feats.get("home_player_points_avg", 0) > 0:
            features_list.append(feats)
    
    df = pd.DataFrame(features_list)
    print(f"Built dataset with {len(df)} games")
    return df


def compute_rolling_for_all_players(session, season: str):
    """Compute rolling stats for all players who played in this season."""
    print("Computing rolling stats...")
    
    # Get all unique player_ids who played this season
    player_ids = (
        session.query(BoxScore.player_id)
        .join(Game, BoxScore.game_id == Game.game_id)
        .filter(Game.season == season)
        .distinct()
        .all()
    )
    player_ids = [p[0] for p in player_ids]
    print(f"  Found {len(player_ids)} players in {season}")
    
    # Import and run rolling stats computation
    from sportsprediction.data.features.rolling import compute_rolling_stats
    
    for i, pid in enumerate(player_ids):
        if i % 50 == 0:
            print(f"  Processing player {i+1}/{len(player_ids)}...")
        compute_rolling_stats(session, player_id=pid)
        session.commit()
    
    print("Rolling stats computation complete!")


if __name__ == "__main__":
    engine = create_db_engine("data/hermes.db")
    
    with get_session(engine) as session:
        # First, compute rolling stats for all players in 2024-25
        compute_rolling_for_all_players(session, "2024-25")
        
        # Then build dataset
        df = build_dataset(session, "2024-25")
        
        # Save to CSV for inspection
        df.to_csv("data/poc_training_data.csv", index=False)
        print(f"\nDataset saved to data/poc_training_data.csv")
        print(f"Columns: {list(df.columns)}")
        print(f"\nFirst few rows:")
        print(df.head())
