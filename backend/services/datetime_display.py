"""Human-readable appointment times for chat replies (clinic IST)."""

from __future__ import annotations

from datetime import datetime

from services.healthcare_store import TZ


def parse_starts_at(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)


def format_appointment_time(value: datetime | str) -> str:
    """e.g. 2026-09-26 9:00 AM IST"""
    dt = parse_starts_at(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    local = dt.astimezone(TZ)
    abbrev = local.tzname() or "IST"
    hour = local.strftime("%I").lstrip("0") or "12"
    minute = local.strftime("%M")
    ampm = local.strftime("%p")
    date_part = local.strftime("%Y-%m-%d")
    if minute == "00":
        return f"{date_part} {hour} {ampm} {abbrev}"
    return f"{date_part} {hour}:{minute} {ampm} {abbrev}"
