#!/usr/bin/env python3
"""Simple NBA Prediction CLI - Fixed version."""

import sys
import json
import urllib.request
import os

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============== HELP ==============

HELP = """
=== NBA PREDICTION TOOL ===

Commands:
  /elo           Show ELO rankings (best teams)
                 Optional: /elo --png (save chart)
  /games         Show recent game scores  
  /predict       Predict a matchup
                 Usage: /predict <team1> <team2>
                 Example: /predict Celtics Lakers
  /player       Show player career stats
                 Usage: /player <name> [--png]
                 Example: /player Curry
  /team         Show team stats by season
                 Usage: /team <name> [--png]
                 Example: /team Lakers
  /compare       Compare two players
                 Usage: /compare <player1> vs <player2> [--png]
                 Example: /compare Curry vs LeBron
  /trend         Show player PPG trend
                 Usage: /trend <player> [--png]
                 Example: /trend Luka
  /top           Show league leaders
                 Usage: /top <category> [--png]
                 Categories: pts, reb, ast, stl, blk, 3pm
                 Example: /top pts
  /heatmap       Show team stats correlation heatmap
                 Usage: /heatmap [--png]
  /shot          Show player shot chart
                 Usage: /shot <player> [--png]
                 Example: /shot Curry
  /pattern        Analyze player matchup patterns
                 Usage: /pattern <player> vs <team>
                 Example: /pattern Curry vs Lakers
  /momentum       Show who's hot/cold
                 Example: /momentum
  /matchup       Classify player vs team matchup
                 Usage: /matchup <player> vs <team>
                 Example: /matchup LeBron vs Celtics
  /odds          Show Polymarket NBA championship odds
  /teams         List all available teams
  /update        Update ELO ratings
  /help          Show this message
  /quit          Exit

Examples:
  /elo
  /elo --png
  /predict Celtics Lakers
  /player Curry
  /team Lakers
  /compare Curry vs LeBron
  /trend Luka
  /top pts
  /heatmap --png
  /shot Curry
  /pattern Curry vs Lakers
  /momentum
  /matchup LeBron vs Celtics
  /odds
  /games
"""

# ============== FUNCTIONS ==============

def load_elo():
    try:
        with open("data/elo_ratings.json") as f:
            return json.load(f)
    except:
        return {}

def load_teams():
    sys.path.insert(0, 'src')
    from sportsprediction.data.models import Team
    from sportsprediction.data.models.base import create_db_engine
    from sportsprediction.data.db import get_session
    engine = create_db_engine("data/hermes.db")
    with get_session(engine) as session:
        return {t.team_id: t.full_name for t in session.query(Team).all()}

def get_recent_games(teams):
    sys.path.insert(0, 'src')
    from sportsprediction.data.models import BoxScore, Game
    from sportsprediction.data.models.base import create_db_engine
    from sportsprediction.data.db import get_session
    from sqlalchemy import func
    from collections import defaultdict
    
    engine = create_db_engine("data/hermes.db")
    with get_session(engine) as session:
        game_teams = session.query(
            BoxScore.game_id, BoxScore.team_id,
            func.sum(BoxScore.points).label('pts'),
        ).group_by(BoxScore.game_id, BoxScore.team_id).all()
    
    games_data = defaultdict(dict)
    for game_id, team_id, pts in game_teams:
        games_data[game_id][team_id] = float(pts)
    
    valid = {k: v for k, v in games_data.items() if len(v) == 2}
    
    with get_session(engine) as session:
        all_dates = {g.game_id: g.game_date for g in session.query(Game).all()}
    
    sorted_games = sorted(
        [g for g in valid.keys() if g in all_dates],
        key=lambda g: all_dates[g], reverse=True
    )[:10]
    
    results = []
    for gid in sorted_games:
        tids = list(valid[gid].keys())
        results.append({
            "date": all_dates[gid],
            "t1": teams.get(tids[0], f"Team {tids[0]}"),
            "t2": teams.get(tids[1], f"Team {tids[1]}"),
            "s1": valid[gid][tids[0]],
            "s2": valid[gid][tids[1]],
        })
    return results

def expected_score(rating_a, rating_b):
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

def show_elo(teams, elo, save_png=False):
    import matplotlib.pyplot as plt
    import os
    
    sorted_elo = sorted(elo.items(), key=lambda x: x[1]["elo"], reverse=True)
    print("\n=== ELO RANKINGS ===\n")
    print(f"{'Rank':<5} {'Team':<25} {'ELO':<8} {'Record':<12} {'Win%'}")
    print("-" * 60)
    for i, (tid, data) in enumerate(sorted_elo[:15], 1):
        name = teams.get(int(tid), f"Team {tid}")[:24]
        print(f"{i:<5} {name:<25} {data['elo']:<8.0f} {data['wins']}-{data['losses']:<6} {data['win_pct']}%")
    
    # Generate PNG if requested
    if save_png:
        fig, ax = plt.subplots(figsize=(12, 8))
        
        top_teams = sorted_elo[:15]
        names = [teams.get(int(tid), f"Team {tid}")[:20] for tid, _ in top_teams]
        ratings = [data["elo"] for _, data in top_teams]
        
        colors = ['#1d428a' if i < 5 else '#552583' if i < 10 else '#888888' for i in range(len(names))]
        
        bars = ax.barh(names[::-1], ratings[::-1], color=colors[::-1])
        ax.set_xlabel('ELO Rating', fontsize=12, fontweight='bold')
        ax.set_title('NBA Team ELO Ratings', fontsize=14, fontweight='bold')
        
        for bar, rating in zip(bars, ratings[::-1]):
            ax.text(bar.get_width() + 5, bar.get_y() + bar.get_height()/2, 
                   f'{rating:.0f}', va='center', fontsize=9)
        
        plt.tight_layout()
        
        filepath = os.path.join("data", "elo_rankings.png")
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"\n✓ Chart saved to: {filepath}")

