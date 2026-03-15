#!/usr/bin/env python
"""Daily update script - runs automatically to keep model fresh.

Usage:
    python scripts/daily_update.py

This script:
1. Syncs new games from NBA API
2. Updates ELO ratings
3. (Optional) Rebuilds ML model

Run via cron:
    0 8 * * * cd /path/to/HermesAnalysis && python scripts/daily_update.py
"""

import os
import sys

# Change to project directory
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("="*60)
print("NBA PREDICTION DAILY UPDATE")
print("="*60)

# 1. Sync new games
print("\n[1/3] Syncing new games...")
try:
    from sportsprediction.data.ingestion.daily_sync import sync_today_games
    from sportsprediction.data.models.base import create_db_engine
    from sportsprediction.data.db import get_session
    
    engine = create_db_engine("data/hermes.db")
    with get_session(engine) as session:
        result = sync_today_games(session)
    print(f"   ✓ Synced {result.get('games_synced', 0)} new games")
except Exception as e:
    print(f"   ⚠ Sync error (may be no new games): {e}")

# 2. Update ELO
print("\n[2/3] Updating ELO ratings...")
try:
    from scripts.compute_elo import compute_elo_ratings
    
    engine = create_db_engine("data/hermes.db")
    with get_session(engine) as session:
        ratings = compute_elo_ratings(session, "data/elo_ratings.json")
    print(f"   ✓ Updated ELO for {len(ratings)} teams")
except Exception as e:
    print(f"   ⚠ ELO update error: {e}")

# 3. Rebuild model (optional - uncomment if desired)
# print("\n[3/3] Rebuilding ML model...")
# try:
#     os.system("python scripts/train_poc_v4.py > /dev/null 2>&1")
#     os.system("python scripts/train_model_v2.py > /dev/null 2>&1")
#     print("   ✓ Model rebuilt")
# except Exception as e:
#     print(f"   ⚠ Model rebuild error: {e}")

print("\n" + "="*60)
print("✓ DAILY UPDATE COMPLETE")
print("="*60)
print("\nTo use:")
print("  python scripts/cli.py")
print("  # Then type /elo, /predict, /games, etc.")
