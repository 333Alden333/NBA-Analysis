"""Matchup feature computation -- player historical performance vs specific teams.

FEAT-03: Computes matchup averages and diffs for player-vs-team-defense history.
"""

import datetime
from typing import Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from hermes.data.models import BoxScore, Game, MatchupStats

# Minimum number of historical matchup games to produce stats
MATCHUP_MIN_GAMES = 3

# Lookback window: only use games within this many years
LOOKBACK_YEARS = 3


def _get_opponent_team_id(game: Game, player_team_id: int) -> int:
    """Determine opponent team from game and player's team."""
    if player_team_id == game.home_team_id:
        return game.away_team_id
    return game.home_team_id


def _compute_fg_pct(fgm: Optional[int], fga: Optional[int]) -> Optional[float]:
    """Compute field goal percentage with zero-division safety."""
    if fga is None or fga == 0 or fgm is None:
        return None
    return fgm / fga


def compute_matchup_stats(
    session: Session,
    player_id: int,
    as_of_date: Optional[datetime.date] = None,
) -> list[MatchupStats]:
    """Compute matchup features for a player across all their games.

    For each game the player has played, computes their historical average
    performance against that game's opponent team (using only prior games).

    Args:
        session: SQLAlchemy session.
        player_id: Player to compute matchup stats for.
        as_of_date: If set, only compute for games on or before this date.

    Returns:
        List of MatchupStats records upserted.
    """
    # Get all box scores for this player, joined with game info
    player_games = (
        session.query(BoxScore, Game)
        .join(Game, BoxScore.game_id == Game.game_id)
        .filter(BoxScore.player_id == player_id)
        .order_by(Game.game_date.asc())
        .all()
    )

    if not player_games:
        return []

    results = []

    for idx, (box_score, game) in enumerate(player_games):
        if as_of_date and game.game_date > as_of_date:
            continue

        opponent_team_id = _get_opponent_team_id(game, box_score.team_id)

        # Lookback cutoff: 3 years before this game
        lookback_cutoff = game.game_date - datetime.timedelta(days=LOOKBACK_YEARS * 365)

        # Find all prior games by this player against the same opponent
        prior_matchup_games = []
        prior_all_games = []

        for prev_bs, prev_game in player_games[:idx]:
            if prev_game.game_date >= game.game_date:
                continue  # Temporal discipline: only use prior data
            if prev_game.game_date < lookback_cutoff:
                continue  # Outside lookback window

            prior_all_games.append(prev_bs)

            prev_opponent = _get_opponent_team_id(prev_game, prev_bs.team_id)
            if prev_opponent == opponent_team_id:
                prior_matchup_games.append(prev_bs)

        matchup_count = len(prior_matchup_games)
        has_history = matchup_count >= MATCHUP_MIN_GAMES

        # Build stat record
        matchup_record = {
            "player_id": player_id,
            "game_id": game.game_id,
            "game_date": game.game_date,
            "opponent_team_id": opponent_team_id,
            "matchup_games_played": matchup_count,
            "has_matchup_history": has_history,
        }

        if has_history:
            # Compute matchup averages
            matchup_record["matchup_avg_points"] = _mean([g.points for g in prior_matchup_games])
            matchup_record["matchup_avg_rebounds"] = _mean([g.rebounds for g in prior_matchup_games])
            matchup_record["matchup_avg_assists"] = _mean([g.assists for g in prior_matchup_games])
            matchup_record["matchup_avg_fg_pct"] = _mean([
                _compute_fg_pct(g.fgm, g.fga) for g in prior_matchup_games
            ])
            matchup_record["matchup_avg_plus_minus"] = _mean([g.plus_minus for g in prior_matchup_games])

            # Compute overall averages (all opponents, within lookback)
            # Include matchup games too -- overall means ALL games
            overall_avg_points = _mean([g.points for g in prior_all_games])
            overall_avg_rebounds = _mean([g.rebounds for g in prior_all_games])
            overall_avg_assists = _mean([g.assists for g in prior_all_games])
            overall_avg_fg_pct = _mean([_compute_fg_pct(g.fgm, g.fga) for g in prior_all_games])
            overall_avg_plus_minus = _mean([g.plus_minus for g in prior_all_games])

            # Diffs
            matchup_record["matchup_diff_points"] = _safe_diff(
                matchup_record["matchup_avg_points"], overall_avg_points
            )
            matchup_record["matchup_diff_rebounds"] = _safe_diff(
                matchup_record["matchup_avg_rebounds"], overall_avg_rebounds
            )
            matchup_record["matchup_diff_assists"] = _safe_diff(
                matchup_record["matchup_avg_assists"], overall_avg_assists
            )
            matchup_record["matchup_diff_fg_pct"] = _safe_diff(
                matchup_record["matchup_avg_fg_pct"], overall_avg_fg_pct
            )
            matchup_record["matchup_diff_plus_minus"] = _safe_diff(
                matchup_record["matchup_avg_plus_minus"], overall_avg_plus_minus
            )
        else:
            # Below threshold -- NULL everything
            for col in [
                "matchup_avg_points", "matchup_avg_rebounds", "matchup_avg_assists",
                "matchup_avg_fg_pct", "matchup_avg_plus_minus",
                "matchup_diff_points", "matchup_diff_rebounds", "matchup_diff_assists",
                "matchup_diff_fg_pct", "matchup_diff_plus_minus",
            ]:
                matchup_record[col] = None

        # Upsert
        existing = session.query(MatchupStats).filter_by(
            player_id=player_id, game_id=game.game_id
        ).first()

        if existing:
            for key, value in matchup_record.items():
                setattr(existing, key, value)
            results.append(existing)
        else:
            ms = MatchupStats(**matchup_record)
            session.add(ms)
            results.append(ms)

    session.flush()
    return results


def compute_matchup_stats_for_games(
    session: Session,
    game_ids: list[str],
) -> list[MatchupStats]:
    """Compute matchup stats for all players in the given games.

    Args:
        session: SQLAlchemy session.
        game_ids: List of game IDs to process.

    Returns:
        List of all MatchupStats records created/updated.
    """
    # Find all player_ids in those games
    player_ids = (
        session.query(BoxScore.player_id)
        .filter(BoxScore.game_id.in_(game_ids))
        .distinct()
        .all()
    )

    all_results = []
    for (pid,) in player_ids:
        all_results.extend(compute_matchup_stats(session, player_id=pid))

    return all_results


def _mean(values: list) -> Optional[float]:
    """Compute mean of non-None values. Returns None if all are None."""
    filtered = [v for v in values if v is not None]
    if not filtered:
        return None
    return sum(filtered) / len(filtered)


def _safe_diff(a: Optional[float], b: Optional[float]) -> Optional[float]:
    """Compute a - b, returning None if either is None."""
    if a is None or b is None:
        return None
    return a - b
