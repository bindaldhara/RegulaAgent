"""Scheduling helpers (timezone, date phrases). Bookings live in Postgres."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

# Clinic schedule: all slots and "today/tomorrow" are interpreted in IST.
TZ = ZoneInfo("Asia/Kolkata")


def resolve_date_phrase(phrase: str | None) -> date:
    if not phrase:
        return (datetime.now(TZ) + timedelta(days=1)).date()
    lower = phrase.lower().strip()
    today = datetime.now(TZ).date()
    if lower == "today":
        return today
    if lower == "tomorrow":
        return today + timedelta(days=1)
    if lower == "next week":
        return today + timedelta(days=7)
    try:
        return date.fromisoformat(lower)
    except ValueError:
        return today + timedelta(days=1)


def local_clinic_hour(starts_at: datetime) -> int:
    """Hour-of-day in clinic TZ (IST) for slot matching and display."""
    if starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=TZ)
    return starts_at.astimezone(TZ).hour


def normalize_specialty(value: str | None) -> str | None:
    if not value:
        return None
    return value.lower().strip()
