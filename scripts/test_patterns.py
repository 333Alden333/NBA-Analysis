"""Test pattern recognition and trend analysis with real data."""
import sys
sys.path.insert(0, '/home/absent/HermesAnalysis/src')

from sqlalchemy import text
from sportsprediction.data.db import init_db
from sportsprediction.data.features.pattern import (
    TrendAnalyzer,
    PerformanceTrend,
    MatchupClassifier,
    MatchupType,
    PatternDetector,
    MatchupPattern,
)

# Get database session
from sportsprediction.data.models.base import create_db_engine, get_session_factory

engine = create_db_engine('/home/absent/HermesAnalysis/data/hermes.db')
Session = get_session_factory(engine)
session = Session()

print("=" * 60)
print("TESTING PATTERN RECOGNITION WITH REAL DATA")
print("=" * 60)

# Test 1: Trend Analysis on Shai Gilgeous-Alexander
print("\n1. TREND ANALYSIS: Shai Gilgeous-Alexander")
print("-" * 40)

analyzer = TrendAnalyzer(session)

# Find Shai's player_id
result = session.execute(text("SELECT player_id, full_name FROM players WHERE full_name LIKE '%Shai%'")).fetchone()
if result:
    shai_id = result[0]
    print(f"Player ID: {shai_id}")
    
    # Analyze points trend
    trend = analyzer.analyze_trend(shai_id, stat='points', games=10)
    print(f"  Trend: {trend.trend.value}")
    print(f"  Slope: {trend.slope:.2f} points/game change")
    print(f"  Recent avg: {trend.recent_avg:.1f}")
    print(f"  Earlier avg: {trend.earlier_avg:.1f}")
    print(f"  Confidence: {trend.confidence:.2f}")
    
    # Get momentum score
    momentum = analyzer.get_momentum_score(shai_id, games=5)
    print(f"  Momentum score (last 5 games): {momentum:.1f}")
else:
    print("  Shai not found in database")

# Test 2: Pattern Detection
print("\n2. PATTERN DETECTION")
print("-" * 40)

detector = PatternDetector(session)

# Try to detect patterns for a player against a team
# Get a player who has multiple games
result = session.execute(text("""
    SELECT player_id, COUNT(*) as game_count 
    FROM box_scores 
    GROUP BY player_id 
    ORDER BY game_count DESC 
    LIMIT 1
""")).fetchone()

if result:
    player_id = result[0]
    game_count = result[1]
    print(f"Testing player {player_id} with {game_count} games")
    
    # Try against team 1610612760 (OKC Thunder)
    patterns = detector.detect_for_player_team(player_id, 1610612760, recent_games=10)
    print(f"  Found {len(patterns)} patterns:")
    for p in patterns:
        print(f"    - {p.pattern.value}: {p.description} (strength: {p.strength:.2f})")

# Test 3: Matchup Classification
print("\n3. MATCHUP CLASSIFICATION")
print("-" * 40)

classifier = MatchupClassifier(session)

# Try to classify a player vs team matchup
if result:
    player_id = result[0]
    # Get a team they played against
    team_result = session.execute(text("""
        SELECT DISTINCT team_id 
        FROM box_scores 
        WHERE player_id = :pid 
        LIMIT 1
    """), {"pid": player_id}).fetchone()
    
    if team_result:
        team_id = team_result[0]
        classification = classifier.classify(player_id, team_id)
        print(f"  Player {player_id} vs Team {team_id}:")
        print(f"    Type: {classification.matchup_type.value}")
        print(f"    Confidence: {classification.confidence:.2f}")
        if classification.diff_points:
            print(f"    Diff points: {classification.diff_points:.1f}")

# Test 4: Find hot players (momentum screening)
print("\n4. MOMENTUM SCREENING: Top 5 Hot Players")
print("-" * 40)

# Get players with most games
results = session.execute(text("""
    SELECT bs.player_id, p.full_name, COUNT(*) as games
    FROM box_scores bs
    JOIN players p ON bs.player_id = p.player_id
    GROUP BY bs.player_id
    HAVING games >= 5
    ORDER BY games DESC
    LIMIT 20
")).fetchall()

momentum_scores = []
for pid, name, games in results:
    momentum = analyzer.get_momentum_score(pid, games=5)
    momentum_scores.append((name, momentum, games))

# Sort by momentum
momentum_scores.sort(key=lambda x: x[1], reverse=True)

print("  Top 5 by momentum:")
for name, momentum, games in momentum_scores[:5]:
    emoji = "HOT" if momentum > 3 else "COLD" if momentum < -3 else "NEUTRAL"
    print(f"    {emoji:6} {name}: {momentum:+.1f} ({games} games)")

print("\n  Bottom 5 by momentum:")
for name, momentum, games in momentum_scores[-5:]:
    emoji = "HOT" if momentum > 3 else "COLD" if momentum < -3 else "NEUTRAL"
    print(f"    {emoji:6} {name}: {momentum:+.1f} ({games} games)")

session.close()
print("\n" + "=" * 60)
print("TESTS COMPLETE")
print("=" * 60)