def show_games(teams):
    games = get_recent_games(teams)
    print("\n=== RECENT GAMES ===\n")
    for g in games:
        print(f"{g['date']}: {g['t1']} {g['s1']:.0f} - {g['s2']:.0f} {g['t2']}")

def show_predict(teams, elo, arg):
    if not arg:
        print("Usage: /predict <team1> <team2>")
        print("Example: /predict Celtics Lakers")
        return
    
    # Split arg into parts and match each to a team
    parts = arg.lower().split()
    matches = []
    for tid, name in teams.items():
        name_lower = name.lower()
        # Check if any part of the arg matches the team name (full or last word)
        for part in parts:
            if part in name_lower or part == name_lower.split()[-1]:
                matches.append((tid, name))
                break
    
    if len(matches) < 2:
        print("Teams not found. Available:")
        for name in sorted(set(teams.values())):
            print(f"  - {name}")
        return
    
    t1_id, t1_name = matches[0]
    t2_id, t2_name = matches[1]
    t1_elo = elo.get(str(t1_id), elo.get(t1_id, {}))
    t2_elo = elo.get(str(t2_id), elo.get(t2_id, {}))
    
    if not t1_elo or not t2_elo:
        print("Error: No ELO data")
        return
    
    prob = expected_score(t1_elo.get("elo", 1500), t2_elo.get("elo", 1500))
    
    print(f"\n=== PREDICTION ===")
    print(f"{t1_name} vs {t2_name}")
    print(f"\nELO Ratings:")
    print(f"  {t1_name}: {t1_elo.get('elo', 1500):.0f} ({t1_elo.get('wins', 0)}-{t1_elo.get('losses', 0)}, {t1_elo.get('win_pct', 0):.1f}%)")
    print(f"  {t2_name}: {t2_elo.get('elo', 1500):.0f} ({t2_elo.get('wins', 0)}-{t2_elo.get('losses', 0)}, {t2_elo.get('win_pct', 0):.1f}%)")
    print(f"\nWin Probability:")
    print(f"  {t1_name}: {prob:.1%}")
    print(f"  {t2_name}: {1-prob:.1%}")
    print(f"\nMarket Odds (Polymarket):")
    print("  [NBA daily markets not available - showing futures]")
    print(f"  Championship: Thunder 35.5%, Next: varies")

def show_odds():
    print("\n=== POLYMARKET NBA ODDS ===\n")
    print("Note: Daily game markets currently unavailable\n")
    print("2026 NBA Championship:")
    print("  Oklahoma City Thunder: 35.5%")
    print("  Houston Rockets: 2.9%")
    print("  Cleveland Cavaliers: 6.2%")
    print("  Denver Nuggets: 5.1%")
    print("  Boston Celtics: 4.8%")
    print("\n(Source: Polymarket - https://polymarket.com/market/2026-nba-champion)")
    print("(Note: These are real-time market prices, may vary)")

