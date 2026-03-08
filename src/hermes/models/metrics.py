"""Accuracy metrics -- hit rate, Brier score, MAE, RMSE, calibration."""

import logging
import math
from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from hermes.data.models.prediction import Prediction, PredictionOutcome

logger = logging.getLogger(__name__)

# Prediction types that are binary classification (Brier score applies)
_CLASSIFICATION_TYPES = {"game_winner"}


def compute_metrics(
    session: Session,
    prediction_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> dict:
    """Compute accuracy metrics for predictions.

    For game_winner: hit_rate + brier_score.
    For regression types: hit_rate + MAE + RMSE + CI coverage.

    Args:
        session: SQLAlchemy session.
        prediction_type: Filter to specific type. If None, computes for all.
        start_date: Filter predictions created on or after this date.
        end_date: Filter predictions created on or before this date.

    Returns:
        dict with metrics.
    """
    if prediction_type is None:
        return _compute_all_types(session, start_date, end_date)

    # Build query for resolved predictions
    query = (
        session.query(Prediction, PredictionOutcome)
        .join(PredictionOutcome, Prediction.id == PredictionOutcome.prediction_id)
        .filter(Prediction.prediction_type == prediction_type)
    )

    if start_date:
        query = query.filter(Prediction.created_at >= datetime(start_date.year, start_date.month, start_date.day))
    if end_date:
        end_dt = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)
        query = query.filter(Prediction.created_at <= end_dt)

    rows = query.all()

    # Count total predictions (including unresolved) for this type
    total_query = session.query(Prediction).filter(
        Prediction.prediction_type == prediction_type
    )
    if start_date:
        total_query = total_query.filter(
            Prediction.created_at >= datetime(start_date.year, start_date.month, start_date.day)
        )
    if end_date:
        end_dt = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)
        total_query = total_query.filter(Prediction.created_at <= end_dt)

    total_predictions = total_query.count()
    total_resolved = len(rows)

    if total_resolved == 0:
        return {
            "prediction_type": prediction_type,
            "hit_rate": 0.0,
            "total_predictions": total_predictions,
            "total_resolved": 0,
        }

    # Hit rate
    correct = sum(1 for _, outcome in rows if outcome.is_correct == 1)
    hit_rate = correct / total_resolved

    result = {
        "prediction_type": prediction_type,
        "hit_rate": hit_rate,
        "total_predictions": total_predictions,
        "total_resolved": total_resolved,
    }

    if prediction_type in _CLASSIFICATION_TYPES:
        # Brier score: mean of (predicted_probability - actual)^2
        brier_sum = 0.0
        for pred, outcome in rows:
            prob = pred.win_probability if pred.win_probability is not None else 0.5
            brier_sum += (prob - outcome.actual_value) ** 2
        result["brier_score"] = brier_sum / total_resolved
    else:
        # Regression metrics: MAE, RMSE, CI coverage
        abs_errors = []
        sq_errors = []
        ci_hits = 0
        ci_count = 0

        for pred, outcome in rows:
            err = abs(pred.predicted_value - outcome.actual_value)
            abs_errors.append(err)
            sq_errors.append(err ** 2)

            if pred.confidence_lower is not None and pred.confidence_upper is not None:
                ci_count += 1
                if pred.confidence_lower <= outcome.actual_value <= pred.confidence_upper:
                    ci_hits += 1

        result["mae"] = sum(abs_errors) / len(abs_errors)
        result["rmse"] = math.sqrt(sum(sq_errors) / len(sq_errors))
        if ci_count > 0:
            result["ci_coverage"] = ci_hits / ci_count
        else:
            result["ci_coverage"] = None

    return result


def _compute_all_types(
    session: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> dict:
    """Compute metrics for all prediction types."""
    # Find all distinct types
    types_query = session.query(Prediction.prediction_type).distinct()
    pred_types = [row[0] for row in types_query.all()]

    by_type = {}
    for pt in pred_types:
        by_type[pt] = compute_metrics(session, prediction_type=pt,
                                       start_date=start_date, end_date=end_date)

    return {"by_type": by_type}


def compute_calibration(session: Session, bins: int = 10) -> list:
    """Compute calibration data for game_winner predictions.

    Groups predictions by win_probability into bins and computes
    actual win rate per bin.

    Returns:
        List of dicts with bin_lower, bin_upper, predicted_avg, actual_rate, count.
    """
    rows = (
        session.query(Prediction, PredictionOutcome)
        .join(PredictionOutcome, Prediction.id == PredictionOutcome.prediction_id)
        .filter(Prediction.prediction_type == "game_winner")
        .all()
    )

    if not rows:
        return []

    # Bin predictions by win_probability
    bin_width = 1.0 / bins
    buckets = []

    for i in range(bins):
        bin_lower = i * bin_width
        bin_upper = (i + 1) * bin_width

        bucket_preds = []
        for pred, outcome in rows:
            prob = pred.win_probability if pred.win_probability is not None else 0.5
            if bin_lower <= prob < bin_upper or (i == bins - 1 and prob == bin_upper):
                bucket_preds.append((prob, outcome.actual_value))

        if bucket_preds:
            predicted_avg = sum(p for p, _ in bucket_preds) / len(bucket_preds)
            actual_rate = sum(a for _, a in bucket_preds) / len(bucket_preds)
            buckets.append({
                "bin_lower": bin_lower,
                "bin_upper": bin_upper,
                "predicted_avg": predicted_avg,
                "actual_rate": actual_rate,
                "count": len(bucket_preds),
            })

    return buckets


def format_metrics_report(metrics_dict: dict) -> str:
    """Format metrics as a readable table string for CLI output."""
    lines = []
    lines.append("")
    lines.append(f"{'Type':<20} {'Hit Rate':>10} {'Brier/MAE':>10} {'CI Cov':>10} {'RMSE':>10} {'Resolved':>10}")
    lines.append("-" * 72)

    if "by_type" in metrics_dict:
        for ptype, m in sorted(metrics_dict["by_type"].items()):
            _format_row(lines, m)
    else:
        _format_row(lines, metrics_dict)

    lines.append("")
    return "\n".join(lines)


def _format_row(lines: list, m: dict):
    """Format a single metrics row."""
    ptype = m.get("prediction_type", "unknown")
    hit_rate = f"{m.get('hit_rate', 0):.1%}"
    resolved = str(m.get("total_resolved", 0))

    if "brier_score" in m:
        score = f"{m['brier_score']:.4f}"
    elif "mae" in m:
        score = f"{m['mae']:.2f}"
    else:
        score = "N/A"

    ci_cov = f"{m['ci_coverage']:.1%}" if m.get("ci_coverage") is not None else "N/A"
    rmse = f"{m['rmse']:.2f}" if "rmse" in m else "N/A"

    lines.append(f"{ptype:<20} {hit_rate:>10} {score:>10} {ci_cov:>10} {rmse:>10} {resolved:>10}")
