#!/usr/bin/env python3
"""ESPN-based NBA game sync adapter.

Alternative to NBA.com API when rate-limited.
Uses ESPN's public API which is more accessible.
"""

import os
import sys
import requests
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# ESPN to NBA.com team ID mapping
ESPN_TO_NBA_ID = {
    1: 1610612737,   # Atlanta Hawks
    2: 1610612738,   # Boston Celtics  
    3: 1610612739,   # Brooklyn Nets
    4: 1610612740,   # Chicago Bulls
    5: 1610612741,   # Cleveland Cavaliers
    6: 1610612742,   # Dallas Mavericks
    7: 1610612743,   # Denver Nuggets
    8: 1610612744,   # Detroit Pistons
    9: 1610612745,   # Golden State Warriors
    10: 1610612746,  # Houston Rockets
    11: 1610612747,  # Indiana Pacers
    12: 1610612748,  # LA Clippers
    13: 1610612749,  # Los Angeles Lakers
    14: 1610612750,  # Memphis Grizzlies
    15: 1610612751,  # Miami Heat
    16: 1610612752,  # Milwaukee Bucks
    17: 1610612753,  # Minnesota Timberwolves
    18: 1610612754,  # New Orleans Pelicans
    19: 1610612755,  # New York Knicks
    20: 1610612756,  # Oklahoma City Thunder
    21: 1610612757,  # Orlando Magic
    22: 1610612758,  # Philadelphia 76ers
    23: 1610612759,  # Phoenix Suns
    24: 1610612760,  # Portland Trail Blazers
    25: 1610612761,  # Sacramento Kings
    26: 1610612762,  # San Antonio Spurs
    27: 1610612763,  # Toronto Raptors
    28: 1610612764,  # Utah Jazz
    29: 1610612765,  # Washington Wizards
    30: 1610612766,  # Charlotte Hornets
}

def get_games_for_date(date_str: str) -> List[Dict]:
    """Get NBA games for a specific date from ESPN API."""
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str}"
    
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return []
        
        data = r.json()
        games = []
        
        for event in data.get("events", []):
            comp = event.get("competitions", [{}])[0]
            
            # Get teams and scores
            competitors = comp.get("competitors", [])
            if len(competitors) < 2:
                continue
            
            home = next((c for c in competitors if c.get("homeAway") == "home"), {})
            away = next((c for c in competitors if c.get("homeAway") == "away"), {})
            
            if not home or not away:
                continue
            
            # Extract data
            home_team_id = ESPN_TO_NBA_ID.get(int(home.get("team", {}).get("id", 0)))
            away_team_id = ESPN_TO_NBA_ID.get(int(away.get("team", {}).get("id", 0)))
            
            if not home_team_id or not away_team_id:
                continue
            
            game_data = {
                "game_date": date_str,
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "home_score": int(home.get("score", 0)),
                "away_score": int(away.get("score", 0)),
                "status": comp.get("status", {}).get("description", "Final"),
            }
            
            games.append(game_data)
        
        return games
    
    except Exception as e:
        print(f"Error fetching {date_str}: {e}")
        return []

def sync_recent_games(db_path: str, days_back: int = 7) -> Dict[str, int]:
    """Sync recent games from ESPN API."""
    results = {"games_synced": 0, "dates_checked": 0, "errors": 0}
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get the latest date in our database
    cursor.execute("SELECT MAX(game_date) FROM games WHERE game_date >= '2025-10-21'")
    last_date = cursor.fetchone()[0]
    
    if last_date:
        last_date = datetime.strptime(last_date, "%Y-%m-%d")
    else:
        last_date = datetime.now() - timedelta(days=days_back)
    
    # Check recent dates
    today = datetime.now()
    
    for i in range(days_back):
        check_date = today - timedelta(days=i)
        
        # Skip if we already have this date
        if last_date and check_date.date() <= last_date.date():
            continue
        
        date_str = check_date.strftime("%Y%m%d")
        games = get_games_for_date(date_str)
        
        results["dates_checked"] += 1
        
        for game in games:
            # Check if game already exists
            cursor.execute("""
                SELECT COUNT(*) FROM games 
                WHERE game_date = ? AND home_team_id = ? AND away_team_id = ?
            """, (check_date.strftime("%Y-%m-%d"), game["home_team_id"], game["away_team_id"]))
            
            if cursor.fetchone()[0] == 0:
                # Generate game_id (format: 0022400006 = season + game number)
                season = f"002{check_date.year % 100}{((check_date.month - 1) // 3) + 1}0"
                game_id = f"{season}{results['games_synced']:04d}"
                
                # Determine season from date
                if check_date.month >= 10:
                    game_season = f"20{check_date.year % 100}-{check_date.year % 100 + 1}"
                else:
                    game_season = f"20{check_date.year % 100 - 1}-{check_date.year % 100}"
                
                # Insert new game
                cursor.execute("""
                    INSERT INTO games (game_id, season, game_date, home_team_id, away_team_id, home_score, away_score, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    game_id,
                    game_season,
                    check_date.strftime("%Y-%m-%d"),
                    game["home_team_id"],
                    game["away_team_id"],
                    game["home_score"],
                    game["away_score"],
                    game.get("status", "Final")
                ))
                results["games_synced"] += 1
    
    conn.commit()
    conn.close()
    
    return results

def main():
    """Test the ESPN sync."""
    print("Testing ESPN API sync...")
    
    # Test getting games for yesterday
    yesterday = datetime.now() - timedelta(days=1)
    games = get_games_for_date(yesterday.strftime("%Y%m%d"))
    
    print(f"Found {len(games)} games for {yesterday.strftime('%Y-%m-%d')}:")
    for game in games:
        print(f"  Team {game['away_team_id']} @ {game['home_team_id']}: {game['away_score']}-{game['home_score']}")
    
    # Test syncing to database
    if games:
        results = sync_recent_games("data/hermes.db", days_back=1)
        print(f"\nSync results: {results}")

if __name__ == "__main__":
    main()