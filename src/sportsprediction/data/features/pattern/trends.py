"""Performance trend analysis - tracks momentum and trajectory.

Analyzes:
- Performance trajectory (improving/declining)
- Pace-adjusted trends
- Rest impact on performance
- Year-over-year improvements
"""

from enum import Enum
from typing import Optional, List
from dataclasses import dataclass

import numpy as np
from sqlalchemy.orm import Session

from sportsprediction.data.models import BoxScore, Game, PlayerRollingStats


class PerformanceTrend(Enum):
    """Direction of player performance trend."""
    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"
    INSUFFICIENT_DATA = "insufficient_data"


# Trend detection thresholds
MIN_GAMES_FOR_TREND = 5
SLOPE_THRESHOLD = 0.5  # Points per game improvement/decline


@dataclass
class TrendAnalysis:
    """Result of trend analysis."""
    trend: PerformanceTrend
    slope: float  # Points per game change
    recent_avg: float
    earlier_avg: float
    confidence: float  # 0-1 based on sample size and R²


class TrendAnalyzer:
    """Analyzes player performance trends over time."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def analyze_trend(
        self,
        player_id: int,
        stat: str = "points",
        games: int = 20,
    ) -> TrendAnalysis:
        """Analyze player's performance trend for a stat.
        
        Uses linear regression to detect trajectory.
        
        Args:
            player_id: Player to analyze
            stat: Stat to analyze (points, rebounds, assists, etc.)
            games: How many recent games to consider
            
        Returns:
            TrendAnalysis with trend direction and confidence
        """
        # Get recent box scores ordered by date
        recent_games = (
            self.session.query(BoxScore, Game)
            .join(Game, BoxScore.game_id == Game.game_id)
            .filter(BoxScore.player_id == player_id)
            .order_by(Game.game_date.desc())
            .limit(games)
            .all()
        )
        
        if len(recent_games) < MIN_GAMES_FOR_TREND:
            return TrendAnalysis(
                trend=PerformanceTrend.INSUFFICIENT_DATA,
                slope=0.0,
                recent_avg=0.0,
                earlier_avg=0.0,
                confidence=0.0,
            )
        
        # Extract stat values (most recent first)
        stat_values = []
        for bs, game in reversed(recent_games):  # Oldest first for regression
            val = getattr(bs, stat, None)
            if val is not None:
                stat_values.append((len(stat_values), val))
        
        if len(stat_values) < MIN_GAMES_FOR_TREND:
            return TrendAnalysis(
                trend=PerformanceTrend.INSUFFICIENT_DATA,
                slope=0.0,
                recent_avg=0.0,
                earlier_avg=0.0,
                confidence=0.0,
            )
        
        # Linear regression
        x = np.array([v[0] for v in stat_values])
        y = np.array([v[1] for v in stat_values])
        
        # Simple linear regression: y = mx + b
        n = len(x)
        sum_x = np.sum(x)
        sum_y = np.sum(y)
        sum_xy = np.sum(x * y)
        sum_x2 = np.sum(x ** 2)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2) if (n * sum_x2 - sum_x ** 2) != 0 else 0
        
        # Compute R² for confidence
        y_mean = np.mean(y)
        ss_tot = np.sum((y - y_mean) ** 2)
        ss_res = np.sum((y - (slope * x + y_mean - slope * np.mean(x))) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        # Split into halves for avg comparison
        mid = len(stat_values) // 2
        earlier = [v[1] for v in stat_values[:mid]]
        recent = [v[1] for v in stat_values[mid:]]
        
        earlier_avg = np.mean(earlier) if earlier else 0
        recent_avg = np.mean(recent) if recent else 0
        
        # Determine trend
        if abs(slope) < SLOPE_THRESHOLD:
            trend = PerformanceTrend.STABLE
        elif slope > 0:
            trend = PerformanceTrend.IMPROVING
        else:
            trend = PerformanceTrend.DECLINING
        
        # Confidence based on R² and sample size
        confidence = min(abs(r_squared) * (len(stat_values) / 20), 1.0)
        
        return TrendAnalysis(
            trend=trend,
            slope=slope,
            recent_avg=recent_avg,
            earlier_avg=earlier_avg,
            confidence=confidence,
        )
    
    def analyze_rest_impact(
        self,
        player_id: int,
        rest_days: int,
    ) -> float:
        """Calculate player's performance differential on rest days.
        
        Args:
            player_id: Player to analyze
            rest_days: Number of days of rest
            
        Returns:
            Expected points added/subtracted due to rest (positive = better)
        """
        # This would need TeamFeatures to get rest_days per game
        # Simplified version returning 0
        # Full implementation would query TeamFeatures for rest_days
        # then compare performance on rest vs no rest
        return 0.0
    
    def get_momentum_score(
        self,
        player_id: int,
        games: int = 5,
    ) -> float:
        """Get a momentum score (-10 to +10) for a player.
        
        Positive = hot, negative = cold.
        
        Args:
            player_id: Player to score
            games: Recent games to consider
            
        Returns:
            Momentum score
        """
        recent = (
            self.session.query(BoxScore, Game)
            .join(Game, BoxScore.game_id == Game.game_id)
            .filter(BoxScore.player_id == player_id)
            .order_by(Game.game_date.desc())
            .limit(games)
            .all()
        )
        
        if not recent:
            return 0.0
        
        # Get rolling average for comparison
        rolling = (
            self.session.query(PlayerRollingStats)
            .filter(
                PlayerRollingStats.player_id == player_id,
                PlayerRollingStats.games_available_5 >= games,
            )
            .first()
        )
        
        season_avg = rolling.points_avg_5 if rolling else 20  # Default assumption
        
        # Calculate recent average
        recent_avg = np.mean([bs.points for bs, _ in recent if bs.points])
        
        # Momentum = (recent - season) / season * 10
        if season_avg > 0:
            momentum = ((recent_avg - season_avg) / season_avg) * 10
        else:
            momentum = 0.0
        
        return max(-10, min(10, momentum))  # Clamp to [-10, 10]
