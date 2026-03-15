"""Enhanced POC training - all features: rest days, H2H, players, home advantage.

Features:
1. Team rolling averages (pts, ast, reb) - 10 game window
2. Rest days - days since last game (B2B = 1)
3. Head-to-head - historical record between these teams
4. Player-level - top 5 players' avg stats
5. Home advantage - ~3% boost (domain knowledge, applied to team 1)
"""

import numpy as np
import pandas as pd
from collections import defaultdict
from sportsprediction.data.models.base import create_db_engine
from sportsprediction.data.db import get_session
from sportsprediction.data.models import Game, BoxScore
from sqlalchemy import func


# Domain knowledge: Home court advantage is ~3% win rate boost
# In terms of scoring, home teams average ~2-3 more points
HOME_COURT_PTS_ADVANTAGE = 2.5


def build_enhanced_features(session) -> pd.DataFrame:
    """Build dataset with all features."""
    print("Loading base game data...")
    
    # Get all games with team scores
    game_teams = session.query(
        BoxScore.game_id,
        BoxScore.team_id,
        func.sum(BoxScore.points).label('pts'),
    ).group_by(BoxScore.game_id, BoxScore.team_id).all()
    
    game_dates = {g.game_id: g.game_date for g in session.query(Game).all()}
    
    # Build games data
    games_data = defaultdict(dict)
    for game_id, team_id, pts in game_teams:
        if game_id in game_dates:
            games_data[game_id][team_id] = float(pts)
    
    valid = {k: v for k, v in games_data.items() if len(v) == 2}
    sorted_games = sorted(valid.keys())
    
    print(f"Processing {len(valid)} games...")
    
    # Precompute: team rolling stats
    print("  Computing team rolling stats...")
    team_stats = compute_team_rolling(session, sorted_games, valid, game_dates)
    
    # Precompute: rest days
    print("  Computing rest days...")
    rest_days = compute_rest_days(session, sorted_games, valid, game_dates)
    
    # Precompute: head-to-head
    print("  Computing head-to-head...")
    h2h_stats = compute_h2h(session, sorted_games, valid, game_dates)
    
    # Precompute: player-level
    print("  Computing player-level stats...")
    player_stats = compute_player_stats(session, sorted_games, valid)
    
    # Precompute: momentum
    print("  Computing momentum...")
    momentum = compute_momentum(session, sorted_games, valid)
    
    # Build feature matrix
    print("  Building features...")
    features = []
    
    for i, gid in enumerate(sorted_games):
        if i % 1000 == 0:
            print(f"    Game {i}/{len(sorted_games)}")
        
        teams = valid[gid]
        tids = list(teams.keys())
        t1_id, t2_id = tids[0], tids[1]
        t1_pts, t2_pts = teams[t1_id], teams[t2_id]
        
        # Get features
        t1_roll = team_stats.get((t1_id, gid), {})
        t2_roll = team_stats.get((t2_id, gid), {})
        
        t1_rest = rest_days.get((t1_id, gid), 3)
        t2_rest = rest_days.get((t2_id, gid), 3)
        
        h2h = h2h_stats.get((t1_id, t2_id), {})
        
        t1_players = player_stats.get((t1_id, gid), {})
        t2_players = player_stats.get((t2_id, gid), {})
        
        # Skip if missing core features
        if not t1_roll or not t2_roll:
            continue
        
        # Target: did team 1 win?
        target = 1 if t1_pts > t2_pts else 0
        
        # Feature: is this a B2B? (rest = 1)
        t1_b2b = 1 if t1_rest == 1 else 0
        t2_b2b = 1 if t2_rest == 1 else 0
        
        # Feature: home advantage (we apply to team 1 as domain knowledge)
        # In reality we'd need home/away from the data
        t1_home_bonus = HOME_COURT_PTS_ADVANTAGE
        t2_home_bonus = 0  # No way to know for team 2 without home/away
        
        f = {
            "game_id": gid,
            "game_date": game_dates.get(gid),
            "t1_team_id": t1_id,
            "t2_team_id": t2_id,
            "t1_pts": t1_pts,
            "t2_pts": t2_pts,
            "target": target,
            
            # Team rolling averages
            "t1_avg_pts": t1_roll.get("avg_pts", 0),
            "t1_avg_ast": t1_roll.get("avg_ast", 0),
            "t1_avg_reb": t1_roll.get("avg_reb", 0),
            "t2_avg_pts": t2_roll.get("avg_pts", 0),
            "t2_avg_ast": t2_roll.get("avg_ast", 0),
            "t2_avg_reb": t2_roll.get("avg_reb", 0),
            
            # Differentials
            "pt_diff": t1_roll.get("avg_pts", 0) - t2_roll.get("avg_pts", 0),
            "ast_diff": t1_roll.get("avg_ast", 0) - t2_roll.get("avg_ast", 0),
            "reb_diff": t1_roll.get("avg_reb", 0) - t2_roll.get("avg_reb", 0),
            
            # Rest days
            "t1_rest_days": t1_rest,
            "t2_rest_days": t2_rest,
            "t1_b2b": t1_b2b,
            "t2_b2b": t2_b2b,
            "rest_advantage": t2_rest - t1_rest,  # Positive = t1 more rested
            
            # Head-to-head
            "t1_h2h_wins": h2h.get("t1_wins", 0),
            "t2_h2h_wins": h2h.get("t2_wins", 0),
            "h2h_games": h2h.get("games", 0),
            "h2h_win_pct": h2h.get("t1_win_pct", 0.5),
            
            # Player-level
            "t1_top_player_pts": t1_players.get("top_pts", 0),
            "t2_top_player_pts": t2_players.get("top_pts", 0),
            "t1_top3_pts": t1_players.get("top3_pts", 0),
            "t2_top3_pts": t2_players.get("top3_pts", 0),
            
            # Momentum
            "t1_momentum": momentum.get((t1_id, gid), {}).get("team_momentum", 0),
            "t2_momentum": momentum.get((t2_id, gid), {}).get("team_momentum", 0),
            "t1_hot_players": momentum.get((t1_id, gid), {}).get("hot_players", 0),
            "t2_hot_players": momentum.get((t2_id, gid), {}).get("hot_players", 0),
            "momentum_diff": (
                momentum.get((t1_id, gid), {}).get("team_momentum", 0) -
                momentum.get((t2_id, gid), {}).get("team_momentum", 0)
            ),
            
            # Home advantage (domain knowledge - applied to t1)
            "t1_home_advantage": t1_home_bonus,
            "t2_home_advantage": t2_home_bonus,
        }
        
        features.append(f)
    
    return pd.DataFrame(features)


