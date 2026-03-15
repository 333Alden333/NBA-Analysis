"""Script to populate missing player and game data from box_scores."""
import sqlite3
import json

conn = sqlite3.connect('data/hermes.db')
cursor = conn.cursor()

# Extract unique games from box_scores
print("Extracting games...")
cursor.execute('SELECT DISTINCT game_id FROM box_scores')
game_ids = [r[0] for r in cursor.fetchall()]
print(f"Found {len(game_ids)} unique games")

# Extract unique players from box_scores  
print("Extracting players...")
cursor.execute('SELECT DISTINCT raw_json FROM box_scores')
player_data = {}
for row in cursor.fetchall():
    if row[0]:
        data = json.loads(row[0])
        pid = data.get('personId')
        if pid and pid not in player_data:
            player_data[pid] = {
                'first_name': data.get('firstName', ''),
                'last_name': data.get('familyName', ''),
                'position': data.get('position', 'F'),
            }

print(f"Found {len(player_data)} unique players")

# Insert players
print("Inserting players...")
inserted_players = 0
for pid, info in player_data.items():
    try:
        full_name = f"{info['first_name']} {info['last_name']}"
        cursor.execute('''
            INSERT OR IGNORE INTO players (player_id, full_name, first_name, last_name, position, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
        ''', (pid, full_name, info['first_name'], info['last_name'], info['position']))
        inserted_players += 1
    except Exception as e:
        print(f"Error inserting player {pid}: {e}")

print(f"Inserted {inserted_players} players")

# Create games from game_ids
print("Creating games...")
inserted_games = 0
for gid in game_ids:
    try:
        # Parse game_id to get approximate date
        # Format: 0042400407 = season type + year + game number
        if len(gid) >= 10:
            game_num = int(gid[7:10]) if gid[7:10].isdigit() else 0
            # Rough date approximation for 2024-25 season
            if game_num < 82:  # Preseason
                month, day = 10, 1 + game_num
            elif game_num < 632:  # Regular season
                game_num -= 81
                month = 10 + (game_num // 30)
                day = 1 + (game_num % 30)
            else:  # Playoffs
                month, day = 4, 1
            
            game_date = f"2024-{month:02d}-{day:02d}"
        else:
            game_date = "2024-12-01"
            
        cursor.execute('''
            INSERT OR IGNORE INTO games (game_id, game_date, season, status)
            VALUES (?, ?, '2024-25', 'Final')
        ''', (gid, game_date))
        inserted_games += 1
    except Exception as e:
        print(f"Error inserting game {gid}: {e}")

print(f"Inserted {inserted_games} games")

conn.commit()

# Verify
cursor.execute('SELECT COUNT(*) FROM players')
print(f"Total players: {cursor.fetchone()[0]}")

cursor.execute('SELECT COUNT(*) FROM games')
print(f"Total games: {cursor.fetchone()[0]}")

conn.close()
print("Done!")
