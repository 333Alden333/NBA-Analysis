"""Pattern detector - identifies specific matchup patterns and tendencies.

Detects patterns like:
- Hot streaks: player performs well in consecutive games
- Cold streaks: player struggles in consecutive games
- Trap games: player performs below expectation after big game
- Bounce-back: player performs well after poor performance
- Rest advantage: player performs better/worse on rest
"""

from enum import Enum
from typing import Optional, List
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session

from sportsprediction.data.models import BoxScore, Game, MatchupStats


class MatchupPattern(Enum):
    """Detectable matchup patterns."""
    HOT_STREAK = "hot_streak"
    COLD_STREAK = "cold_streak"
    EXPLOITS_THIS_TEAM = "exploits_this_team"
    STRUGGLES_VS_THIS_TEAM = "struggles_vs_this_team"
    BOUNCE_BACK = "bounce_back"
    TRAP_GAME = "trap_game"
    REST_DISADVANTAGE = "rest_disadvantage"
    HOME_COURT_BOOST = "home_court_boost"


# Thresholds
STREAK_MIN_GAMES = 3
STREAK_THRESHOLD = 1.2  # 20% above/below average
TRAP_AFTER_BIG_GAME = 1.5  # 50% above avg, then below avg
BOUNCE_BACK_AFTER = 0.7  # 30% below avg, then above avg


@dataclass
class PatternDetection:
    """Result of pattern detection."""
    pattern: MatchupPattern
    strength: float  # 0-1 confidence
    description: str
    evidence: List[str]


class PatternDetector:
    """Detects specific performance patterns in matchups."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def detect_for_player_team(
        self,
        player_id: int,
        team_id: int,
        recent_games: int = 10,
    ) -> List[PatternDetection]:
        """Detect patterns for player vs specific team.
        
        Args:
            session: Database session
            player_id: Player to analyze
            team_id: Team to analyze against
            recent_games: How many recent games to consider
            
        Returns:
            List of detected patterns with strength
        """
        patterns = []
        
        # Get recent matchup games
        matchups = (
            self.session.query(MatchupStats, Game)
            .join(Game, MatchupStats.game_id == Game.game_id)
            .filter(
                MatchupStats.player_id == player_id,
                MatchupStats.opponent_team_id == team_id,
                MatchupStats.has_matchup_history == True,
            )
            .order_by(Game.game_date.desc())
            .limit(recent_games)
            .all()
        )
        
        if len(matchups) < STREAK_MIN_GAMES:
            return patterns
        
        # Detect hot/cold streaks
        points_diffs = [m.matchup_diff_points for m in matchups 
                       if m.matchup_diff_points is not None]
        
        if len(points_diffs) >= STREAK_MIN_GAMES:
            # Check for hot streak (last N games all above threshold)
            recent = points_diffs[:STREAK_MIN_GAMES]
            if all(d > STREAK_THRESHOLD for d in recent):
                patterns.append(PatternDetection(
                    pattern=MatchupPattern.HOT_STREAK,
                    strength=min(len(recent) / 5.0, 1.0),
                    description=f"Hot streak: {STREAK_MIN_GAMES}+ games above average",
                    evidence=[f"+{d:.1f} pts above avg" for d in recent[:3]],
                ))
            
            # Check for cold streak
            if all(d < -STREAK_THRESHOLD for d in recent):
                patterns.append(PatternDetection(
                    pattern=MatchupPattern.COLD_STREAK,
                    strength=min(len(recent) / 5.0, 1.0),
                    description=f"Cold streak: {STREAK_MIN_GAMES}+ games below average",
                    evidence=[f"{d:.1f} pts below avg" for d in recent[:3]],
                ))
        
        # Detect if consistently exploits this team
        avg_diff = sum(points_diffs) / len(points_diffs) if points_diffs else 0
        if avg_diff > STREAK_THRESHOLD * 2:
            patterns.append(PatternDetection(
                pattern=MatchupPattern.EXPLOITS_THIS_TEAM,
                strength=min(abs(avg_diff) / 5.0, 1.0),
                description=f"Consistently dominates this opponent",
                evidence=[f"Average +{avg_diff:.1f} pts above their avg"],
            ))
        elif avg_diff < -STREAK_THRESHOLD * 2:
            patterns.append(PatternDetection(
                pattern=MatchupPattern.STRUGGLES_VS_THIS_TEAM,
                strength=min(abs(avg_diff) / 5.0, 1.0),
                description=f"Consistently struggles vs this team",
                evidence=[f"Average {avg_diff:.1f} pts below their avg"],
            ))
        
        return patterns
    
    def detect_trap_game(
        self,
        player_id: int,
        game_id: str,
    ) -> Optional[PatternDetection]:
        """Detect if a game is a 'trap' (after big performance).
        
        A trap game is when player just had a huge game then underperforms.
        
        Args:
            player_id: Player to check
            game_id: Game to evaluate
            
        Returns:
            PatternDetection if trap detected, None otherwise
        """
        # Get this game and previous 2
        games = (
            self.session.query(BoxScore, Game)
            .join(Game, BoxScore.game_id == Game.game_id)
            .filter(BoxScore.player_id == player_id)
            .order_by(Game.game_date.desc())
            .limit(3)
            .all()
        )
        
        if len(games) < 3:
            return None
        
        current, prev, before_prev = games[0], games[1], games[2]
        
        # Check if prev game was huge (50% above season avg)
        # This is simplified - would need season average from rolling stats
        prev_pts = prev[0].points or 0
        
        # Check if current game is below average
        curr_pts = current[0].points or 0
        
        if prev_pts > 30 and curr_pts < prev_pts * 0.7:
            return PatternDetection(
                pattern=MatchupPattern.TRAP_GAME,
                strength=0.7,
                description="Potential trap game after big performance",
                evidence=[f"Previous: {prev_pts} pts", f"Current: {curr_pts} pts"],
            )
        
        return None