def compute_team_rolling(session, sorted_games, valid, game_dates, window=10):
    """Compute rolling averages for each team before each game."""
    # Get all box scores with dates
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
    
    # Group by team
    team_games = defaultdict(list)
    for team_id, game_id, game_date, pts, ast, reb in bs_data:
        team_games[team_id].append({
            "game_id": game_id,
            "game_date": game_date,
            "pts": pts or 0,
            "ast": ast or 0,
            "reb": reb or 0,
        })
    
    # Compute rolling
    rolling = {}
    for team_id, games in team_games.items():
        game_idx = {g["game_id"]: i for i, g in enumerate(games)}
        
        for i, game in enumerate(games):
            gid = game["game_id"]
            start = max(0, i - window)
            prior = games[start:i]
            
            if len(prior) >= 3:
                rolling[(team_id, gid)] = {
                    "avg_pts": np.mean([g["pts"] for g in prior]),
                    "avg_ast": np.mean([g["ast"] for g in prior]),
                    "avg_reb": np.mean([g["reb"] for g in prior]),
                }
    
    return rolling


def compute_rest_days(session, sorted_games, valid, game_dates):
    """Compute days since each team's last game."""
    team_last_date = {}
    rest = {}
    
    for gid in sorted_games:
        if gid not in game_dates:
            continue
        date = game_dates[gid]
        
        for team_id in valid[gid].keys():
            if team_id in team_last_date:
                last_date = team_last_date[team_id]
                days = (date - last_date).days
                # Sanity check: ignore unrealistic values (offseason, errors)
                if 0 < days < 30:  # Within a month
                    rest[(team_id, gid)] = days
            
            team_last_date[team_id] = date
    
    return rest


def compute_h2h(session, sorted_games, valid, game_dates):
    """Compute head-to-head record between team pairs."""
    h2h = defaultdict(lambda: {"t1_wins": 0, "t2_wins": 0, "games": 0})
    
    for gid in sorted_games:
        teams = valid[gid]
        tids = sorted(teams.keys())
        pair = (tids[0], t1_id := tids[1])
        
        # Determine winner
        if teams[tids[0]] > teams[tids[1]]:
            h2h[pair]["t1_wins"] += 1
        else:
            h2h[pair]["t2_wins"] += 1
        h2h[pair]["games"] += 1
    
    # Compute win percentages (for team 1 perspective)
    h2h_pct = {}
    for pair, stats in h2h.items():
        total = stats["games"]
        t1_pct = stats["t1_wins"] / total if total > 0 else 0.5
        h2h_pct[pair] = {
            "t1_wins": stats["t1_wins"],
            "t2_wins": stats["t2_wins"],
            "games": total,
            "t1_win_pct": t1_pct,
        }
    
    return h2h_pct


