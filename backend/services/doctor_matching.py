"""Match patient text to catalog doctors and time preferences."""

from __future__ import annotations

import re

from services.scheduling_slots import SEED_DOCTORS


def resolve_doctor_external_id(doctor_name: str | None) -> str | None:
    if not doctor_name or not doctor_name.strip():
        return None
    lower = doctor_name.lower()
    for external_id, full_name, _ in SEED_DOCTORS:
        name_lower = full_name.lower()
        if name_lower in lower or lower in name_lower:
            return external_id
        tokens = [t for t in re.sub(r"[^a-z\s]", " ", name_lower).split() if t and t != "dr"]
        if tokens and all(t in lower for t in tokens):
            return external_id
        if tokens and tokens[-1] in lower:
            if len(tokens) == 1 or tokens[0] in lower:
                return external_id
    return None


def resolve_doctor_from_message(text: str) -> str | None:
    lower = text.lower()
    for external_id, full_name, _ in SEED_DOCTORS:
        name_lower = full_name.lower()
        if name_lower in lower:
            return external_id
        last = full_name.split()[-1].lower()
        first = full_name.split()[1].lower() if len(full_name.split()) > 2 else ""
        if last in lower and (not first or first in lower):
            return external_id
    return None


def extract_preferred_hour(text: str) -> int | None:
    lower = text.lower()
    match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", lower)
    if match:
        hour = int(match.group(1))
        ampm = match.group(3)
        if ampm == "pm" and hour != 12:
            hour += 12
        if ampm == "am" and hour == 12:
            hour = 0
        return hour
    match = re.search(r"\b(\d{1,2}):(\d{2})\b", lower)
    if match:
        return int(match.group(1))
    return None