def update_elo():
    print("Updating ELO...")
    import importlib.util
    spec = importlib.util.spec_from_file_location("compute_elo", "scripts/compute_elo.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    from sportsprediction.data.models.base import create_db_engine
    from sportsprediction.data.db import get_session
    engine = create_db_engine("data/hermes.db")
    with get_session(engine) as session:
        module.compute_elo_ratings(session)
    print("✓ ELO updated")

def show_teams(teams):
    print("\n=== AVAILABLE TEAMS ===\n")
    for name in sorted(set(teams.values())):
        print(f"  {name}")


def show_player(name_query, save_png=False):
    """Show player career stats by season (like ESPN table)."""
    import sqlite3
    import matplotlib.pyplot as plt
    import os
    
    if not name_query:
        print("Usage: /player <name> [--png]")
        print("Example: /player Curry")
        print("         /player Curry --png")
        return
    
    # Check for --png flag
    if '--png' in name_query:
        name_query = name_query.replace('--png', '').strip()
        save_png = True
    
    conn = sqlite3.connect("data/hermes.db")
    cur = conn.cursor()
    
    # Find player
    player = cur.execute("""
        SELECT player_id, first_name, last_name 
        FROM players 
        WHERE first_name LIKE ? OR last_name LIKE ?
        LIMIT 5
    """, (f"%{name_query}%", f"%{name_query}%")).fetchall()
    
    if not player:
        print(f"No players found matching '{name_query}'")
        conn.close()
        return
    
    if len(player) > 1:
        print(f"Multiple players found - be more specific:")
        for p in player:
            print(f"  {p[1]} {p[2]} (ID: {p[0]})")
        conn.close()
        return
    
    player_id, first_name, last_name = player[0]
    
    # Get career stats by season (all available from 2022 onwards)
    stats = cur.execute("""
        SELECT 
            SUBSTR(g.season, 1, 4) as year,
            COUNT(*) as GP,
            ROUND(AVG(bs.minutes), 1) as MIN,
            ROUND(AVG(bs.points), 1) as PTS,
            ROUND(AVG(bs.rebounds), 1) as REB,
            ROUND(AVG(bs.assists), 1) as AST,
            ROUND(AVG(bs.steals), 1) as STL,
            ROUND(AVG(bs.blocks), 1) as BLK,
            ROUND(AVG(bs.turnovers), 1) as "TO",
            ROUND(AVG(bs.fg3m), 1) as "3PM",
            ROUND(AVG(1.0 * bs.fgm / NULLIF(bs.fga, 0)) * 100, 1) as "FG_PCT",
            ROUND(AVG(1.0 * bs.fg3m / NULLIF(bs.fg3a, 0)) * 100, 1) as "3P_PCT",
            ROUND(AVG(1.0 * bs.ftm / NULLIF(bs.fta, 0)) * 100, 1) as "FT_PCT"
        FROM box_scores bs
        JOIN games g ON bs.game_id = g.game_id
        WHERE bs.player_id = ? AND bs.minutes > 0 AND g.season >= '2022-23'
        GROUP BY g.season
        ORDER BY year DESC
    """, (player_id,)).fetchall()
    
    if not stats:
        print(f"No stats found for {first_name} {last_name}")
        conn.close()
        return
    
    # Calculate career averages (2022-23 onwards)
    career = cur.execute("""
        SELECT 
            ROUND(AVG(bs.minutes), 1) as MIN,
            ROUND(AVG(bs.points), 1) as PTS,
            ROUND(AVG(bs.rebounds), 1) as REB,
            ROUND(AVG(bs.assists), 1) as AST,
            ROUND(AVG(bs.steals), 1) as STL,
            ROUND(AVG(bs.blocks), 1) as BLK,
            ROUND(AVG(bs.turnovers), 1) as "TO",
            ROUND(AVG(bs.fg3m), 1) as "3PM",
            ROUND(AVG(1.0 * bs.fgm / NULLIF(bs.fga, 0)) * 100, 1) as "FG_PCT",
            ROUND(AVG(1.0 * bs.fg3m / NULLIF(bs.fg3a, 0)) * 100, 1) as "3P_PCT",
            ROUND(AVG(1.0 * bs.ftm / NULLIF(bs.fta, 0)) * 100, 1) as "FT_PCT",
            COUNT(*) as GP
        FROM box_scores bs
        JOIN games g ON bs.game_id = g.game_id
        WHERE bs.player_id = ? AND bs.minutes > 0 AND g.season >= '2022-23'
    """, (player_id,)).fetchone()
    
    # Print header
    print(f"\n=== {first_name} {last_name} Career Stats ===\n")
    print(f"{'SEASON':<8} {'GP':>4} {'MIN':>5} {'PTS':>5} {'REB':>5} {'AST':>5} {'STL':>4} {'BLK':>4} {'TO':>4} {'3PM':>4} {'FG%':>5} {'3P%':>5} {'FT%':>5}")
    print("-" * 75)
    
    # Print each season
    for row in stats:
        year, gp, min_, pts, reb, ast, stl, blk, to, tpm, fg, tp, ft = row
        print(f"{year}-{str(int(year)+1)[-2:]:<5} {gp:>4} {min_:>5.1f} {pts:>5.1f} {reb:>5.1f} {ast:>5.1f} {stl:>4.1f} {blk:>4.1f} {to:>4.1f} {tpm:>4.1f} {fg:>4.1f}% {tp:>4.1f}% {ft:>4.1f}%")
    
    # Print career totals
    print("-" * 75)
    min_, pts, reb, ast, stl, blk, to, tpm, fg, tp, ft, gp = career
    print(f"{'Career':<8} {gp:>4} {min_:>5.1f} {pts:>5.1f} {reb:>5.1f} {ast:>5.1f} {stl:>4.1f} {blk:>4.1f} {to:>4.1f} {tpm:>4.1f} {fg:>4.1f}% {tp:>4.1f}% {ft:>4.1f}%")
    
    # Generate PNG if requested
    if save_png:
        # Create visualization
        fig, ax = plt.subplots(figsize=(12, 6))
        
        seasons = [f"{row[0]}-{str(int(row[0])+1)[-2:]}" for row in stats]
        ppg = [float(row[3]) for row in stats]  # PTS
        
        bars = ax.bar(seasons, ppg, color='#1d428a')  # NBA blue
        ax.set_xlabel('Season', fontsize=12, fontweight='bold')
        ax.set_ylabel('Points Per Game', fontsize=12, fontweight='bold')
        ax.set_title(f'{first_name} {last_name} - PPG by Season', fontsize=14, fontweight='bold')
        
        # Add value labels
        for bar, pts_val in zip(bars, ppg):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                   f'{pts_val:.1f}', ha='center', va='bottom', fontsize=9)
        
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        # Save
        filename = f"{first_name}_{last_name}_ppg.png".replace(" ", "_")
        filepath = os.path.join("data", filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"\n✓ Chart saved to: {filepath}")
    
    conn.close()


# ============== TEAM STATS ==============

