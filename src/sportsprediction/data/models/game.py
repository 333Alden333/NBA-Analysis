"""Game model."""

from sqlalchemy import Integer, String, Text, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Game(Base):
    __tablename__ = "games"

    game_id: Mapped[str] = mapped_column(String(10), primary_key=True)
    season: Mapped[str | None] = mapped_column(String(10), nullable=True)
    game_date: Mapped[str | None] = mapped_column(Date, nullable=True)
    home_team_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("teams.team_id"), nullable=True)
    away_team_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("teams.team_id"), nullable=True)
    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)
