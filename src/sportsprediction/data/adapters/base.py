"""Abstract data source adapter interfaces."""

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class NBADataAdapter(ABC):
    """Abstract interface for NBA data sources."""

    @abstractmethod
    def get_player_info(self, player_id: int) -> dict[str, Any]:
        """Get player biographical info."""
        ...

    @abstractmethod
    def get_player_game_log(self, player_id: int, season: str) -> pd.DataFrame:
        """Get player game log for a season. Season format: '2024-25'."""
        ...

    @abstractmethod
    def get_game_box_score(self, game_id: str) -> dict[str, pd.DataFrame]:
        """Get box score for a game. Returns dict of DataFrames."""
        ...

    @abstractmethod
    def get_play_by_play(self, game_id: str) -> pd.DataFrame:
        """Get play-by-play for a game."""
        ...

    @abstractmethod
    def get_shot_chart(self, game_id: str, player_id: int | None = None) -> pd.DataFrame:
        """Get shot chart detail for a game, optionally filtered by player."""
        ...

    @abstractmethod
    def get_league_standings(self, season: str) -> pd.DataFrame:
        """Get league standings for a season."""
        ...

    @abstractmethod
    def get_season_games(self, season: str) -> pd.DataFrame:
        """Get all games for a season (for historical load)."""
        ...

    @abstractmethod
    def get_schedule(self, season: str) -> pd.DataFrame:
        """Get schedule for a season."""
        ...


class InjuryDataAdapter(ABC):
    """Abstract interface for injury data sources."""

    @abstractmethod
    def get_current_injuries(self) -> pd.DataFrame:
        """Get current injury report."""
        ...
