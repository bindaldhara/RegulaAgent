"""Intent classification: LLM (OpenRouter) with mock regex fallback for tests."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

from config import Settings, get_settings
from schemas.enums import Intent
from schemas.intent import ExtractedEntities, IntentClassification
from services.doctor_matching import extract_preferred_hour, resolve_doctor_from_message
from services.intent_llm import INTENT_SYSTEM, classify_intent_openrouter
from services.scheduling_intent import extract_date_phrase, is_slots_request
from services.scheduling_slots import SEED_DOCTORS

_SPECIALTY_MAP = {
    "cardio": "cardiology",
    "cardiologist": "cardiology",
    "cardiology": "cardiology",
    "dentist": "dentistry",
    "dental": "dentistry",
    "dentistry": "dentistry",
    "dermatologist": "dermatology",
    "dermatology": "dermatology",
    "pediatric": "pediatrics",
    "pediatrics": "pediatrics",
}

_EMERGENCY_PATTERNS = (
    "chest pain",
    "can't breathe",
    "cannot breathe",
    "stroke",
    "severe bleeding",
    "unconscious",
    "heart attack",
    "suicidal",
)

_PROTECTED_DATA_PATTERNS = (
    "all patient records",
    "every patient",
    "database",
    "ssn",
    "social security",
    "someone else's",
    "another patient",
)

_APPOINTMENT_REF_RE = re.compile(r"^appt\d+$", re.I)


def use_mock_intent_classifier(settings: Settings | None = None) -> bool:
    cfg = settings or get_settings()
    mode = cfg.agent_provider.lower().strip()
    if mode == "mock":
        return True
    if mode in ("openrouter", "llm"):
        return not bool(cfg.openrouter_api_key)
    # auto
    return not bool(cfg.openrouter_api_key)


def _extract_specialty(text: str) -> str | None:
    lower = text.lower()
    for token, specialty in _SPECIALTY_MAP.items():
        if token in lower:
            return specialty
    return None


def _doctor_name_from_message(text: str) -> str | None:
    ext = resolve_doctor_from_message(text)
    if ext:
        for e, name, _ in SEED_DOCTORS:
            if e == ext:
                return name
    return None


def _extract_appointment_id(text: str) -> str | None:
    match = re.search(r"\b(appt\d+)\b", text, re.I)
    if match:
        return match.group(1).lower()
    match = re.search(r"\bappointment\s+(appt\d+)\b", text, re.I)
    return match.group(1).lower() if match else None


def normalize_appointment_ref(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    ref = value.strip().lower()
    return ref if _APPOINTMENT_REF_RE.match(ref) else None


def _safety_classification(user_message: str) -> IntentClassification | None:
    text = user_message.lower()
    entities = ExtractedEntities(
        specialty=_extract_specialty(user_message),
        doctor_name=_doctor_name_from_message(user_message),
        date=extract_date_phrase(user_message),
        appointment_id=_extract_appointment_id(user_message),
        preferred_hour=extract_preferred_hour(user_message),
    )
    if any(p in text for p in _EMERGENCY_PATTERNS):
        return IntentClassification(
            intent=Intent.UNKNOWN,
            confidence=0.95,
            entities=entities,
            assistant_reply=(
                "This may be a medical emergency. I'm connecting you to a human clinician "
                "and you should call emergency services if you are in immediate danger."
            ),
            is_emergency=True,
        )
    if any(p in text for p in _PROTECTED_DATA_PATTERNS):
        return IntentClassification(
            intent=Intent.UNKNOWN,
            confidence=0.9,
            entities=entities,
            assistant_reply="I can't help with bulk or unauthorized patient record access.",
        )
    return None


def _normalize_llm_entities(
    classification: IntentClassification,
    user_message: str,
    chat_history: list[dict[str, Any]] | None,
) -> IntentClassification:
    blob = user_message
    for turn in (chat_history or [])[-8:]:
        if turn.get("role") in (None, "user"):
            blob += " " + (turn.get("content") or "")

    entities = classification.entities
    doctor = entities.doctor_name or _doctor_name_from_message(user_message) or _doctor_name_from_message(blob)
    if doctor:
        doctor = _doctor_name_from_message(doctor) or _doctor_name_from_message(blob) or doctor

    date = entities.date or extract_date_phrase(user_message) or extract_date_phrase(blob)
    specialty = entities.specialty or _extract_specialty(user_message) or _extract_specialty(blob)
    appt = normalize_appointment_ref(entities.appointment_id) or _extract_appointment_id(user_message)
    hour = extract_preferred_hour(user_message) or extract_preferred_hour(blob)
    if hour is None:
        hour = entities.preferred_hour

    updated = entities.model_copy(
        update={
            "doctor_name": doctor,
            "date": date,
            "specialty": specialty,
            "appointment_id": appt,
            "preferred_hour": hour,
        }
    )
    return classification.model_copy(update={"entities": updated})


def classify_intent_mock(user_message: str) -> IntentClassification:
    text = user_message.lower()
    entities = ExtractedEntities(
        specialty=_extract_specialty(user_message),
        doctor_name=_doctor_name_from_message(user_message),
        date=extract_date_phrase(user_message),
        appointment_id=_extract_appointment_id(user_message),
        preferred_hour=extract_preferred_hour(user_message),
    )

    safety = _safety_classification(user_message)
    if safety:
        return safety

    if any(w in text for w in ("cancel", "cancellation")):
        return IntentClassification(
            intent=Intent.CANCEL_APPOINTMENT,
            confidence=0.88,
            entities=entities,
            assistant_reply="I can help cancel an appointment once we verify your identity.",
        )

    if any(w in text for w in ("my appointment", "upcoming", "when is my", "check appointment")):
        return IntentClassification(
            intent=Intent.CHECK_APPOINTMENT,
            confidence=0.85,
            entities=entities,
            assistant_reply="I'll look up your appointments after we verify your identity.",
        )

    if re.search(r"\b(?:find|list|show|get|check)\b.*\bappointments?\b", text) or "my appointments" in text:
        return IntentClassification(
            intent=Intent.CHECK_APPOINTMENT,
            confidence=0.88,
            entities=entities,
            assistant_reply="I'll look up your appointments after we verify your identity.",
        )

    if is_slots_request(user_message):
        return IntentClassification(
            intent=Intent.LIST_AVAILABLE_SLOTS,
            confidence=0.86,
            entities=entities,
            assistant_reply="I'll check open appointment times for that doctor and date.",
        )

    if (
        re.search(r"\b(?:get|show|list|find|which)\b.*\b(?:dentist|cardiolog|specialists?)\b", text)
        or re.search(r"\b(?:dentist|cardiolog|specialists?)\b.*\bavailable\b", text)
        or re.search(r"\bavailable\b.*\b(?:dentist|cardiolog|specialists?)\b", text)
        or re.search(r"\b(?:drs|doctors)\b.*\bavailable\b", text)
        or re.search(r"\bavailable\b.*\b(?:drs|doctors)\b", text)
    ):
        return IntentClassification(
            intent=Intent.SEARCH_DOCTOR,
            confidence=0.84,
            entities=entities,
            assistant_reply="I'll search for doctors that match what you asked for.",
        )

    if any(w in text for w in ("find", "search", "who is available", "available doctor", "specialist")):
        return IntentClassification(
            intent=Intent.SEARCH_DOCTOR,
            confidence=0.82,
            entities=entities,
            assistant_reply="I'll search for doctors that match what you asked for.",
        )

    if any(w in text for w in ("book", "schedule", "appointment", "see a", "visit")) or re.search(
        r"\b(?:then|instead)\b.*\bbook\b", text
    ):
        specialty = entities.specialty or "provider"
        date_phrase = entities.date or "your preferred date"
        return IntentClassification(
            intent=Intent.BOOK_APPOINTMENT,
            confidence=0.9,
            entities=entities,
            assistant_reply=f"Sure. Let me check available {specialty} appointments for {date_phrase}.",
        )

    return IntentClassification(
        intent=Intent.UNKNOWN,
        confidence=0.4,
        entities=entities,
        assistant_reply="I can help you find a doctor, book, cancel, or check appointments. What would you like to do?",
    )


def classify_intent(
    user_message: str,
    settings: Settings | None = None,
    chat_history: list[dict[str, Any]] | None = None,
) -> IntentClassification:
    cfg = settings or get_settings()
    safety = _safety_classification(user_message)
    if safety:
        return safety

    if use_mock_intent_classifier(cfg):
        return classify_intent_mock(user_message)

    try:
        result = classify_intent_openrouter(
            user_message, chat_history, cfg, system_prompt=INTENT_SYSTEM
        )
        return _normalize_llm_entities(result, user_message, chat_history)
    except Exception:
        logger.exception("LLM intent classification failed; falling back to mock rules")
        return classify_intent_mock(user_message)
