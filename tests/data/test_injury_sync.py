"""Tests for injury sync function."""

import json
from datetime import datetime

import pandas as pd
import pytest

from sportsprediction.data.adapters.base import InjuryDataAdapter
from sportsprediction.data.models.injury import Injury
from sportsprediction.data.models.sync_log import SyncLog


class MockInjuryDataAdapter(InjuryDataAdapter):
    """Mock adapter returning fixture data."""

    def __init__(self, data=None, error=False):
        self._data = data
        self._error = error

    def get_current_injuries(self) -> pd.DataFrame:
        if self._error:
            raise RuntimeError("Adapter failure")
        if self._data is not None:
            return self._data
        return pd.DataFrame(
            {
                "Player Name": ["LeBron James", "Stephen Curry"],
                "Team": ["LAL", "GSW"],
                "Game Date": ["2026-03-08", "2026-03-08"],
                "Game Time": ["7:00 PM", "7:30 PM"],
                "Matchup": ["LAL vs GSW", "GSW vs LAL"],
                "Current Status": ["Out", "Questionable"],
                "Reason": ["Ankle", "Knee"],
            }
        )


class TestSyncInjuries:
    def test_accepts_abstract_adapter(self, session):
        from sportsprediction.data.ingestion.injury_sync import sync_injuries

        import inspect

        sig = inspect.signature(sync_injuries)
        # Should work with any InjuryDataAdapter, not just concrete
        adapter = MockInjuryDataAdapter()
        sync_injuries(adapter, session)

    def test_creates_injury_records(self, session):
        from sportsprediction.data.ingestion.injury_sync import sync_injuries

        adapter = MockInjuryDataAdapter()
        sync_injuries(adapter, session)
        injuries = session.query(Injury).all()
        assert len(injuries) == 2
        assert injuries[0].player_name == "LeBron James"
        assert injuries[1].player_name == "Stephen Curry"

    def test_stores_raw_json(self, session):
        from sportsprediction.data.ingestion.injury_sync import sync_injuries

        adapter = MockInjuryDataAdapter()
        sync_injuries(adapter, session)
        injury = session.query(Injury).first()
        assert injury.raw_json is not None
        raw = json.loads(injury.raw_json)
        assert "Player Name" in raw

    def test_writes_sync_log(self, session):
        from sportsprediction.data.ingestion.injury_sync import sync_injuries

        adapter = MockInjuryDataAdapter()
        sync_injuries(adapter, session)
        log = session.query(SyncLog).filter_by(entity_type="injuries").first()
        assert log is not None
        assert log.records_synced == 2
        assert log.status == "success"

    def test_clears_old_records_on_resync(self, session):
        from sportsprediction.data.ingestion.injury_sync import sync_injuries

        adapter = MockInjuryDataAdapter()
        sync_injuries(adapter, session)
        assert session.query(Injury).count() == 2

        # Re-sync with single record
        single = pd.DataFrame(
            {
                "Player Name": ["Anthony Davis"],
                "Team": ["LAL"],
                "Game Date": ["2026-03-08"],
                "Game Time": ["7:00 PM"],
                "Matchup": ["LAL vs BOS"],
                "Current Status": ["Doubtful"],
                "Reason": ["Back"],
            }
        )
        adapter2 = MockInjuryDataAdapter(data=single)
        sync_injuries(adapter2, session)
        assert session.query(Injury).count() == 1
        assert session.query(Injury).first().player_name == "Anthony Davis"

    def test_handles_empty_report(self, session):
        from sportsprediction.data.ingestion.injury_sync import sync_injuries

        adapter = MockInjuryDataAdapter(data=pd.DataFrame())
        sync_injuries(adapter, session)
        assert session.query(Injury).count() == 0
        log = session.query(SyncLog).filter_by(entity_type="injuries").first()
        assert log is not None
        assert log.records_synced == 0
        assert log.status == "success"

    def test_handles_adapter_error(self, session):
        from sportsprediction.data.ingestion.injury_sync import sync_injuries

        adapter = MockInjuryDataAdapter(error=True)
        sync_injuries(adapter, session)
        log = session.query(SyncLog).filter_by(entity_type="injuries").first()
        assert log is not None
        assert log.status == "failed"
