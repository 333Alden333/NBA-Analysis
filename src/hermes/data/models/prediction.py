"""Prediction and PredictionOutcome models."""

from datetime import datetime

from sqlalchemy import (
    Integer, String, Float, Text, DateTime, ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        UniqueConstraint(
            "game_id", "prediction_type", "player_id", "model_version",
            name="uq_prediction_game_type_player_model",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(
        String(10), ForeignKey("games.game_id"), nullable=False
    )
    prediction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    player_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("players.player_id"), nullable=True
    )
    predicted_value: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_lower: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_upper: Mapped[float | None] = mapped_column(Float, nullable=True)
    win_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_version: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class PredictionOutcome(Base):
    __tablename__ = "prediction_outcomes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prediction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("predictions.id"), nullable=False
    )
    actual_value: Mapped[float] = mapped_column(Float, nullable=False)
    is_correct: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
