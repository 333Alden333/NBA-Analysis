"""Rolling average computation for player stats over 5/10/20 game windows.

Temporal discipline: rolling averages for game N use ONLY games BEFORE game N.
DNP games (minutes=0 or NULL) are excluded from windows.
"""

import numpy as np
import pandas as pd
from sqlalchemy import and_
from sqlalchemy.orm import Session

from sportsprediction.data.models import BoxScore, Game, PlayerRollingStats

ROLLING_STATS = [
    "points", "rebounds", "assists", "steals", "blocks", "turnovers",
    "fg_pct", "fg3_pct", "ft_pct", "minutes", "plus_minus", "offensive_rebounds",
]
WINDOWS = [5, 10, 20]


def compute_rolling_stats(session: Session, player_id: int, as_of_date=None) -> None:
    """Compute and persist rolling averages for a player.

    Args:
        session: SQLAlchemy session.
        player_id: Player to compute for.
        as_of_date: If provided, only process games before this date.
    """
    # Query box scores joined with games, excluding DNPs
    query = (
        session.query(BoxScore, Game.game_date, Game.game_id)
        .join(Game, BoxScore.game_id == Game.game_id)
        .filter(
            BoxScore.player_id == player_id,
            BoxScore.minutes > 0,
            BoxScore.minutes.isnot(None),
        )
    )
    if as_of_date is not None:
        query = query.filter(Game.game_date < as_of_date)

    query = query.order_by(Game.game_date.asc())
    results = query.all()

    if not results:
        return

    # Build DataFrame from query results
    rows = []
    for bs, game_date, game_id in results:
        # Compute per-game shooting percentages with division safety
        fga = bs.fga or 0
        fg3a = bs.fg3a or 0
        fta = bs.fta or 0
        fg_pct = (bs.fgm / fga) if fga > 0 else 0.0
        fg3_pct = (bs.fg3m / fg3a) if fg3a > 0 else 0.0
        ft_pct = (bs.ftm / fta) if fta > 0 else 0.0

        rows.append({
            "game_id": game_id,
            "game_date": game_date,
            "points": float(bs.points or 0),
            "rebounds": float(bs.rebounds or 0),
            "assists": float(bs.assists or 0),
            "steals": float(bs.steals or 0),
            "blocks": float(bs.blocks or 0),
            "turnovers": float(bs.turnovers or 0),
            "fg_pct": fg_pct,
            "fg3_pct": fg3_pct,
            "ft_pct": ft_pct,
            "minutes": float(bs.minutes or 0),
            "plus_minus": float(bs.plus_minus or 0),
            "offensive_rebounds": float(bs.offensive_rebounds or 0),
        })

    df = pd.DataFrame(rows)

    # Compute rolling averages for each window
    for window in WINDOWS:
        for stat in ROLLING_STATS:
            col_name = f"{stat}_avg_{window}"
            # Rolling mean with min_periods=1
            rolling_vals = df[stat].rolling(window=window, min_periods=1).mean()
            # Shift by 1 for temporal discipline: game N uses only prior games
            df[col_name] = rolling_vals.shift(1)

        # Games available count
        ga_col = f"games_available_{window}"
        count_vals = df["points"].rolling(window=window, min_periods=1).count()
        df[ga_col] = count_vals.shift(1)

    # Persist to PlayerRollingStats
    for _, row in df.iterrows():
        kwargs = {
            "player_id": player_id,
            "game_id": row["game_id"],
            "game_date": row["game_date"],
        }

        for window in WINDOWS:
            for stat in ROLLING_STATS:
                col = f"{stat}_avg_{window}"
                val = row[col]
                kwargs[col] = None if pd.isna(val) else float(val)

            ga_col = f"games_available_{window}"
            ga_val = row[ga_col]
            kwargs[ga_col] = None if pd.isna(ga_val) else int(ga_val)

        # Upsert via merge
        existing = session.query(PlayerRollingStats).filter_by(
            player_id=player_id, game_id=row["game_id"]
        ).first()

        if existing:
            for k, v in kwargs.items():
                if k not in ("player_id", "game_id"):
                    setattr(existing, k, v)
        else:
            obj = PlayerRollingStats(**kwargs)
            session.add(obj)

    session.flush()


def compute_rolling_stats_for_games(session: Session, game_ids: list) -> None:
    """Compute rolling stats for all players in the given games.

    Args:
        session: SQLAlchemy session.
        game_ids: List of game IDs to process.
    """
    # Find all unique player_ids in those games
    player_ids = (
        session.query(BoxScore.player_id)
        .filter(BoxScore.game_id.in_(game_ids))
        .distinct()
        .all()
    )

    for (pid,) in player_ids:
        compute_rolling_stats(session, player_id=pid)