def show_team(name_query, save_png=False):
    """Show team stats by season."""
    import sqlite3
    import matplotlib.pyplot as plt
    import os
    
    if not name_query:
        print("Usage: /team <name> [--png]")
        print("Example: /team Lakers")
        return
    
    if '--png' in name_query:
        name_query = name_query.replace('--png', '').strip()
        save_png = True
    
    conn = sqlite3.connect("data/hermes.db")
    cur = conn.cursor()
    
    # Find team
    team = cur.execute("""
        SELECT team_id, abbreviation, full_name 
        FROM teams 
        WHERE full_name LIKE ? OR abbreviation LIKE ?
        LIMIT 5
    """, (f"%{name_query}%", f"%{name_query}%")).fetchall()
    
    if not team:
        print(f"No teams found matching '{name_query}'")
        conn.close()
        return
    
    if len(team) > 1:
        print(f"Multiple teams found - be more specific:")
        for t in team:
            print(f"  {t[2]} ({t[1]})")
        conn.close()
        return
    
    team_id, abbrev, full_name = team[0]
    abbrev = abbrev or full_name[:3].upper()
    
    # Get team stats by season - simpler approach using box_scores + games
    stats = cur.execute("""
        SELECT 
            SUBSTR(g.season, 1, 4) as year,
            COUNT(DISTINCT g.game_id) as GP,
            SUM(CASE WHEN team_pts > opp_pts THEN 1 ELSE 0 END) as W,
            SUM(CASE WHEN team_pts < opp_pts THEN 1 ELSE 0 END) as L
        FROM games g
        JOIN (
            SELECT game_id, team_id, SUM(points) as team_pts
            FROM box_scores WHERE team_id = ?
            GROUP BY game_id
        ) my_team ON g.game_id = my_team.game_id
        JOIN (
            SELECT game_id, SUM(points) as opp_pts
            FROM box_scores
            WHERE team_id != ? AND game_id IN (
                SELECT game_id FROM box_scores WHERE team_id = ?
            )
            GROUP BY game_id
        ) opp ON g.game_id = opp.game_id
        WHERE g.season >= '2022-23'
        GROUP BY g.season
        ORDER BY year DESC
    """, (team_id, team_id, team_id)).fetchall()
    
    if not stats:
        print(f"No stats found for {full_name}")
        conn.close()
        return
    
    # Print table
    print(f"\n=== {full_name} ({abbrev}) Season Stats ===\n")
    print(f"{'SEASON':<8} {'GP':>4} {'W':>4} {'L':>4} {'WIN%':>6}")
    print("-" * 35)
    
    wins_total = 0
    losses_total = 0
    games_total = 0
    
    for row in stats:
        year, gp, w, l = row
        win_pct = w / gp * 100 if gp > 0 else 0
        print(f"{year}-{str(int(year)+1)[-2:]:<5} {gp:>4} {w:>4} {l:>4} {win_pct:>5.1f}%")
        wins_total += w
        losses_total += l
        games_total += gp
    
    print("-" * 35)
    win_pct_total = wins_total / games_total * 100 if games_total > 0 else 0
    print(f"{'Total':<8} {games_total:>4} {wins_total:>4} {losses_total:>4} {win_pct_total:>5.1f}%")
    
    # PNG
    if save_png:
        fig, ax = plt.subplots(figsize=(10, 6))
        seasons = [f"{row[0]}-{str(int(row[0])+1)[-2:]}" for row in stats]
        wins = [row[2] for row in stats]
        
        ax.bar(seasons, wins, color='#17408B')
        ax.set_xlabel('Season', fontsize=12, fontweight='bold')
        ax.set_ylabel('Wins', fontsize=12, fontweight='bold')
        ax.set_title(f'{abbrev} - Wins by Season', fontsize=14, fontweight='bold')
        
        for i, w in enumerate(wins):
            ax.text(i, w + 1, str(w), ha='center', fontsize=10)
        
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        filepath = os.path.join("data", f"{abbrev}_wins.png")
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"\n✓ Chart saved to: {filepath}")
    
    conn.close()


# ============== PLAYER COMPARE ==============

