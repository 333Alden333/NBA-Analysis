"""add prediction tables

Revision ID: 003_predictions
Revises: 83f355add86d
Create Date: 2026-03-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_predictions'
down_revision: Union[str, None] = '83f355add86d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'predictions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('game_id', sa.String(length=10), nullable=False),
        sa.Column('prediction_type', sa.String(length=20), nullable=False),
        sa.Column('player_id', sa.Integer(), nullable=True),
        sa.Column('predicted_value', sa.Float(), nullable=False),
        sa.Column('confidence_lower', sa.Float(), nullable=True),
        sa.Column('confidence_upper', sa.Float(), nullable=True),
        sa.Column('win_probability', sa.Float(), nullable=True),
        sa.Column('model_version', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['game_id'], ['games.game_id']),
        sa.ForeignKeyConstraint(['player_id'], ['players.player_id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'game_id', 'prediction_type', 'player_id', 'model_version',
            name='uq_prediction_game_type_player_model',
        ),
    )

    op.create_table(
        'prediction_outcomes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('prediction_id', sa.Integer(), nullable=False),
        sa.Column('actual_value', sa.Float(), nullable=False),
        sa.Column('is_correct', sa.Integer(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['prediction_id'], ['predictions.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('prediction_outcomes')
    op.drop_table('predictions')
