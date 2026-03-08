"""PlayerRollingStats model -- rolling averages over 5/10/20 game windows."""

from sqlalchemy import Integer, String, Float, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

# Stats tracked with rolling windows
_STATS = [
    "points", "rebounds", "assists", "steals", "blocks", "turnovers",
    "fg_pct", "fg3_pct", "ft_pct", "minutes", "plus_minus",
    "offensive_rebounds",
]
_WINDOWS = [5, 10, 20]


class PlayerRollingStats(Base):
    __tablename__ = "player_rolling_stats"
    __table_args__ = (
        UniqueConstraint("player_id", "game_id", name="uq_player_game_rolling"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.player_id"), index=True)
    game_id: Mapped[str] = mapped_column(String(10), ForeignKey("games.game_id"), index=True)
    game_date: Mapped[str | None] = mapped_column(Date, nullable=True, index=True)

    # 12 stats x 3 windows = 36 rolling average columns
    points_avg_5: Mapped[float | None] = mapped_column(Float, nullable=True)
    points_avg_10: Mapped[float | None] = mapped_column(Float, nullable=True)
    points_avg_20: Mapped[float | None] = mapped_column(Float, nullable=True)

    rebounds_avg_5: Mapped[float | None] = mapped_column(Float, nullable=True)
    rebounds_avg_10: Mapped[float | None] = mapped_column(Float, nullable=True)
    rebounds_avg_20: Mapped[float | None] = mapped_column(Float, nullable=True)

    assists_avg_5: Mapped[float | None] = mapped_column(Float, nullable=True)
    assists_avg_10: Mapped[float | None] = mapped_column(Float, nullable=True)
    assists_avg_20: Mapped[float | None] = mapped_column(Float, nullable=True)

    steals_avg_5: Mapped[float | None] = mapped_column(Float, nullable=True)
    steals_avg_10: Mapped[float | None] = mapped_column(Float, nullable=True)
    steals_avg_20: Mapped[float | None] = mapped_column(Float, nullable=True)

    blocks_avg_5: Mapped[float | None] = mapped_column(Float, nullable=True)
    blocks_avg_10: Mapped[float | None] = mapped_column(Float, nullable=True)
    blocks_avg_20: Mapped[float | None] = mapped_column(Float, nullable=True)

    turnovers_avg_5: Mapped[float | None] = mapped_column(Float, nullable=True)
    turnovers_avg_10: Mapped[float | None] = mapped_column(Float, nullable=True)
    turnovers_avg_20: Mapped[float | None] = mapped_column(Float, nullable=True)

    fg_pct_avg_5: Mapped[float | None] = mapped_column(Float, nullable=True)
    fg_pct_avg_10: Mapped[float | None] = mapped_column(Float, nullable=True)
    fg_pct_avg_20: Mapped[float | None] = mapped_column(Float, nullable=True)

    fg3_pct_avg_5: Mapped[float | None] = mapped_column(Float, nullable=True)
    fg3_pct_avg_10: Mapped[float | None] = mapped_column(Float, nullable=True)
    fg3_pct_avg_20: Mapped[float | None] = mapped_column(Float, nullable=True)

    ft_pct_avg_5: Mapped[float | None] = mapped_column(Float, nullable=True)
    ft_pct_avg_10: Mapped[float | None] = mapped_column(Float, nullable=True)
    ft_pct_avg_20: Mapped[float | None] = mapped_column(Float, nullable=True)

    minutes_avg_5: Mapped[float | None] = mapped_column(Float, nullable=True)
    minutes_avg_10: Mapped[float | None] = mapped_column(Float, nullable=True)
    minutes_avg_20: Mapped[float | None] = mapped_column(Float, nullable=True)

    plus_minus_avg_5: Mapped[float | None] = mapped_column(Float, nullable=True)
    plus_minus_avg_10: Mapped[float | None] = mapped_column(Float, nullable=True)
    plus_minus_avg_20: Mapped[float | None] = mapped_column(Float, nullable=True)

    offensive_rebounds_avg_5: Mapped[float | None] = mapped_column(Float, nullable=True)
    offensive_rebounds_avg_10: Mapped[float | None] = mapped_column(Float, nullable=True)
    offensive_rebounds_avg_20: Mapped[float | None] = mapped_column(Float, nullable=True)

    # How many games were actually available for each window
    games_available_5: Mapped[int | None] = mapped_column(Integer, nullable=True)
    games_available_10: Mapped[int | None] = mapped_column(Integer, nullable=True)
    games_available_20: Mapped[int | None] = mapped_column(Integer, nullable=True)
