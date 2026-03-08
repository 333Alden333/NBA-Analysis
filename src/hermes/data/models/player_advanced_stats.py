"""PlayerAdvancedStats model -- TS%, USG%, simplified PER per game."""

from sqlalchemy import Integer, String, Float, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class PlayerAdvancedStats(Base):
    __tablename__ = "player_advanced_stats"
    __table_args__ = (
        UniqueConstraint("player_id", "game_id", name="uq_player_game_advanced"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.player_id"), index=True)
    game_id: Mapped[str] = mapped_column(String(10), ForeignKey("games.game_id"), index=True)
    game_date: Mapped[str | None] = mapped_column(Date, nullable=True, index=True)

    true_shooting_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    usage_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    simplified_per: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Team-level inputs stored for auditability
    team_fga: Mapped[int | None] = mapped_column(Integer, nullable=True)
    team_fta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    team_tov: Mapped[int | None] = mapped_column(Integer, nullable=True)
    team_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