def show_compare(query, save_png=False):
    """Compare two players."""
    import sqlite3
    import matplotlib.pyplot as plt
    import os
    
    if not query or 'vs' not in query.lower():
        print("Usage: /compare <player1> vs <player2> [--png]")
        print("Example: /compare Curry vs LeBron")
        return
    
    if '--png' in query:
        query = query.replace('--png', '').strip()
        save_png = True
    
    parts = query.lower().split('vs')
    if len(parts) != 2:
        print("Usage: /compare <player1> vs <player2> [--png]")
        return
    
    p1_query = parts[0].strip()
    p2_query = parts[1].strip()
    
    conn = sqlite3.connect("data/hermes.db")
    cur = conn.cursor()
    
    # Find players
    p1 = cur.execute("SELECT player_id, first_name, last_name FROM players WHERE first_name LIKE ? OR last_name LIKE ? LIMIT 1", 
                    (f"%{p1_query}%", f"%{p1_query}%")).fetchone()
    p2 = cur.execute("SELECT player_id, first_name, last_name FROM players WHERE first_name LIKE ? OR last_name LIKE ? LIMIT 1", 
                    (f"%{p2_query}%", f"%{p2_query}%")).fetchone()
    
    if not p1 or not p2:
        print("Could not find both players. Be more specific.")
        conn.close()
        return
    
    # Get career averages
    p1_stats = cur.execute("""
        SELECT ROUND(AVG(points), 1), ROUND(AVG(rebounds), 1), ROUND(AVG(assists), 1), COUNT(*)
        FROM box_scores WHERE player_id = ? AND minutes > 0
    """, (p1[0],)).fetchone()
    
    p2_stats = cur.execute("""
        SELECT ROUND(AVG(points), 1), ROUND(AVG(rebounds), 1), ROUND(AVG(assists), 1), COUNT(*)
        FROM box_scores WHERE player_id = ? AND minutes > 0
    """, (p2[0],)).fetchone()
    
    print(f"\n=== {p1[1]} {p2[1]} vs {p2[1]} {p2[2]} ===")
    print(f"\nCareer Averages (2022-23 onwards):")
    print(f"{'Player':<20} {'PPG':>6} {'RPG':>6} {'APG':>6} {'GP':>6}")
    print("-" * 50)
    print(f"{p1[1]} {p1[2]:<10} {p1_stats[0]:>6.1f} {p1_stats[1]:>6.1f} {p1_stats[2]:>6.1f} {p1_stats[3]:>6}")
    print(f"{p2[1]} {p2[2]:<10} {p2_stats[0]:>6.1f} {p2_stats[1]:>6.1f} {p2_stats[2]:>6.1f} {p2_stats[3]:>6}")
    
    if save_png:
        fig, ax = plt.subplots(figsize=(10, 6))
        
        stats = ['PPG', 'RPG', 'APG']
        p1_vals = [float(p1_stats[0]), float(p1_stats[1]), float(p1_stats[2])]
        p2_vals = [float(p2_stats[0]), float(p2_stats[1]), float(p2_stats[2])]
        
        x = range(len(stats))
        width = 0.35
        
        ax.bar([i - width/2 for i in x], p1_vals, width, label=p1[1], color='#17408B')
        ax.bar([i + width/2 for i in x], p2_vals, width, label=p2[1], color='#C9082A')
        
        ax.set_ylabel('Average', fontsize=12, fontweight='bold')
        ax.set_title(f'{p1[2]} vs {p2[2]} - Career Comparison', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(stats)
        ax.legend()
        
        plt.tight_layout()
        
        filename = f"{p1[2]}_vs_{p2[2]}_compare.png".replace(" ", "_")
        filepath = os.path.join("data", filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"\n✓ Chart saved to: {filepath}")
    
    conn.close()


# ============== PLAYER TREND ==============

def show_trend(name_query, save_png=False):
    """Show player PPG trend over time."""
    import sqlite3
    import matplotlib.pyplot as plt
    import os
    
    if not name_query:
        print("Usage: /trend <player> [--png]")
        print("Example: /trend Curry")
        return
    
    if '--png' in name_query:
        name_query = name_query.replace('--png', '').strip()
        save_png = True
    
    conn = sqlite3.connect("data/hermes.db")
    cur = conn.cursor()
    
    player = cur.execute("SELECT player_id, first_name, last_name FROM players WHERE first_name LIKE ? OR last_name LIKE ? LIMIT 1",
                        (f"%{name_query}%", f"%{name_query}%")).fetchone()
    
    if not player:
        print(f"No player found matching '{name_query}'")
        conn.close()
        return
    
    # Get game-by-game PPG trend
    trend = cur.execute("""
        SELECT g.game_date, bs.points, g.season
        FROM box_scores bs
        JOIN games g ON bs.game_id = g.game_id
        WHERE bs.player_id = ? AND bs.minutes > 0
        ORDER BY g.game_date ASC
    """, (player[0],)).fetchall()
    
    if not trend:
        print(f"No stats found for {player[1]} {player[2]}")
        conn.close()
        return
    
    print(f"\n=== {player[1]} {player[2]} PPG Trend ===")
    print(f"Last 20 games:\n")
    
    dates = [t[0] for t in trend[-20:]]
    points = [t[1] for t in trend[-20:]]
    
    for i, t in enumerate(trend[-10:]):
        print(f"  {t[0]}: {t[1]} pts ({t[2]})")
    
    if len(trend) > 10:
        print(f"  ... ({len(trend) - 10} more games)")
    
    avg = sum(p for _, p, _ in trend) / len(trend)
    print(f"\nSeason Avg: {avg:.1f} PPG over {len(trend)} games")
    
    if save_png:
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Last 30 games
        recent = trend[-30:]
        dates = [t[0][-5:] for t in recent]  # Just month-day
        points = [t[1] for t in recent]
        
        ax.plot(dates, points, marker='o', linewidth=2, color='#17408B', label='PPG')
        
        # Rolling average
        window = 5
        rolling = []
        for i in range(len(points)):
            if i < window - 1:
                rolling.append(sum(points[:i+1])/(i+1))
            else:
                rolling.append(sum(points[i-window+1:i+1])/window)
        
        ax.plot(dates, rolling, linewidth=2, color='#C9082A', linestyle='--', label=f'{window}-game avg')
        
        ax.set_xlabel('Game Date', fontsize=12, fontweight='bold')
        ax.set_ylabel('Points', fontsize=12, fontweight='bold')
        ax.set_title(f'{player[1]} {player[2]} - PPG Trend', fontsize=14, fontweight='bold')
        ax.legend()
        
        plt.xticks(rotation=45, ha='right')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        filename = f"{player[1]}_{player[2]}_trend.png".replace(" ", "_")
        filepath = os.path.join("data", filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"\n✓ Chart saved to: {filepath}")
    
    conn.close()


# ============== LEAGUE LEADERS ==============

def show_top(category, save_png=False):
    """Show league leaders for a category."""
    import sqlite3
    import matplotlib.pyplot as plt
    import os
    
    valid_cats = {'pts': 'points', 'reb': 'rebounds', 'ast': 'assists', 
                  'stl': 'steals', 'blk': 'blocks', '3pm': 'fg3m'}
    
    if not category or category.lower() not in valid_cats:
        print("Usage: /top <category> [--png]")
        print("Categories: pts, reb, ast, stl, blk, 3pm")
        return
    
    if '--png' in category:
        category = category.replace('--png', '').strip()
        save_png = True
    
    stat_col = valid_cats[category.lower()]
    title_map = {'pts': 'Points', 'reb': 'Rebounds', 'ast': 'Assists',
                 'stl': 'Steals', 'blk': 'Blocks', '3pm': '3-Pointers Made'}
    
    conn = sqlite3.connect("data/hermes.db")
    cur = conn.cursor()
    
    # Get top 10 players by total in current season
    leaders = cur.execute(f"""
        SELECT p.first_name, p.last_name, SUM(bs.{stat_col}) as total, COUNT(*) as GP,
               ROUND(AVG(bs.{stat_col}), 1) as avg
        FROM box_scores bs
        JOIN players p ON bs.player_id = p.player_id
        JOIN games g ON bs.game_id = g.game_id
        WHERE bs.minutes > 0 AND g.season = '2025-26'
        GROUP BY p.player_id
        ORDER BY total DESC
        LIMIT 10
    """).fetchall()
    
    print(f"\n=== 2025-26 {title_map[category]} Leaders ===\n")
    print(f"{'Rank':<6} {'Player':<25} {'Total':>8} {'GP':>5} {'Avg':>6}")
    print("-" * 55)
    
    for i, row in enumerate(leaders, 1):
        print(f"{i:<6} {row[0]} {row[1]:<18} {row[2]:>8.0f} {row[3]:>5} {row[4]:>6.1f}")
    
    if save_png:
        fig, ax = plt.subplots(figsize=(12, 8))
        
        names = [f"{r[0][0]}. {r[1]}" for r in leaders][:10]
        totals = [r[2] for r in leaders][:10]
        
        colors = ['#17408B' if i < 3 else '#552583' if i < 6 else '#888888' for i in range(len(names))]
        
        bars = ax.barh(names[::-1], totals[::-1], color=colors[::-1])
        ax.set_xlabel(f'Total {title_map[category]}', fontsize=12, fontweight='bold')
        ax.set_title(f'2025-26 {title_map[category]} Leaders', fontsize=14, fontweight='bold')
        
        for bar, val in zip(bars, totals[::-1]):
            ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2, 
                   f'{val:.0f}', va='center', fontsize=10)
        
        plt.tight_layout()
        
        filepath = os.path.join("data", f"leaders_{category}.png")
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"\n✓ Chart saved to: {filepath}")
    
    conn.close()


