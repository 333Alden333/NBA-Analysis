"""Matchup type classifier - categorizes player vs team matchups.

Classifies matchups based on historical performance patterns:
- EXPLOITABLE: Player performs significantly better than average vs this team
- TOUGH: Player performs significantly worse vs this team (team defends well)
- NEUTRAL: No significant difference in performance
- UNKNOWN: Insufficient data to classify
"""

from enum import Enum
from typing import Optional
from dataclasses import dataclass

import numpy as np
from sqlalchemy.orm import Session

from sportsprediction.data.models import MatchupStats, BoxScore, Game


class MatchupType(Enum):
    """Classification categories for player vs team matchups."""
    EXPLOITABLE = "exploitable"      # Player cooks this team
    TOUGH = "tough"                  # This team locks player up
    NEUTRAL = "neutral"              # No significant advantage
    UNKNOWN = "unknown"              # Not enough data


# Thresholds for classification (in standard deviations)
EXPLOITABLE_THRESHOLD = 0.5   # +0.5 std devs above mean
TOUGH_THRESHOLD = -0.5        # -0.5 std devs below mean

# Minimum sample size for classification
MIN_SAMPLE_FOR_CLASSIFICATION = 5


@dataclass
class MatchupClassification:
    """Result of matchup classification."""
    matchup_type: MatchupType
    confidence: float  # 0-1 scale based on sample size
    diff_points: Optional[float]
    diff_rebounds: Optional[float]
    diff_assists: Optional[float]
    diff_fg_pct: Optional[float]


class MatchupClassifier:
    """Classifies player vs team matchup patterns."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def classify(
        self,
        player_id: int,
        opponent_team_id: int,
        as_of_date: Optional[str] = None,
    ) -> MatchupClassification:
        """Classify a player's historical performance against a team.
        
        Args:
            session: Database session
            player_id: Player to evaluate
            opponent_team_id: Team player is facing
            as_of_date: Only consider games before this date (YYYY-MM-DD)
            
        Returns:
            MatchupClassification with type and confidence
        """
        # Get historical matchup data
        query = self.session.query(MatchupStats).filter(
            MatchupStats.player_id == player_id,
            MatchupStats.opponent_team_id == opponent_team_id,
            MatchupStats.has_matchup_history == True,
        )
        
        if as_of_date:
            query = query.filter(MatchupStats.game_date <= as_of_date)
        
        matchups = query.order_by(MatchupStats.game_date.desc()).all()
        
        if len(matchups) < MIN_SAMPLE_FOR_CLASSIFICATION:
            return MatchupClassification(
                matchup_type=MatchupType.UNKNOWN,
                confidence=0.0,
                diff_points=None,
                diff_rebounds=None,
                diff_assists=None,
                diff_fg_pct=None,
            )
        
        # Compute average differentials
        diffs = {
            'points': [],
            'rebounds': [],
            'assists': [],
            'fg_pct': [],
        }
        
        for m in matchups:
            if m.matchup_diff_points is not None:
                diffs['points'].append(m.matchup_diff_points)
            if m.matchup_diff_rebounds is not None:
                diffs['rebounds'].append(m.matchup_diff_rebounds)
            if m.matchup_diff_assists is not None:
                diffs['assists'].append(m.matchup_diff_assists)
            if m.matchup_diff_fg_pct is not None:
                diffs['fg_pct'].append(m.matchup_diff_fg_pct)
        
        # Compute weighted score (points matter most)
        avg_diffs = {k: np.mean(v) if v else 0.0 for k, v in diffs.items()}
        
        # Composite score: points weighted 2x, others 1x each
        composite = (
            avg_diffs['points'] * 2.0 +
            avg_diffs['rebounds'] * 1.0 +
            avg_diffs['assists'] * 1.0 +
            avg_diffs['fg_pct'] * 100.0  # Scale up FG% impact
        ) / 5.0
        
        # Compute confidence based on sample size
        confidence = min(len(matchups) / 20.0, 1.0)  # Max confidence at 20 games
        
        # Classify based on composite score
        if composite >= EXPLOITABLE_THRESHOLD:
            matchup_type = MatchupType.EXPLOITABLE
        elif composite <= TOUGH_THRESHOLD:
            matchup_type = MatchupType.TOUGH
        else:
            matchup_type = MatchupType.NEUTRAL
        
        return MatchupClassification(
            matchup_type=matchup_type,
            confidence=confidence,
            diff_points=avg_diffs['points'],
            diff_rebounds=avg_diffs['rebounds'],
            diff_assists=avg_diffs['assists'],
            diff_fg_pct=avg_diffs['fg_pct'],
        )
    
    def classify_batch(
        self,
        player_ids: list[int],
        opponent_team_id: int,
    ) -> dict[int, MatchupClassification]:
        """Classify multiple players against the same team.
        
        Useful for finding exploitable matchups for a given opponent.
        
        Args:
            player_ids: List of players to evaluate
            opponent_team_id: Team they're all facing
            
        Returns:
            Dict mapping player_id -> MatchupClassification
        """
        results = {}
        for player_id in player_ids:
            results[player_id] = self.classify(player_id, opponent_team_id)
        return results
