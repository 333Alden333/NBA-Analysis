"""BoxScore model."""

from sqlalchemy import Integer, String, Float, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class BoxScore(Base):
    __tablename__ = "box_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[str] = mapped_column(String(10), ForeignKey("games.game_id"), index=True)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.player_id"), index=True)
    team_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("teams.team_id"), nullable=True)
    minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rebounds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assists: Mapped[int | None] = mapped_column(Integer, nullable=True)
    steals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    blocks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    turnovers: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fgm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fga: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fg3m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fg3a: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ftm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    plus_minus: Mapped[float | None] = mapped_column(Float, nullable=True)
    offensive_rebounds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    defensive_rebounds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    personal_fouls: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)
