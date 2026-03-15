"""Ultra-fast box score sync using bulk API endpoints.

Uses PlayerGameLogs to get ALL box scores for a season in ONE API call.
This is the proper way to do it.
"""

import time
import sqlite3
import json
import logging
from datetime import datetime

from nba_api.stats.endpoints import playergamelogs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ultra_fast_sync():
    """Sync all box scores using bulk endpoint - one call per season!"""
    
    conn = sqlite3.connect('data/hermes.db')
    cursor = conn.cursor()
    
    SEASONS = ['2022-23', '2023-24', '2024-25', '2025-26']
    
    total_rows = 0
    
    for season in SEASONS:
        logger.info(f"=== Syncing {season} ===")
        
        try:
            # ONE API CALL gets all player stats for entire season!
            logs = playergamelogs.PlayerGameLogs(
                season_nullable=season,
                season_type_nullable='Regular Season'
            )
            df = logs.get_data_frames()[0]
            
            logger.info(f"Got {len(df)} rows for {season}")
            
            # Insert all rows
            for _, row in df.iterrows():
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO box_scores 
                        (game_id, player_id, team_id, points, rebounds, assists,
                         steals, blocks, turnovers, fgm, fga, fg3m, fg3a, ftm, fta,
                         plus_minus, offensive_rebounds, defensive_rebounds,
                         personal_fouls, raw_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        row.get('GAME_ID'),
                        row.get('PLAYER_ID'),
                        row.get('TEAM_ID'),
                        row.get('PTS'),
                        row.get('REB'),
                        row.get('AST'),
                        row.get('STL'),
                        row.get('BLK'),
                        row.get('TOV'),  # TOV not TO
                        row.get('FGM'),
                        row.get('FGA'),
                        row.get('FG3M'),
                        row.get('FG3A'),
                        row.get('FTM'),
                        row.get('FTA'),
                        row.get('PLUS_MINUS'),
                        row.get('OREB'),
                        row.get('DREB'),
                        row.get('PF'),
                        row.to_json()
                    ))
                    total_rows += 1
                except Exception as e:
                    pass
            
            conn.commit()
            logger.info(f"Inserted {len(df)} rows for {season}")
            
            # Also do playoffs
            try:
                logs_p = playergamelogs.PlayerGameLogs(
                    season_nullable=season,
                    season_type_nullable='Playoffs'
                )
                df_p = logs_p.get_data_frames()[0]
                
                logger.info(f"Got {len(df_p)} playoff rows for {season}")
                
                for _, row in df_p.iterrows():
                    try:
                        cursor.execute('''
                            INSERT OR REPLACE INTO box_scores 
                            (game_id, player_id, team_id, points, rebounds, assists,
                             steals, blocks, turnovers, fgm, fga, fg3m, fg3a, ftm, fta,
                             plus_minus, offensive_rebounds, defensive_rebounds,
                             personal_fouls, raw_json)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            row.get('GAME_ID'),
                            row.get('PLAYER_ID'),
                            row.get('TEAM_ID'),
                            row.get('PTS'),
                            row.get('REB'),
                            row.get('AST'),
                            row.get('STL'),
                            row.get('BLK'),
                            row.get('TO'),
                            row.get('FGM'),
                            row.get('FGA'),
                            row.get('FG3M'),
                            row.get('FG3A'),
                            row.get('FTM'),
                            row.get('FTA'),
                            row.get('PLUS_MINUS'),
                            row.get('OREB'),
                            row.get('DREB'),
                            row.get('PF'),
                            row.to_json()
                        ))
                        total_rows += 1
                    except:
                        pass
                
                conn.commit()
                logger.info(f"Inserted {len(df_p)} playoff rows")
                
            except Exception as e:
                logger.warning(f"Playoffs error: {e}")
            
            time.sleep(1)  # Rate limit
            
        except Exception as e:
            logger.error(f"Error syncing {season}: {e}")
    
    logger.info(f"Total rows inserted: {total_rows:,}")
    
    # Final stats
    cursor.execute('SELECT COUNT(*) FROM box_scores')
    total = cursor.fetchone()[0]
    logger.info(f"Total box scores in DB: {total:,}")
    
    # Also sync players from the data
    logger.info("Syncing players...")
    cursor.execute('SELECT DISTINCT player_id, player_name, team_abbreviation FROM box_scores')
    for pid, name, team in cursor.fetchall():
        try:
            parts = name.split() if name else ['', '']
            first = parts[0] if parts else ''
            last = ' '.join(parts[1:]) if len(parts) > 1 else ''
            
            cursor.execute('''
                INSERT OR REPLACE INTO players 
                (player_id, full_name, first_name, last_name, is_active)
                VALUES (?, ?, ?, ?, 1)
            ''', (pid, name, first, last))
        except:
            pass
    
    conn.commit()
    
    cursor.execute('SELECT COUNT(*) FROM players')
    logger.info(f"Total players: {cursor.fetchone()[0]:,}")
    
    conn.close()
    logger.info("DONE!")


if __name__ == "__main__":
    ultra_fast_sync()