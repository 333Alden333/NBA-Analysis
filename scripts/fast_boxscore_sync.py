"""Fast box score sync - fetch all box scores for all games efficiently.

Uses nba_api's LeagueGameFinder to get all game data in bulk,
then processes in batches to avoid rate limiting.
"""

import time
import sqlite3
import json
import logging
from datetime import datetime

from nba_api.stats.endpoints import playergamelogs, boxscore traditional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_DELAY = 0.5  # Fast but not too fast
BATCH_SIZE = 100


def fast_boxscore_sync():
    """Fast sync all box scores using bulk endpoints."""
    
    conn = sqlite3.connect('data/hermes.db')
    cursor = conn.cursor()
    
    # Get all game IDs we need box scores for
    cursor.execute('''
        SELECT game_id FROM games 
        WHERE game_date >= '2022-10-01'
        ORDER BY game_date
    ''')
    game_ids = [r[0] for r in cursor.fetchall()]
    total_games = len(game_ids)
    
    logger.info(f"Need to sync {total_games} games")
    
    # Check which games already have box scores
    cursor.execute('SELECT DISTINCT game_id FROM box_scores')
    existing = set(r[0] for r in cursor.fetchall())
    
    # Filter to only games that need syncing
    to_sync = [gid for gid in game_ids if gid not in existing]
    logger.info(f"Already have {len(existing)}, need {len(to_sync)} more")
    
    if not to_sync:
        logger.info("Nothing to sync!")
        conn.close()
        return
    
    synced = 0
    errors = 0
    
    for i, gid in enumerate(to_sync):
        try:
            # Fetch box score
            time.sleep(API_DELAY)
            
            # Use boxscore traditional endpoint
            bs = boxscore.BoxScoreTraditional(gid)
            data = bs.get_dict()
            
            # Extract player stats
            players = data.get('resultSets', {})
            for rs in players:
                if rs.get('name') == 'PlayerStats':
                    rows = rs.get('rowSet', [])
                    for row in rows:
                        # row structure: [0]=PLAYER_NAME, [1]=PLAYER_ID, etc.
                        # Insert into box_scores
                        try:
                            cursor.execute('''
                                INSERT OR REPLACE INTO box_scores 
                                (game_id, player_id, team_id, points, rebounds, assists,
                                 steals, blocks, turnovers, fgm, fga, fg3m, fg3a, ftm, fta,
                                 plus_minus, offensive_rebounds, defensive_rebounds,
                                 personal_fouls, raw_json)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                gid,
                                row[1] if len(row) > 1 else None,  # PLAYER_ID
                                row[2] if len(row) > 2 else None,  # TEAM_ID
                                row[24] if len(row) > 24 else None,  # PTS
                                row[20] if len(row) > 20 else None,  # REB
                                row[21] if len(row) > 21 else None,  # AST
                                row[22] if len(row) > 22 else None,  # STL
                                row[23] if len(row) > 23 else None,  # BLK
                                row[25] if len(row) > 25 else None,  # TO
                                row[9] if len(row) > 9 else None,   # FGM
                                row[10] if len(row) > 10 else None,  # FGA
                                row[12] if len(row) > 12 else None,  # FG3M
                                row[13] if len(row) > 13 else None,  # FG3A
                                row[15] if len(row) > 15 else None,  # FTM
                                row[16] if len(row) > 16 else None,  # FTA
                                row[28] if len(row) > 28 else None,  # PLUS_MINUS
                                row[18] if len(row) > 18 else None,  # OREB
                                row[19] if len(row) > 19 else None,  # DREB
                                row[26] if len(row) > 26 else None,  # PF
                                json.dumps(dict(zip([c['name'] for c in rs.get('headers', [])], row)))
                            ))
                        except Exception as e:
                            pass
            
            conn.commit()
            synced += 1
            
            if synced % 50 == 0:
                logger.info(f"Progress: {synced}/{len(to_sync)} games synced")
                
        except Exception as e:
            errors += 1
            if errors < 10:
                logger.warning(f"Error syncing {gid}: {e}")
    
    logger.info(f"Done! Synced {synced} games, {errors} errors")
    
    # Final stats
    cursor.execute('SELECT COUNT(*) FROM box_scores')
    total = cursor.fetchone()[0]
    logger.info(f"Total box scores now: {total:,}")
    
    conn.close()


if __name__ == "__main__":
    fast_boxscore_sync()
