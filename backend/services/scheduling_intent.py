"""Slot vs doctor-search intent and follow-up turns from chat history."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from schemas.enums import Intent
from schemas.intent import IntentClassification
from services.doctor_matching import resolve_doctor_from_message
from services.healthcare_store import TZ
from services.scheduling_slots import SEED_DOCTORS

_MONTHS: dict[str, int] = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


def _relative_date_phrase(text: str) -> str | None:
    lower = text.lower()
    for phrase in (
        "tomorrow",
        "today",
        "next week",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
    ):
        if phrase in lower:
            return phrase
    match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    return match.group(1) if match else None


def _doctor_name_from_message(text: str) -> str | None:
    ext = resolve_doctor_from_message(text)
    if not ext:
        return None
    for external_id, name, _ in SEED_DOCTORS:
        if external_id == ext:
            return name
    return None


def parse_calendar_date(text: str) -> str | None:
    """Return ISO date string when the message contains a calendar day."""
    lower = text.lower()
    match = re.search(
        r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?([a-z]+)(?:\s+(\d{4}))?\b",
        lower,
    )
    if match:
        day = int(match.group(1))
        month_key = match.group(2)
        year = int(match.group(3)) if match.group(3) else datetime.now(TZ).year
        month = _MONTHS.get(month_key)
        if month:
            return date(year, month, day).isoformat()

    match = re.search(
        r"\b([a-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s+(\d{4}))?\b",
        lower,
    )
    if match:
        month = _MONTHS.get(match.group(1))
        if month:
            day = int(match.group(2))
            year = int(match.group(3)) if match.group(3) else datetime.now(TZ).year
            return date(year, month, day).isoformat()
    return None


def extract_date_phrase(text: str) -> str | None:
    return parse_calendar_date(text) or _relative_date_phrase(text)


def is_slots_request(text: str) -> bool:
    lower = text.lower().strip()
    if re.fullmatch(r"slots?\s*(available)?\s*\??", lower):
        return True
    if not re.search(r"\bslots?\b", lower):
        if re.search(r"\b(?:available|open)\s+times?\b", lower):
            return True
        return False
    if re.search(r"\b(?:available|open|what|which|show|get|list|other)\b", lower):
        return True
    if _doctor_name_from_message(text):
        return True
    if re.search(r"\b(?:available|open)\s+slots?\b", lower):
        return True
    if re.search(r"\bslots?\s+available\b", lower):
        return True
    return False


def _user_history_blob(current_message: str, history: list[dict[str, Any]] | None) -> str:
    parts = [current_message]
    for turn in (history or [])[-12:]:
        if turn.get("role") not in (None, "user"):
            continue
        content = (turn.get("content") or "").strip()
        if content:
            parts.append(content)
    return " ".join(parts)


def _history_mentions_slots(blob: str) -> bool:
    lower = blob.lower()
    return "slot" in lower or "available times" in lower or "open times" in lower


def refine_intent_from_history(
    classification: IntentClassification,
    message: str,
    history: list[dict[str, Any]] | None,
) -> IntentClassification:
    blob = _user_history_blob(message, history)
    date_phrase = extract_date_phrase(message)
    entities = classification.entities

    if is_slots_request(message):
        updates: dict[str, Any] = {
            "intent": Intent.LIST_AVAILABLE_SLOTS,
            "confidence": max(classification.confidence, 0.86),
            "assistant_reply": "I'll check open appointment times for that doctor and date.",
        }
        if date_phrase:
            updates["entities"] = entities.model_copy(update={"date": date_phrase})
        return classification.model_copy(update=updates)

    if classification.intent == Intent.SEARCH_DOCTOR and is_slots_request(blob):
        return classification.model_copy(
            update={
                "intent": Intent.LIST_AVAILABLE_SLOTS,
                "assistant_reply": "I'll check open appointment times for that doctor and date.",
            }
        )

    if classification.intent == Intent.UNKNOWN:
        if date_phrase and (_history_mentions_slots(blob) or _doctor_name_from_message(blob)):
            return classification.model_copy(
                update={
                    "intent": Intent.LIST_AVAILABLE_SLOTS,
                    "confidence": 0.84,
                    "entities": entities.model_copy(update={"date": date_phrase}),
                    "assistant_reply": "I'll check open appointment times for that date.",
                }
            )
        if re.fullmatch(r"slots?\s*(available)?\s*\??", message.lower().strip()) and _history_mentions_slots(
            blob
        ):
            return classification.model_copy(
                update={
                    "intent": Intent.LIST_AVAILABLE_SLOTS,
                    "confidence": 0.82,
                    "assistant_reply": "I'll check open appointment times.",
                }
            )

    return classification
