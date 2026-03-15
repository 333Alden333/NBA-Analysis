"""Fix missing game records - better date parsing."""
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('data/hermes.db')
cursor = conn.cursor()

# Clear existing games (keep original 36)
cursor.execute('DELETE FROM games WHERE game_id NOT IN (SELECT game_id FROM box_scores GROUP BY game_id LIMIT 36)')

# Get all unique game_ids
cursor.execute('SELECT DISTINCT game_id FROM box_scores')
all_game_ids = [r[0] for r in cursor.fetchall()]
print(f"Total unique game_ids: {len(all_game_ids)}")

def parse_game_info(game_id):
    """Parse season and date from NBA game_id."""
    try:
        # Format: 00[season][type][game_num]
        # season: 23 = 2022-23, 24 = 2023-24, 25 = 2024-25
        # type: 2 = regular, 4 = playoffs, 5 = play-in
        
        season_code = game_id[2:4]  # '23', '24', '25'
        game_type = game_id[4]  # '2', '4', '5'
        game_num = int(game_id[5:])
        
        season_year = 2000 + int(season_code)
        season = f"{season_year}-{str(season_year+1)[2:]}"
        
        # Game number to date mapping (approximate)
        if game_type == '4':  # Playoffs
            # ~90 playoff games, mid-April to June
            if game_num < 15:
                month, day = 4, 15 + game_num
            elif game_num < 45:
                month, day = 4, (game_num - 15) // 2 + 1
                month = 5
            elif game_num < 75:
                month, day = 5, (game_num - 45) // 2 + 1
            else:
                month, day = 6, (game_num - 75) // 2 + 1
        elif game_type == '5':  # Play-in
            month, day = 4, 10 + (game_num // 10)
        else:  # Regular season
            # ~1230 games, Oct to Apr
            # Days: Oct(31) + Nov(30) + Dec(31) + Jan(31) + Feb(28) + Mar(31) + Apr(15) = 197
            month = 10
            day = game_num + 1
            while day > 30 and month < 12:
                if month in [10, 12, 1, 3]:
                    max_day = 31
                elif month in [11, 4]:
                    max_day = 30
                elif month == 2:
                    max_day = 28
                else:
                    max_day = 31
                
                if day > max_day:
                    day -= max_day
                    month += 1
                else:
                    break
        
        game_date = f"{season_year}-{month:02d}-{day:02d}"
        return season, game_date
    except:
        return None, None

# Get existing game IDs
cursor.execute('SELECT game_id FROM games')
existing = set(r[0] for r in cursor.fetchall())

# Create missing games
inserted = 0
for gid in all_game_ids:
    if gid not in existing:
        season, game_date = parse_game_info(gid)
        if season and game_date:
            cursor.execute('''
                INSERT INTO games (game_id, game_date, season, status)
                VALUES (?, ?, ?, 'Final')
            ''', (gid, game_date, season))
            inserted += 1

conn.commit()
print(f"Inserted {inserted} games")

# Verify
cursor.execute('SELECT COUNT(*) FROM games')
print(f"Total games: {cursor.fetchone()[0]}")

cursor.execute('SELECT MAX(game_date), MIN(game_date) FROM games')
max_d, min_d = cursor.fetchone()
print(f"Date range: {min_d} to {max_d}")

# Show by season
cursor.execute('''
    SELECT season, COUNT(*) 
    FROM games 
    GROUP BY season 
    ORDER BY season
''')
print("\nGames by season:")
for row in cursor.fetchall():
    print(f"  {row}")

# Show recent
cursor.execute('SELECT game_id, game_date, season FROM games ORDER BY game_id DESC LIMIT 5')
print("\nMost recent:")
for row in cursor.fetchall():
    print(f"  {row}")

conn.close()