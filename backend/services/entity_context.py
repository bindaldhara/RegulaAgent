"""Fill missing booking entities from recent chat turns."""

from __future__ import annotations

from typing import Any

from agent.intent_classifier import _doctor_name_from_message, _extract_date, _extract_specialty
from schemas.intent import ExtractedEntities
from services.doctor_matching import extract_preferred_hour
from services.scheduling_slots import SEED_DOCTORS


def _user_history_blob(current_message: str, history: list[dict[str, Any]]) -> str:
    parts = [current_message]
    for turn in history[-10:]:
        if turn.get("role") not in (None, "user"):
            continue
        content = turn.get("content") or ""
        if content:
            parts.append(content)
    return " ".join(parts)


def _specialty_for_doctor(doctor_name: str) -> str | None:
    for _, name, spec in SEED_DOCTORS:
        if name == doctor_name:
            return spec
    return None


def _doctor_matches_specialty(doctor_name: str, specialty: str | None) -> bool:
    if not specialty:
        return True
    doc_spec = _specialty_for_doctor(doctor_name)
    return doc_spec is None or doc_spec == specialty


def enrich_booking_entities(
    entities: ExtractedEntities,
    current_message: str,
    history: list[dict[str, Any]] | None,
) -> ExtractedEntities:
    history = history or []
    # Ignore assistant turns so prior slot/doctor replies do not override the new request.
    user_blob = _user_history_blob(current_message, history)
    updates: dict[str, Any] = {}
    target_specialty = entities.specialty or _extract_specialty(current_message)

    if not entities.doctor_name:
        name = _doctor_name_from_message(current_message) or _doctor_name_from_message(user_blob)
        if name and _doctor_matches_specialty(name, target_specialty):
            updates["doctor_name"] = name
    if not entities.specialty:
        specialty = _extract_specialty(current_message) or _extract_specialty(user_blob)
        if specialty:
            updates["specialty"] = specialty
    doctor_name = updates.get("doctor_name") or entities.doctor_name
    resolved_specialty = entities.specialty or updates.get("specialty")
    if not entities.specialty and not updates.get("specialty") and doctor_name:
        for _, name, spec in SEED_DOCTORS:
            if name == doctor_name:
                updates["specialty"] = spec
                break
    if doctor_name and resolved_specialty and not _doctor_matches_specialty(doctor_name, resolved_specialty):
        updates["doctor_name"] = None
    if not entities.date:
        date_phrase = _extract_date(current_message) or _extract_date(user_blob)
        if date_phrase:
            updates["date"] = date_phrase

    hour_now = extract_preferred_hour(current_message)
    if hour_now is not None:
        updates["preferred_hour"] = hour_now
    elif entities.preferred_hour is None:
        hour_blob = extract_preferred_hour(user_blob)
        if hour_blob is not None:
            updates["preferred_hour"] = hour_blob

    if not updates:
        return entities
    return entities.model_copy(update=updates)
