"""Ultra-minimal training pipeline for NBA prediction POC.

Fast approach: Compute features on-the-fly from raw box scores.
No precomputation needed - just load raw data and train.
"""

import numpy as np
import pandas as pd
from sportsprediction.data.models.base import create_db_engine
from sportsprediction.data.db import get_session
from sportsprediction.data.models import Game, BoxScore, Team


def get_team_rolling(session, team_id: int, game_id: str, window: int = 10) -> dict:
    """Get team's rolling averages BEFORE this game.
    
    Uses raw box scores to compute on-the-fly.
    """
    # Get all games for this team BEFORE this game
    team_games = (
        session.query(Game)
        .filter(
            Game.game_id == game_id
        )
        .first()
    )
    if not team_games:
        return {}
    
    # Get all box scores for this team in prior games
    prior_bs = (
        session.query(BoxScore)
        .join(Game, BoxScore.game_id == Game.game_id)
        .filter(
            BoxScore.team_id == team_id,
            Game.game_date < team_games.game_date
        )
        .order_by(Game.game_date.desc())
        .limit(window)
        .all()
    )
    
    if not prior_bs:
        return {}
    
    return {
        "avg_points": np.mean([bs.points or 0 for bs in prior_bs]),
        "avg_rebounds": np.mean([bs.rebounds or 0 for bs in prior_bs]),
        "avg_assists": np.mean([bs.assists or 0 for bs in prior_bs]),
        "avg_fg_pct": np.mean([
            (bs.fgm / bs.fga) if (bs.fga and bs.fga > 0) else 0 
            for bs in prior_bs
        ]),
    }


def build_dataset_fast(session, min_games: int = 10) -> pd.DataFrame:
    """Build dataset quickly using on-the-fly feature computation."""
    
    # Get all games with scores (finalized)
    games = (
        session.query(Game)
        .filter(Game.home_score.isnot(None))
        .order_by(Game.game_date)
        .all()
    )
    
    print(f"Processing {len(games)} games...")
    
    features_list = []
    for i, game in enumerate(games):
        if i % 500 == 0:
            print(f"  Game {i+1}/{len(games)}...")
        
        # Skip first few games of each season (not enough history)
        if game.game_date.month == 10 and game.game_date.day < 25:
            continue
        
        # Get team rolling stats BEFORE this game
        home_roll = get_team_rolling(session, game.home_team_id, game.game_id, 10)
        away_roll = get_team_rolling(session, game.away_team_id, game.game_id, 10)
        
        if not home_roll or not away_roll:
            continue
        
        # Also get this season's record
        season_games = (
            session.query(Game)
            .filter(
                Game.season == game.season,
                Game.game_date < game.game_date,
                or_(
                    Game.home_team_id == game.home_team_id,
                    Game.away_team_id == game.home_team_id
                )
            )
            .all()
        )
        
        home_wins = 0
        home_losses = 0
        for sg in season_games:
            if sg.home_team_id == game.home_team_id:
                if sg.home_score > sg.away_score:
                    home_wins += 1
                else:
                    home_losses += 1
            else:
                if sg.away_score > sg.home_score:
                    home_wins += 1
                else:
                    home_losses += 1
        
        features = {
            "game_id": game.game_id,
            "game_date": game.game_date,
            "season": game.season,
            # Target
            "home_win": 1 if game.home_score > game.away_score else 0,
            # Home team rolling
            "home_avg_points": home_roll.get("avg_points", 0),
            "home_avg_rebounds": home_roll.get("avg_rebounds", 0),
            "home_avg_assists": home_roll.get("avg_assists", 0),
            "home_avg_fg_pct": home_roll.get("avg_fg_pct", 0),
            # Away team rolling
            "away_avg_points": away_roll.get("avg_points", 0),
            "away_avg_rebounds": away_roll.get("avg_rebounds", 0),
            "away_avg_assists": away_roll.get("avg_assists", 0),
            "away_avg_fg_pct": away_roll.get("avg_fg_pct", 0),
            # Season record
            "home_wins": home_wins,
            "home_losses": home_losses,
            "home_win_pct": home_wins / (home_wins + home_losses) if (home_wins + home_losses) > 0 else 0.5,
            # Point differential
            "home_pt_diff": home_roll.get("avg_points", 0) - away_roll.get("avg_points", 0),
        }
        
        features_list.append(features)
    
    df = pd.DataFrame(features_list)
    print(f"Built dataset with {len(df)} games")
    return df


from sqlalchemy import or_


if __name__ == "__main__":
    engine = create_db_engine("data/hermes.db")
    
    with get_session(engine) as session:
        df = build_dataset_fast(session)
        
        # Save for training
        df.to_csv("data/poc_training_data.csv", index=False)
        
        print(f"\nDataset shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        print(f"\nTarget distribution:\n{df['home_win'].value_counts()}")
        print(f"\nSample:")
        print(df.head())
