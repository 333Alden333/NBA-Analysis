"""PlayByPlay model."""

from sqlalchemy import Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class PlayByPlay(Base):
    __tablename__ = "play_by_play"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[str] = mapped_column(String(10), ForeignKey("games.game_id"), index=True)
    event_num: Mapped[int | None] = mapped_column(Integer, nullable=True)
    period: Mapped[int | None] = mapped_column(Integer, nullable=True)
    clock: Mapped[str | None] = mapped_column(String(10), nullable=True)
    event_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    player1_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    player2_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    player3_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    team_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_home: Mapped[str | None] = mapped_column(String(10), nullable=True)
    score_away: Mapped[str | None] = mapped_column(String(10), nullable=True)
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)