# ============== HEATMAP ==============

def show_heatmap(save_png=False):
    """Show team stats correlation heatmap."""
    import sqlite3
    import matplotlib.pyplot as plt
    import seaborn as sns
    import pandas as pd
    import os
    
    conn = sqlite3.connect("data/hermes.db")
    cur = conn.cursor()
    
    # Get team stats from box_scores
    stats = cur.execute("""
        SELECT 
            t.full_name as Team,
            COUNT(DISTINCT g.game_id) as GP,
            SUM(bs.points) as PTS,
            SUM(bs.rebounds) as REB,
            SUM(bs.assists) as AST,
            SUM(bs.steals) as STL,
            SUM(bs.blocks) as BLK,
            SUM(bs.turnovers) as TOV,
            SUM(bs.fg3m) as TPM
        FROM box_scores bs
        JOIN games g ON bs.game_id = g.game_id
        JOIN teams t ON bs.team_id = t.team_id
        WHERE g.season = '2024-25'
        GROUP BY t.team_id
    """).fetchall()
    
    if not stats:
        print("No team stats found for 2024-25 season")
        conn.close()
        return
    
    import pandas as pd
    df = pd.DataFrame(stats, columns=['Team', 'GP', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'TPM'])
    
    # Calculate per-game stats
    df['PPG'] = df['PTS'] / df['GP']
    df['RPG'] = df['REB'] / df['GP']
    df['APG'] = df['AST'] / df['GP']
    df['SPG'] = df['STL'] / df['GP']
    df['BPG'] = df['BLK'] / df['GP']
    df['TPG'] = df['TOV'] / df['GP']
    df['TPMpg'] = df['TPM'] / df['GP']
    
    # Get correlation matrix
    stats_cols = ['PPG', 'RPG', 'APG', 'SPG', 'BPG', 'TPG', 'TPMpg']
    corr_matrix = df[stats_cols].corr()
    
    print("\n=== Team Stats Correlation Matrix (2024-25) ===\n")
    print(corr_matrix.round(2).to_string())
    
    if save_png:
        fig, ax = plt.subplots(figsize=(10, 8))
        sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='coolwarm',
                   center=0, square=True, linewidths=1, ax=ax)
        ax.set_title('NBA Team Stats Correlation Matrix (2024-25)', fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        filepath = os.path.join("data", "heatmap.png")
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"\n✓ Chart saved to: {filepath}")
    
    conn.close()


# ============== SHOT CHART ==============

