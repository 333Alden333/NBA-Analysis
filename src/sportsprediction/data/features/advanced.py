"""Advanced stat computation: TS%, USG%, simplified PER per game.

All pure formula functions handle division by zero by returning 0.0.
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from sportsprediction.data.models import BoxScore, Game, PlayerAdvancedStats


def compute_true_shooting_pct(points: float, fga: float, fta: float) -> float:
    """TS% = PTS / (2 * (FGA + 0.44 * FTA)).

    Returns 0.0 if denominator is zero.
    """
    denom = 2.0 * (fga + 0.44 * fta)
    if denom == 0:
        return 0.0
    return points / denom


def compute_usage_rate(
    fga: float, fta: float, tov: float, minutes: float,
    team_fga: float, team_fta: float, team_tov: float, team_minutes: float,
) -> float:
    """USG% = 100 * ((FGA + 0.44*FTA + TOV) * (TmMP/5)) / (MP * (TmFGA + 0.44*TmFTA + TmTOV)).

    Returns 0.0 if any denominator component is zero.
    """
    team_possessions = team_fga + 0.44 * team_fta + team_tov
    if minutes == 0 or team_possessions == 0 or team_minutes == 0:
        return 0.0
    numerator = (fga + 0.44 * fta + tov) * (team_minutes / 5.0)
    denominator = minutes * team_possessions
    return 100.0 * numerator / denominator


def compute_simplified_per(
    points: float, rebounds: float, assists: float,
    steals: float, blocks: float, turnovers: float,
    fgm: float, fga: float, ftm: float, fta: float,
    minutes: float,
) -> float:
    """Simplified PER = (positive - negative) / minutes * 15.

    Positive = points + rebounds + assists + steals + blocks
    Negative = turnovers + missed_fg + missed_ft

    Returns 0.0 if minutes is zero.
    """
    if minutes == 0:
        return 0.0
    positive = points + rebounds + assists + steals + blocks
    missed_fg = fga - fgm
    missed_ft = fta - ftm
    negative = turnovers + missed_fg + missed_ft
    return (positive - negative) / minutes * 15.0


def compute_advanced_stats(session: Session, player_id: int, as_of_date=None) -> None:
    """Compute and persist advanced stats for a player.

    Args:
        session: SQLAlchemy session.
        player_id: Player to compute for.
        as_of_date: If provided, only process games before this date.
    """
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

    for bs, game_date, game_id in results:
        # Get team totals for this game
        team_totals = (
            session.query(
                func.sum(BoxScore.fga).label("team_fga"),
                func.sum(BoxScore.fta).label("team_fta"),
                func.sum(BoxScore.turnovers).label("team_tov"),
                func.sum(BoxScore.minutes).label("team_minutes"),
            )
            .filter(
                BoxScore.game_id == game_id,
                BoxScore.team_id == bs.team_id,
            )
            .one()
        )

        t_fga = team_totals.team_fga or 0
        t_fta = team_totals.team_fta or 0
        t_tov = team_totals.team_tov or 0
        t_min = float(team_totals.team_minutes or 0)

        points = bs.points or 0
        fga = bs.fga or 0
        fta = bs.fta or 0
        fgm = bs.fgm or 0
        ftm = bs.ftm or 0
        minutes = float(bs.minutes or 0)
        tov = bs.turnovers or 0
        rebounds = bs.rebounds or 0
        assists = bs.assists or 0
        steals = bs.steals or 0
        blocks = bs.blocks or 0

        ts_pct = compute_true_shooting_pct(points, fga, fta)
        usg = compute_usage_rate(fga, fta, tov, minutes, t_fga, t_fta, t_tov, t_min)
        per = compute_simplified_per(
            points, rebounds, assists, steals, blocks, tov,
            fgm, fga, ftm, fta, minutes,
        )

        # Upsert
        existing = session.query(PlayerAdvancedStats).filter_by(
            player_id=player_id, game_id=game_id
        ).first()

        kwargs = dict(
            player_id=player_id,
            game_id=game_id,
            game_date=game_date,
            true_shooting_pct=ts_pct,
            usage_rate=usg,
            simplified_per=per,
            team_fga=t_fga,
            team_fta=t_fta,
            team_tov=t_tov,
            team_minutes=t_min,
        )

        if existing:
            for k, v in kwargs.items():
                if k not in ("player_id", "game_id"):
                    setattr(existing, k, v)
        else:
            obj = PlayerAdvancedStats(**kwargs)
            session.add(obj)

    session.flush()


def compute_advanced_stats_for_games(session: Session, game_ids: list) -> None:
    """Compute advanced stats for all players in the given games."""
    player_ids = (
        session.query(BoxScore.player_id)
        .filter(BoxScore.game_id.in_(game_ids))
        .distinct()
        .all()
    )

    for (pid,) in player_ids:
        compute_advanced_stats(session, player_id=pid)
