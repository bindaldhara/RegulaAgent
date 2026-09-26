from datetime import datetime
from zoneinfo import ZoneInfo

from services.healthcare_store import TZ, local_clinic_hour


def test_local_clinic_hour_matches_ist_display() -> None:
    ist_2pm = datetime(2026, 9, 27, 14, 0, tzinfo=TZ)
    assert local_clinic_hour(ist_2pm) == 14

    utc_same_instant = ist_2pm.astimezone(ZoneInfo("UTC"))
    assert utc_same_instant.hour == 8
    assert local_clinic_hour(utc_same_instant) == 14