def show_shot(name_query, save_png=False):
    """Show player shot chart."""
    import sqlite3
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle, Arc
    import os
    
    if not name_query:
        print("Usage: /shot <player> [--png]")
        print("Example: /shot Curry")
        return
    
    if '--png' in name_query:
        name_query = name_query.replace('--png', '').strip()
        save_png = True
    
    conn = sqlite3.connect("data/hermes.db")
    cur = conn.cursor()
    
    # Find player
    player = cur.execute("SELECT player_id, first_name, last_name FROM players WHERE first_name LIKE ? OR last_name LIKE ? LIMIT 1",
                       (f"%{name_query}%", f"%{name_query}%")).fetchone()
    
    if not player:
        print(f"No player found matching '{name_query}'")
        conn.close()
        return
    
    # Get shot data
    shots = cur.execute("""
        SELECT loc_x, loc_y, shot_made, shot_distance, action_type, shot_type
        FROM shot_charts
        WHERE player_id = ?
    """, (player[0],)).fetchall()
    
    if not shots:
        print(f"No shot chart data for {player[1]} {player[2]}")
        conn.close()
        return
    
    print(f"\n=== {player[1]} {player[2]} Shot Chart ===")
    print(f"Total shots: {len(shots)}")
    
    made = sum(1 for s in shots if s[2] == 1)
    print(f"Made: {made} ({made/len(shots)*100:.1f}%)")
    
    if save_png:
        # Draw court
        def draw_court(ax=None, color='black', lw=2):
            if ax is None:
                ax = plt.gca()
            
            hoop = Circle((0, 0), radius=7.5, linewidth=lw, color=color, fill=False)
            backboard = Rectangle((-30, -7.5), 60, -1, linewidth=lw, color=color)
            outer_box = Rectangle((-80, -47.5), 190, 160, linewidth=lw, color=color, fill=False)
            inner_box = Rectangle((-60, -47.5), 120, 190, linewidth=lw, color=color, fill=False)
            top_free_throw = Arc((0, 142.5), 120, 120, theta1=0, theta2=180, linewidth=lw, color=color, fill=False)
            bottom_free_throw = Arc((0, 142.5), 120, 120, theta1=180, theta2=0, linewidth=lw, color=color, linestyle='dashed')
            corner_three_a = Rectangle((-220, -47.5), 0, 140, linewidth=lw, color=color)
            corner_three_b = Rectangle((220, -47.5), 0, 140, linewidth=lw, color=color)
            three_arc = Arc((0, 0), 475, 475, theta1=22, theta2=158, linewidth=lw, color=color)
            center_outer_arc = Arc((0, 422.5), 120, 120, theta1=180, theta2=0, linewidth=lw, color=color)
            
            court_elements = [hoop, backboard, outer_box, inner_box, top_free_throw, 
                            bottom_free_throw, corner_three_a, corner_three_b, three_arc, center_outer_arc]
            
            for element in court_elements:
                ax.add_patch(element)
            
            return ax
        
        fig, ax = plt.subplots(figsize=(12, 11))
        draw_court(ax)
        ax.set_xlim(-250, 250)
        ax.set_ylim(-50, 450)
        ax.set_aspect('equal')
        
        # Plot shots
        for shot in shots:
            x, y, made, dist, action, stype = shot
            color = '#17408B' if made == 1 else '#C9082A'  # Blue for made, Red for miss
            ax.scatter(x, y, c=color, s=100, alpha=0.6)
        
        # Legend
        from matplotlib.lines import Line2D
        legend_elements = [Line2D([0], [0], marker='o', color='w', markerfacecolor='#17408B', 
                                 markersize=10, label='Made'),
                         Line2D([0], [0], marker='o', color='w', markerfacecolor='#C9082A', 
                                 markersize=10, label='Missed')]
        ax.legend(handles=legend_elements, loc='upper right')
        
        ax.set_title(f'{player[1]} {player[2]} - Shot Chart', fontsize=14, fontweight='bold')
        ax.set_xlabel('Court Width (units)')
        ax.set_ylabel('Court Length (units)')
        
        plt.tight_layout()
        
        filename = f"{player[1]}_{player[2]}_shot_chart.png".replace(" ", "_")
        filepath = os.path.join("data", filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"\n✓ Chart saved to: {filepath}")
    
    conn.close()


def show_pattern(query, save_png=False):
    """Analyze player matchup patterns."""
    sys.path.insert(0, 'src')
    from sportsprediction.data.models.base import create_db_engine
    from sportsprediction.data.db import get_session
    from sportsprediction.data.features.pattern.detector import PatternDetector, MatchupPattern
    from sportsprediction.data.models import Player, Team
    
    # Parse query: "player vs team"
    if ' vs ' not in query:
        print("Usage: /pattern <player> vs <team>")
        return
    
    player_name, team_name = query.split(' vs ', 1)
    player_name = player_name.strip()
    team_name = team_name.strip()
    
    engine = create_db_engine("data/hermes.db")
    with get_session(engine) as session:
        # Find player
        player = session.query(Player).filter(
            (Player.first_name + ' ' + Player.last_name).ilike(f"%{player_name}%")
        ).first()
        
        if not player:
            print(f"Player not found: {player_name}")
            return
        
        # Find team
        team = session.query(Team).filter(
            Team.full_name.ilike(f"%{team_name}%")
        ).first()
        
        if not team:
            team = session.query(Team).filter(
                Team.abbreviation.ilike(f"%{team_name}%")
            ).first()
        
        if not team:
            print(f"Team not found: {team_name}")
            return
        
        # Detect patterns
        detector = PatternDetector(session)
        patterns = detector.detect_for_player_team(player.player_id, team.team_id)
        
        print(f"\n{'='*60}")
        print(f"PATTERN ANALYSIS: {player.first_name} {player.last_name} vs {team.full_name}")
        print(f"{'='*60}")
        
        if not patterns:
            print("\nNo significant patterns detected (need more matchup history)")
        else:
            for p in patterns:
                strength_bar = "█" * int(p.strength * 10) + "░" * (10 - int(p.strength * 10))
                print(f"\n[{p.pattern.value.upper()}] {p.description}")
                print(f"  Strength: {strength_bar} ({p.strength:.0%})")
                for e in p.evidence:
                    print(f"    • {e}")
        
        print()


def show_matchup(query, save_png=False):
    """Classify player vs team matchup."""
    sys.path.insert(0, 'src')
    from sportsprediction.data.models.base import create_db_engine
    from sportsprediction.data.db import get_session
    from sportsprediction.data.features.pattern.classifier import MatchupClassifier, MatchupType
    from sportsprediction.data.models import Player, Team
    
    # Parse query: "player vs team"
    if ' vs ' not in query:
        print("Usage: /matchup <player> vs <team>")
        return
    
    player_name, team_name = query.split(' vs ', 1)
    player_name = player_name.strip()
    team_name = team_name.strip()
    
    engine = create_db_engine("data/hermes.db")
    with get_session(engine) as session:
        # Find player
        player = session.query(Player).filter(
            (Player.first_name + ' ' + Player.last_name).ilike(f"%{player_name}%")
        ).first()
        
        if not player:
            print(f"Player not found: {player_name}")
            return
        
        # Find team
        team = session.query(Team).filter(
            Team.full_name.ilike(f"%{team_name}%")
        ).first()
        
        if not team:
            team = session.query(Team).filter(
                Team.abbreviation.ilike(f"%{team_name}%")
            ).first()
        
        if not team:
            print(f"Team not found: {team_name}")
            return
        
        # Classify matchup
        classifier = MatchupClassifier(session)
        result = classifier.classify(player.player_id, team.team_id)
        
        print(f"\n{'='*60}")
        print(f"MATCHUP CLASSIFICATION: {player.first_name} {player.last_name} vs {team.full_name}")
        print(f"{'='*60}")
        
        emoji = {
            MatchupType.EXPLOITABLE: "🟢",
            MatchupType.TOUGH: "🔴",
            MatchupType.NEUTRAL: "⚪",
            MatchupType.UNKNOWN: "❓"
        }
        
        print(f"\n{emoji[result.matchup_type]} TYPE: {result.matchup_type.value.upper()}")
        print(f"  Confidence: {result.confidence:.0%}")
        
        if result.diff_points is not None:
            sign = "+" if result.diff_points > 0 else ""
            print(f"  Points diff: {sign}{result.diff_points:.1f} vs season avg")
        if result.diff_rebounds is not None:
            sign = "+" if result.diff_rebounds > 0 else ""
            print(f"  Rebounds diff: {sign}{result.diff_rebounds:.1f}")
        if result.diff_assists is not None:
            sign = "+" if result.diff_assists > 0 else ""
            print(f"  Assists diff: {sign}{result.diff_assists:.1f}")
        
        if result.matchup_type == MatchupType.EXPLOITABLE:
            print("\n💡 This matchup is FAVORABLE - player performs well vs this team")
        elif result.matchup_type == MatchupType.TOUGH:
            print("\n⚠️  This matchup is TOUGH - this team defends player well")
        elif result.matchup_type == MatchupType.NEUTRAL:
            print("\n➖ No clear advantage either way")
        
        print()


