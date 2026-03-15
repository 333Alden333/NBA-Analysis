"""MatchupStats model -- player historical performance vs specific teams."""

from sqlalchemy import Integer, String, Float, Boolean, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class MatchupStats(Base):
    __tablename__ = "matchup_stats"
    __table_args__ = (
        UniqueConstraint("player_id", "game_id", name="uq_player_game_matchup"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.player_id"), index=True)
    game_id: Mapped[str] = mapped_column(String(10), ForeignKey("games.game_id"), index=True)
    game_date: Mapped[str | None] = mapped_column(Date, nullable=True, index=True)
    opponent_team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.team_id"), index=True)

    matchup_games_played: Mapped[int | None] = mapped_column(Integer, nullable=True)
    has_matchup_history: Mapped[bool] = mapped_column(Boolean, default=False)

    # Matchup averages
    matchup_avg_points: Mapped[float | None] = mapped_column(Float, nullable=True)
    matchup_avg_rebounds: Mapped[float | None] = mapped_column(Float, nullable=True)
    matchup_avg_assists: Mapped[float | None] = mapped_column(Float, nullable=True)
    matchup_avg_fg_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    matchup_avg_plus_minus: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Difference from player's overall average
    matchup_diff_points: Mapped[float | None] = mapped_column(Float, nullable=True)
    matchup_diff_rebounds: Mapped[float | None] = mapped_column(Float, nullable=True)
    matchup_diff_assists: Mapped[float | None] = mapped_column(Float, nullable=True)
    matchup_diff_fg_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    matchup_diff_plus_minus: Mapped[float | None] = mapped_column(Float, nullable=True)
