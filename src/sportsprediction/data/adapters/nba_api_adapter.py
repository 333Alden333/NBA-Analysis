"""Concrete NBA data adapter wrapping nba_api library endpoints."""

import logging
from typing import Any

import pandas as pd
from nba_api.stats.endpoints import (
    commonplayerinfo,
    playergamelog,
    boxscoretraditionalv3,
    playbyplayv3,
    shotchartdetail,
    leaguestandingsv3,
    leaguegamefinder,
    scheduleleaguev2,
)

from sportsprediction.data.adapters.base import NBADataAdapter
from sportsprediction.data.ingestion.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class NbaApiAdapter(NBADataAdapter):
    """NBA data adapter using the nba_api library (V3 endpoints)."""

    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter

    def get_player_info(self, player_id: int) -> dict[str, Any]:
        """Get player biographical info from CommonPlayerInfo."""
        self.rate_limiter.wait()
        endpoint = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
        df = endpoint.get_data_frames()[0]
        return df.iloc[0].to_dict()

    def get_player_game_log(self, player_id: int, season: str) -> pd.DataFrame:
        """Get player game log for a season."""
        self.rate_limiter.wait()
        endpoint = playergamelog.PlayerGameLog(
            player_id=player_id, season=season
        )
        return endpoint.get_data_frames()[0]

    def get_game_box_score(self, game_id: str) -> dict[str, pd.DataFrame]:
        """Get box score (V3). Returns PlayerStats and TeamStats DataFrames."""
        self.rate_limiter.wait()
        endpoint = boxscoretraditionalv3.BoxScoreTraditionalV3(game_id=game_id)
        dfs = endpoint.get_data_frames()
        return {"PlayerStats": dfs[0], "TeamStats": dfs[1]}

    def get_play_by_play(self, game_id: str) -> pd.DataFrame:
        """Get play-by-play data (V3)."""
        self.rate_limiter.wait()
        endpoint = playbyplayv3.PlayByPlayV3(game_id=game_id)
        return endpoint.get_data_frames()[0]

    def get_shot_chart(
        self, game_id: str, player_id: int | None = None
    ) -> pd.DataFrame:
        """Get shot chart detail for a game."""
        self.rate_limiter.wait()
        endpoint = shotchartdetail.ShotChartDetail(
            team_id=0,
            player_id=player_id or 0,
            game_id_nullable=game_id,
            season_nullable="",
            context_measure_simple="FGA",
        )
        return endpoint.get_data_frames()[0]

    def get_league_standings(self, season: str) -> pd.DataFrame:
        """Get league standings (V3)."""
        self.rate_limiter.wait()
        endpoint = leaguestandingsv3.LeagueStandingsV3(season=season)
        return endpoint.get_data_frames()[0]

    def get_season_games(self, season: str) -> pd.DataFrame:
        """Get all games for a season via LeagueGameFinder."""
        self.rate_limiter.wait()
        endpoint = leaguegamefinder.LeagueGameFinder(
            season_nullable=season, league_id_nullable="00"
        )
        return endpoint.get_data_frames()[0]

    def get_schedule(self, season: str) -> pd.DataFrame:
        """Get schedule for a season."""
        self.rate_limiter.wait()
        endpoint = scheduleleaguev2.ScheduleLeagueV2(season=season)
        return endpoint.get_data_frames()[0]