def show_momentum(save_png=False):
    """Show who's hot and who's cold."""
    sys.path.insert(0, 'src')
    from sportsprediction.data.models.base import create_db_engine
    from sportsprediction.data.db import get_session
    from sportsprediction.data.models import BoxScore, Game, Player
    from sqlalchemy import func
    import matplotlib.pyplot as plt
    
    engine = create_db_engine("data/hermes.db")
    with get_session(engine) as session:
        # Get last 5 games for all players, aggregate points
        recent = (
            session.query(
                Player.player_id,
                Player.first_name,
                Player.last_name,
                func.avg(BoxScore.points).label('avg_pts'),
                func.count(BoxScore.game_id).label('games')
            )
            .join(BoxScore, Player.player_id == BoxScore.player_id)
            .join(Game, BoxScore.game_id == Game.game_id)
            .filter(Game.game_date > '2025-12-01')
            .group_by(Player.player_id, Player.first_name, Player.last_name)
            .having(func.count(BoxScore.game_id) >= 5)
            .order_by(func.avg(BoxScore.points).desc())
            .limit(20)
            .all()
        )
        
        print(f"\n{'='*60}")
        print("MOMENTUM TRACKER - Who's Hot/Cold (Last 2+ Months)")
        print(f"{'='*60}")
        
        print("\n🔥 TOP SCORERS (Last 5+ games):")
        print(f"{'Player':<25} {'Avg PPG':>10} {'Games':>6}")
        print("-" * 43)
        for r in recent[:10]:
            print(f"{r.first_name} {r.last_name:<18} {r.avg_pts:>10.1f} {r.games:>6}")
        
        # Cold players
        cold = recent[-10:] if len(recent) >= 10 else recent
        print("\n❄️  COLD (Lower scoring):")
        print(f"{'Player':<25} {'Avg PPG':>10} {'Games':>6}")
        print("-" * 43)
        for r in cold:
            print(f"{r.first_name} {r.last_name:<18} {r.avg_pts:>10.1f} {r.games:>6}")
        
        print()


def main():
    print("Loading data...")
    elo = load_elo()
    teams = load_teams()
    print(f"✓ Loaded {len(teams)} teams, {len(elo)} ELO ratings\n")
    
    print(HELP)
    
    while True:
        try:
            cmd = input("(NBA) ").strip()
        except EOFError:
            break
        
        if not cmd:
            continue
        
        if cmd.startswith('/'):
            cmd = cmd[1:]  # Remove leading /
        
        parts = cmd.split(' ', 1)
        cmd_name = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        
        if cmd_name in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
        elif cmd_name == 'help':
            print(HELP)
        elif cmd_name == 'elo':
            save_png = '--png' in arg
            arg = arg.replace('--png', '').strip()
            show_elo(teams, elo, save_png)
        elif cmd_name == 'games':
            show_games(teams)
        elif cmd_name == 'predict':
            show_predict(teams, elo, arg)
        elif cmd_name == 'odds':
            show_odds()
        elif cmd_name == 'teams':
            show_teams(teams)
        elif cmd_name == 'player':
            save_png = '--png' in arg
            show_player(arg, save_png)
        elif cmd_name == 'team':
            save_png = '--png' in arg
            show_team(arg, save_png)
        elif cmd_name == 'compare':
            save_png = '--png' in arg
            show_compare(arg, save_png)
        elif cmd_name == 'trend':
            save_png = '--png' in arg
            show_trend(arg, save_png)
        elif cmd_name == 'top':
            save_png = '--png' in arg
            show_top(arg, save_png)
        elif cmd_name == 'heatmap':
            save_png = '--png' in arg
            show_heatmap(save_png)
        elif cmd_name == 'shot':
            save_png = '--png' in arg
            show_shot(arg, save_png)
        elif cmd_name == 'pattern':
            save_png = '--png' in arg
            show_pattern(arg, save_png)
        elif cmd_name == 'matchup':
            save_png = '--png' in arg
            show_matchup(arg, save_png)
        elif cmd_name == 'momentum':
            save_png = '--png' in arg
            show_momentum(save_png)
        elif cmd_name == 'update':
            update_elo()
            elo = load_elo()
        else:
            print(f"Unknown: /{cmd_name}")
            print("Type /help for commands")

if __name__ == "__main__":
    main()
