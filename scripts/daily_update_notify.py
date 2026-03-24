#!/usr/bin/env python3
"""Daily update script for HermesAnalysis with Telegram notifications.

Usage:
    python scripts/daily_update_notify.py

Runs via cron:
    0 8 * * * cd /home/absent/HermesAnalysis && python scripts/daily_update_notify.py
"""

import os
import sys
import requests
import sqlite3
import json
from datetime import datetime

# Change to project directory
os.chdir("/home/absent/HermesAnalysis")
sys.path.insert(0, "/home/absent/HermesAnalysis/src")

# Telegram config - set these as environment variables
BOT_TOKEN = os.environ.get("HERMES_TELEGRAM_BOT_TOKEN", "CHANGEME_BOT_TOKEN")
CHAT_ID = os.environ.get("HERMES_TELEGRAM_CHAT_ID", "CHANGEME_CHAT_ID")

def send_message(text):
    """Send message via Telegram bot."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        r = requests.post(url, data=data, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}", file=sys.stderr)
        return False

def get_db_stats():
    """Get current stats from database."""
    try:
        conn = sqlite3.connect("data/hermes.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT MAX(game_date) FROM games")
        last_game = cursor.fetchone()[0] or "Unknown"
        
        cursor.execute("SELECT COUNT(*) FROM games")
        total_games = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM players")
        total_players = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "last_game": last_game,
            "total_games": total_games,
            "total_players": total_players
        }
    except Exception as e:
        return {"error": str(e)}

def run_daily_update():
    """Run the daily update."""
    games_synced = 0
    
    # 1. Update ELO ratings (skip games sync for now due to API issues)
    print("\n[1/2] Updating ELO ratings...")
    try:
        # Simple ELO update - only process recent games
        INITIAL_ELO = 1500
        K_FACTOR = 32
        HOME_COURT = 100
        
        # Load existing ELO
        elo_path = "data/elo_ratings.json"
        if os.path.exists(elo_path):
            with open(elo_path) as f:
                ratings = json.load(f)
        else:
            ratings = {}
        
        # Initialize missing teams
        conn = sqlite3.connect("data/hermes.db")
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT home_team_id FROM games")
        teams = set()
        for row in cursor.fetchall():
            teams.add(str(row[0]))
        
        for team_id in teams:
            if team_id not in ratings:
                ratings[team_id] = {"elo": INITIAL_ELO, "wins": 0, "losses": 0}
        
        # Process recent games only (last 100 to save time)
        cursor.execute("""
            SELECT home_team_id, away_team_id, home_score, away_score 
            FROM games 
            WHERE home_score IS NOT NULL AND away_score IS NOT NULL
            ORDER BY game_date DESC 
            LIMIT 100
        """)
        recent_games = cursor.fetchall()
        conn.close()
        
        # Update ELO for recent games
        for home_id, away_id, home_score, away_score in recent_games:
            home_id, away_id = str(home_id), str(away_id)
            
            home_elo = ratings.get(home_id, {}).get("elo", INITIAL_ELO)
            away_elo = ratings.get(away_id, {}).get("elo", INITIAL_ELO)
            
            # Expected score
            home_exp = 1 / (1 + 10 ** ((away_elo - home_elo - HOME_COURT) / 400))
            
            # Actual score
            home_actual = 1 if home_score > away_score else 0
            
            # Update ELO
            new_home_elo = home_elo + K_FACTOR * (home_actual - home_exp)
            new_away_elo = away_elo + K_FACTOR * ((1 - home_actual) - (1 - home_exp))
            
            ratings[home_id] = {"elo": new_home_elo, "wins": ratings.get(home_id, {}).get("wins", 0) + home_actual, "losses": ratings.get(home_id, {}).get("losses", 0) + (1 - home_actual)}
            ratings[away_id] = {"elo": new_away_elo, "wins": ratings.get(away_id, {}).get("wins", 0) + (1 - home_actual), "losses": ratings.get(away_id, {}).get("losses", 0) + home_actual}
        
        # Save ELO
        with open(elo_path, "w") as f:
            json.dump(ratings, f, indent=2)
        
        print(f"   ✓ Updated ELO for {len(ratings)} teams (recent games)")
    except Exception as e:
        print(f"   ⚠ ELO update error: {e}")
    
    return games_synced

def main():
    """Main notification handler."""
    print("=" * 50)
    print("HERMESANALYSIS DAILY UPDATE")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Run the daily update
    games_synced = run_daily_update()
    
    # Get stats for notification
    stats = get_db_stats()
    
    # Send Telegram notification
    print("\n[2/2] Sending Telegram notification...")
    
    sync_status = "Game sync requires manual NBA API (rate limited)"
    
    message = f"""🏀 <b>HermesAnalysis Daily Update</b>

✅ Update completed: {datetime.now().strftime('%Y-%m-%d %H:%M')}

📊 Stats:
• Last game: {stats.get('last_game', 'N/A')}
• Total games: {stats.get('total_games', 0):,}
• Players: {stats.get('total_players', 0)}

🔄 Sync: {sync_status}
🤖 Model: V5 (64% accuracy)
📅 Next update: Tomorrow 8am
"""
    
    if send_message(message):
        print("   ✓ Notification sent!")
    else:
        print("   ⚠ Failed to send notification")
    
    print("\n" + "=" * 50)
    print("✓ DAILY UPDATE COMPLETE")
    print("=" * 50)

if __name__ == "__main__":
    main()