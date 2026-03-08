"""TeamFeatures model -- pace, ratings, rest days per team per game."""

from sqlalchemy import Integer, String, Float, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class TeamFeatures(Base):
    __tablename__ = "team_features"
    __table_args__ = (
        UniqueConstraint("team_id", "game_id", name="uq_team_game_features"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.team_id"), index=True)
    game_id: Mapped[str] = mapped_column(String(10), ForeignKey("games.game_id"), index=True)
    game_date: Mapped[str | None] = mapped_column(Date, nullable=True, index=True)

    pace: Mapped[float | None] = mapped_column(Float, nullable=True)
    offensive_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    defensive_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    rest_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    possessions: Mapped[float | None] = mapped_column(Float, nullable=True)
    opponent_possessions: Mapped[float | None] = mapped_column(Float, nullable=True)
    season_win_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