def compute_player_stats(session, sorted_games, valid):
    """Compute player-level features (top performers)."""
    # Get player stats per game
    player_game_stats = session.query(
        BoxScore.game_id,
        BoxScore.team_id,
        BoxScore.player_id,
        BoxScore.points,
    ).all()
    
    # Group by (team, game)
    team_game_players = defaultdict(list)
    for gid, team_id, player_id, pts in player_game_stats:
        team_game_players[(team_id, gid)].append(pts or 0)
    
    # For each team-game, get top players
    player_top = {}
    for (team_id, gid), pts_list in team_game_players.items():
        pts_list.sort(reverse=True)
        player_top[(team_id, gid)] = {
            "top_pts": pts_list[0] if pts_list else 0,
            "top3_pts": sum(pts_list[:3]) / min(3, len(pts_list)) if pts_list else 0,
        }
    
    return player_top


def compute_momentum(session, sorted_games, valid) -> dict:
    """Compute team momentum from player performance trends.
    
    Returns: {(team_id, game_id): {"momentum": float, "hot_players": int}}
    - momentum: average momentum score of top 5 players (-10 to +10)
    - hot_players: count of players with positive momentum
    """
    print("  Computing momentum...")
    
    # Get player points per game - ordered by date
    player_game_pts = (
        session.query(
            BoxScore.player_id,
            BoxScore.team_id,
            Game.game_id,  # Get game_id from join
            BoxScore.points,
        )
        .join(Game, BoxScore.game_id == Game.game_id)
        .order_by(BoxScore.player_id, Game.game_date.asc())
        .all()
    )
    
    # Group by team -> player -> list of (game_id, points)
    player_games = defaultdict(lambda: defaultdict(list))
    for pid, tid, gid, pts in player_game_pts:
        if pts and pts > 0:
            player_games[tid][pid].append((gid, pts))
    
    # Compute momentum for each team-game
    momentum = {}
    for team_id, players in player_games.items():
        for player_id, games in players.items():
            if len(games) < 10:
                continue
            
            # Compare recent 5 games to prior 5 games
            recent_5 = games[-5:]  # List of (gid, pts)
            prior_5 = games[-10:-5]
            
            recent = [g[1] for g in recent_5]
            prior = [g[1] for g in prior_5]
            
            if len(prior) < 3 or len(recent) < 3:
                continue
            
            recent_avg = sum(recent) / len(recent)
            prior_avg = sum(prior) / len(prior)
            
            if prior_avg > 0:
                player_momentum = ((recent_avg - prior_avg) / prior_avg) * 10
                
                # Assign to each game in the "recent" window
                for gid, pts in recent_5:
                    key = (team_id, gid)
                    if key not in momentum:
                        momentum[key] = {"scores": [], "hot": 0}
                    momentum[key]["scores"].append(player_momentum)
                    if player_momentum > 0:
                        momentum[key]["hot"] += 1
    
    # Aggregate to team level
    result = {}
    for (tid, gid), data in momentum.items():
        scores = data["scores"]
        result[(tid, gid)] = {
            "team_momentum": sum(scores) / len(scores) if scores else 0,
            "hot_players": data["hot"],
        }
    
    return result


if __name__ == "__main__":
    engine = create_db_engine("data/hermes.db")
    
    with get_session(engine) as session:
        df = build_enhanced_features(session)
        
        # Save
        df.to_csv("data/poc_training_data_v2.csv", index=False)
        
        print(f"\n=== Dataset ===")
        print(f"Shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        print(f"\nFeatures included:")
        print("  - Team rolling averages (pts, ast, reb)")
        print("  - Rest days (t1_rest_days, t2_rest_days)")
        print("  - B2B indicator (t1_b2b, t2_b2b)")
        print("  - Head-to-head (h2h_win_pct)")
        print("  - Player-level (t1_top_player_pts)")
        print("  - Momentum (t1_momentum, hot_players)")
        print("  - Home advantage (domain knowledge)")
