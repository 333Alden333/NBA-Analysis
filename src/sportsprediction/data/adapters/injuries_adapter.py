"""Concrete InjuryDataAdapter wrapping the nbainjuries package."""

import logging
from datetime import datetime

import pandas as pd

from .base import InjuryDataAdapter

logger = logging.getLogger(__name__)

try:
    from nbainjuries import injury
except Exception:
    injury = None
    logger.warning("nbainjuries package not available (requires Java 8+). Injury adapter will return empty data.")


class NbaInjuriesAdapter(InjuryDataAdapter):
    """Adapter that fetches current NBA injury reports via nbainjuries."""

    def get_current_injuries(self) -> pd.DataFrame:
        """Get current injury report. Returns empty DataFrame if unavailable."""
        if injury is None:
            logger.warning("nbainjuries not available; returning empty DataFrame.")
            return pd.DataFrame()

        try:
            df = injury.get_reportdata(datetime.now(), return_df=True)
            if df is None:
                return pd.DataFrame()
            return df
        except Exception as e:
            logger.error("Failed to fetch injury report: %s", e)
            return pd.DataFrame()
