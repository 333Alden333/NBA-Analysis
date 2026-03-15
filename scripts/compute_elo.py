"""Standalone ELO Rating System for NBA teams.

Separate from the ML model - computes and stores ELO ratings.
Can be queried independently or displayed with predictions.
"""

import numpy as np
import pandas as pd
from collections import defaultdict
from sportsprediction.data.models.base import create_db_engine
from sportsprediction.data.db import get_session
from sportsprediction.data.models import Game, BoxScore, Team
from sqlalchemy import func
import json


# ELO Constants
INITIAL_ELO = 1500
K_FACTOR = 32  # Standard for chess, works for NBA too
HOME_COURT_ADVANTAGE = 100  # ELO points for home court


def compute_elo_ratings(session, output_path: str = "data/elo_ratings.json"):
    """Compute ELO ratings for all teams based on game history.
    
    Returns dict: {team_id: {"elo": float, "wins": int, "losses": int, "last_game": date}}
    """
    print("Computing ELO ratings...")
    
    # Get all games with scores
    game_teams = session.query(
        BoxScore.game_id,
        BoxScore.team_id,
        func.sum(BoxScore.points).label('pts'),
    ).group_by(BoxScore.game_id, BoxScore.team_id).all()
    
    # Get game dates
    game_dates = {g.game_id: g.game_date for g in session.query(Game).all()}
    
    # Build games: {game_id: {team_id: points}}
    games_data = defaultdict(dict)
    for game_id, team_id, pts in game_teams:
        if game_id in game_dates:
            games_data[game_id][team_id] = float(pts)
    
    # Filter to valid games (2 teams)
    valid_games = {k: v for k, v in games_data.items() if len(v) == 2}
    sorted_games = sorted(valid_games.keys())
    
    print(f"  Processing {len(valid_games)} games...")
    
    # Initialize ratings
    team_elo = defaultdict(lambda: INITIAL_ELO)
    team_wins = defaultdict(int)
    team_losses = defaultdict(int)
    team_last_game = {}
    
    # Process each game chronologically
    for i, gid in enumerate(sorted_games):
        if i % 1000 == 0:
            print(f"    Game {i}/{len(sorted_games)}")
        
        teams = valid_games[gid]
        tids = list(teams.keys())
        t1_id, t2_id = tids[0], tids[1]
        t1_pts, t2_pts = teams[t1_id], teams[t2_id]
        
        # Determine winner
        if t1_pts > t2_pts:
            winner, loser = t1_id, t2_id
            t1_result, t2_result = 1, 0
        elif t2_pts > t1_pts:
            winner, loser = t2_id, t1_id
            t1_result, t2_result = 0, 1
        else:
            # Tie - rare in NBA, treat as 0.5 each
            t1_result, t2_result = 0.5, 0.5
            winner, loser = None, None
        
        # Get current ELOs
        t1_elo = team_elo[t1_id]
        t2_elo = team_elo[t2_id]
        
        # Expected scores
        e1 = expected_score(t1_elo, t2_elo)
        e2 = expected_score(t2_elo, t1_elo)
        
        # Update ELOs (no home court in this data)
        new_t1 = t1_elo + K_FACTOR * (t1_result - e1)
        new_t2 = t2_elo + K_FACTOR * (t2_result - e2)
        
        team_elo[t1_id] = new_t1
        team_elo[t2_id] = new_t2
        
        # Update win/loss
        if winner:
            team_wins[winner] += 1
            team_losses[loser] += 1
        
        # Update last game date
        if gid in game_dates:
            team_last_game[t1_id] = game_dates[gid]
            team_last_game[t2_id] = game_dates[gid]
    
    # Build final ratings
    ratings = {}
    for team_id in team_elo:
        ratings[int(team_id)] = {
            "elo": round(team_elo[team_id], 1),
            "wins": team_wins[team_id],
            "losses": team_losses[team_id],
            "games": team_wins[team_id] + team_losses[team_id],
            "win_pct": round(team_wins[team_id] / (team_wins[team_id] + team_losses[team_id]) * 100, 1) 
                      if (team_wins[team_id] + team_losses[team_id]) > 0 else 50.0,
            "last_game": str(team_last_game.get(team_id, "")),
        }
    
    # Save to JSON
    with open(output_path, "w") as f:
        json.dump(ratings, f, indent=2)
    
    print(f"  Computed ratings for {len(ratings)} teams")
    print(f"  ELO range: {min(r['elo'] for r in ratings.values()):.0f} - {max(r['elo'] for r in ratings.values()):.0f}")
    
    return ratings


def expected_score(rating_a, rating_b):
    """Calculate expected score for player A vs player B."""
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def get_team_elo(team_id: int, ratings_path: str = "data/elo_ratings.json") -> dict:
    """Get ELO rating for a specific team."""
    try:
        with open(ratings_path) as f:
            ratings = json.load(f)
        return ratings.get(str(team_id), ratings.get(team_id, {"elo": INITIAL_ELO, "wins": 0, "losses": 0, "games": 0}))
    except FileNotFoundError:
        return {"elo": INITIAL_ELO, "wins": 0, "losses": 0, "games": 0}


def predict_with_elo(t1_id: int, t2_id: int, ratings_path: str = "data/elo_ratings.json") -> dict:
    """Predict using just ELO (no ML model)."""
    t1 = get_team_elo(t1_id, ratings_path)
    t2 = get_team_elo(t2_id, ratings_path)
    
    elo_diff = t1["elo"] - t2["elo"]
    t1_win_prob = expected_score(t1["elo"], t2["elo"])
    
    return {
        "t1_elo": t1["elo"],
        "t2_elo": t2["elo"],
        "elo_diff": elo_diff,
        "t1_win_prob": round(t1_win_prob, 3),
        "t2_win_prob": round(1 - t1_win_prob, 3),
    }


def print_elo_leaders(ratings_path: str = "data/elo_ratings.json", limit: int = 10):
    """Print top teams by ELO."""
    with open(ratings_path) as f:
        ratings = json.load(f)
    
    # Sort by ELO
    sorted_teams = sorted(ratings.items(), key=lambda x: x[1]["elo"], reverse=True)
    
    print(f"\n{'Rank':<5} {'Team ID':<12} {'ELO':<8} {'Record':<15} {'Win%':<6}")
    print("-" * 50)
    
    for i, (team_id, data) in enumerate(sorted_teams[:limit], 1):
        record = f"{data['wins']}-{data['losses']}"
        print(f"{i:<5} {team_id:<12} {data['elo']:<8.0f} {record:<15} {data['win_pct']:.1f}%")


if __name__ == "__main__":
    engine = create_db_engine("data/hermes.db")
    
    with get_session(engine) as session:
        ratings = compute_elo_ratings(session)
    
    print_elo_leaders()
    print("\n✓ ELO ratings saved to data/elo_ratings.json")