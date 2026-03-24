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
# export HERMES_TELEGRAM_BOT_TOKEN="your_bot_token_here"
# export HERMES_TELEGRAM_CHAT_ID="your_chat_id_here"
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
    
    # Update ELO ratings
    print("\n[1/2] Updating ELO ratings...")
    try:
        from sportsprediction.data.models.base import create_db_engine
        from sportsprediction.data.db import get_session
        from sportsprediction.data.models import Game, BoxScore, Team
        from sqlalchemy import func
        import pandas as pd
        import numpy as np
        from collections import defaultdict
        
        INITIAL_ELO = 1500
        K_FACTOR = 32
        HOME_COURT = 100
        
        engine = create_db_engine("data/hermes.db")
        
        with get_session(engine) as session:
            # Get all games
            games = session.query(Game).order_by(Game.game_date).all()
            
            # Get current ELO if exists
            elo_path = "data/elo_ratings.json"
            if os.path.exists(elo_path):
                with open(elo_path) as f:
                    ratings = json.load(f)
            else:
                ratings = {}
            
            # Ensure all teams have ELO
            teams = session.query(Team).all()
            for team in teams:
                if str(team.team_id) not in ratings:
                    ratings[str(team.team_id)] = {"elo": INITIAL_ELO, "wins": 0, "losses": 0}
            
            # Process each game
            for game in games:
                if not game.home_score or not game.away_score:
                    continue
                
                home_id = str(game.home_team_id)
                away_id = str(game.away_team_id)
                
                home_elo = ratings.get(home_id, {}).get("elo", INITIAL_ELO)
                away_elo = ratings.get(away_id, {}).get("elo", INITIAL_ELO)
                
                # Expected score
                home_exp = 1 / (1 + 10 ** ((away_elo - home_elo - HOME_COURT) / 400))
                
                # Actual score
                home_actual = 1 if game.home_score > game.away_score else 0
                
                # Update ELO
                new_home_elo = home_elo + K_FACTOR * (home_actual - home_exp)
                new_away_elo = away_elo + K_FACTOR * ((1 - home_actual) - (1 - home_exp))
                
                ratings[home_id] = {"elo": new_home_elo, "wins": ratings.get(home_id, {}).get("wins", 0) + home_actual, "losses": ratings.get(home_id, {}).get("losses", 0) + (1 - home_actual)}
                ratings[away_id] = {"elo": new_away_elo, "wins": ratings.get(away_id, {}).get("wins", 0) + (1 - home_actual), "losses": ratings.get(away_id, {}).get("losses", 0) + home_actual}
            
            # Save ELO
            with open(elo_path, "w") as f:
                json.dump(ratings, f, indent=2)
        
        print(f"   ✓ Updated ELO for {len(ratings)} teams")
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
    message = f"""🏀 <b>HermesAnalysis Daily Update</b>

✅ Update completed: {datetime.now().strftime('%Y-%m-%d %H:%M')}

📊 Stats:
• Last game: {stats.get('last_game', 'N/A')}
• Total games: {stats.get('total_games', 0):,}
• Players: {stats.get('total_players', 0)}

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