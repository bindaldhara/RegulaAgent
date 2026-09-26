"""Match patient text to catalog doctors and time preferences."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from services.scheduling_slots import SEED_DOCTORS

_FIRST_NAME_ALIASES: dict[str, str] = {
    "sophia": "sofia",
    "sofia": "sofia",
}


def _name_tokens(full_name: str) -> tuple[str, str]:
    tokens = [t for t in re.sub(r"[^a-z\s]", " ", full_name.lower()).split() if t and t != "dr"]
    if not tokens:
        return "", ""
    if len(tokens) == 1:
        return tokens[0], tokens[0]
    return tokens[0], tokens[-1]


def _normalize_first(name: str) -> str:
    return _FIRST_NAME_ALIASES.get(name.lower(), name.lower())


def _first_names_equivalent(spoken: str, canonical: str) -> bool:
    spoken_n = _normalize_first(spoken)
    canon_n = _normalize_first(canonical)
    if spoken_n == canon_n:
        return True
    if len(spoken_n) >= 4 and len(canon_n) >= 4:
        return SequenceMatcher(None, spoken_n, canon_n).ratio() >= 0.84
    return False


def _message_words(text: str) -> set[str]:
    return set(re.findall(r"[a-z]+", text.lower()))


def _last_name_unique(last: str) -> bool:
    count = sum(1 for _, full_name, _ in SEED_DOCTORS if _name_tokens(full_name)[1] == last)
    return count == 1


def resolve_doctor_from_message(text: str) -> str | None:
    lower = text.lower()
    words = _message_words(text)

    for external_id, full_name, _ in SEED_DOCTORS:
        if full_name.lower() in lower:
            return external_id

    candidates: list[str] = []
    for external_id, full_name, _ in SEED_DOCTORS:
        first, last = _name_tokens(full_name)
        if not last:
            continue
        if last not in lower and last not in words:
            continue
        first_ok = (
            not first
            or first in lower
            or first in words
            or any(_first_names_equivalent(w, first) for w in words)
        )
        if first_ok or _last_name_unique(last):
            candidates.append(external_id)

    if len(candidates) == 1:
        return candidates[0]
    return None


def resolve_doctor_external_id(doctor_name: str | None) -> str | None:
    if not doctor_name or not doctor_name.strip():
        return None
    resolved = resolve_doctor_from_message(doctor_name)
    if resolved:
        return resolved
    lower = doctor_name.lower()
    for external_id, full_name, _ in SEED_DOCTORS:
        name_lower = full_name.lower()
        if name_lower in lower or lower in name_lower:
            return external_id
        first, last = _name_tokens(full_name)
        if last in lower and (not first or _first_names_equivalent(lower, first) or first in lower):
            if len([1 for _, n, _ in SEED_DOCTORS if _name_tokens(n)[1] == last]) == 1:
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
