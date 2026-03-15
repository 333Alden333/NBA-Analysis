"""Fix game dates using nba_api properly.

This is the RIGHT way to get game dates - use the LeagueGameFinder
endpoint which returns proper GAME_DATE for each game.
"""

import time
import pandas as pd
from sqlalchemy import text
from sportsprediction.data.models.base import create_db_engine, get_session_factory
from nba_api.stats.endpoints import leaguegamefinder

# Configuration
SEASONS = ['2022-23', '2023-24', '2024-25', '2025-26']

def fix_game_dates():
    """Fetch proper game dates from nba_api."""
    
    engine = create_db_engine('data/hermes.db')
    Session = get_session_factory(engine)
    session = Session()
    
    total_fixed = 0
    
    for season in SEASONS:
        print(f"Fetching {season} schedule...")
        
        try:
            # Get all games for the season - Regular Season
            finder = leaguegamefinder.LeagueGameFinder(
                season_nullable=season,
                season_type_nullable='Regular Season'
            )
            df = finder.get_data_frames()[0]
            
            # Get unique games with dates
            game_dates = df[['GAME_ID', 'GAME_DATE']].drop_duplicates()
            print(f"  Found {len(game_dates)} regular season games")
            
            # Update games table using raw SQL
            for _, row in game_dates.iterrows():
                gid = row['GAME_ID']
                game_date = row['GAME_DATE']
                
                if pd.notna(game_date) and gid:
                    stmt = text("""
                        UPDATE games 
                        SET game_date = :date, season = :season, status = 'Final'
                        WHERE game_id = :gid
                    """)
                    session.execute(stmt, {"date": game_date, "season": season, "gid": gid})
            
            session.commit()
            total_fixed += len(game_dates)
            print(f"  Updated {len(game_dates)} regular season games")
            
            # Also do playoffs
            for game_type in ['Playoffs', 'Play In']:
                try:
                    finder2 = leaguegamefinder.LeagueGameFinder(
                        season_nullable=season,
                        season_type_nullable=game_type
                    )
                    df2 = finder2.get_data_frames()[0]
                    if len(df2) > 0:
                        game_dates2 = df2[['GAME_ID', 'GAME_DATE']].drop_duplicates()
                        
                        for _, row in game_dates2.iterrows():
                            gid = row['GAME_ID']
                            game_date = row['GAME_DATE']
                            
                            if pd.notna(game_date) and gid:
                                stmt = text("""
                                    UPDATE games 
                                    SET game_date = :date, season = :season, status = 'Final'
                                    WHERE game_id = :gid
                                """)
                                session.execute(stmt, {"date": game_date, "season": season, "gid": gid})
                        
                        session.commit()
                        total_fixed += len(game_dates2)
                        print(f"  {game_type}: {len(game_dates2)} games")
                except Exception as e:
                    print(f"    {game_type} error: {e}")
                    
        except Exception as e:
            print(f"  Error: {e}")
        
        time.sleep(1)  # Rate limit
    
    print(f"\nTotal games updated: {total_fixed}")
    
    # Verify
    result = session.execute(text("SELECT MIN(game_date), MAX(game_date) FROM games")).fetchone()
    print(f"Date range: {result[0]} to {result[1]}")
    
    # Show by season
    result = session.execute(text("SELECT season, COUNT(*) FROM games GROUP BY season ORDER BY season")).fetchall()
    print("\nGames by season:")
    for row in result:
        print(f"  {row[0]}: {row[1]} games")
    
    session.close()

if __name__ == "__main__":
    fix_game_dates()