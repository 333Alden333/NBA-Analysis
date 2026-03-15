"""Advanced matchup pattern recognition.

FEAT-03b: Classifies matchup types and detects performance trends.
"""

from .classifier import MatchupClassifier, MatchupType
from .detector import PatternDetector, MatchupPattern
from .trends import TrendAnalyzer, PerformanceTrend

__all__ = [
    "MatchupClassifier",
    "MatchupType", 
    "PatternDetector",
    "MatchupPattern",
    "TrendAnalyzer",
    "PerformanceTrend",
]
