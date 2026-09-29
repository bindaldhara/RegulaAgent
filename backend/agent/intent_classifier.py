"""Intent classification: JEV (TypeSafe), OpenRouter LLM, or mock regex fallback."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

from config import Settings, get_settings
from schemas.enums import Intent
from schemas.intent import ExtractedEntities, IntentClassification
from services.doctor_matching import extract_preferred_hour, resolve_doctor_from_message
from services.intent_jev import classify_intent_jev, jev_available, resolve_jev_client_config
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


def _openrouter_llm_available(cfg: Settings) -> bool:
    return bool(cfg.openrouter_api_key)


def _intent_backend_chain(cfg: Settings) -> str:
    """Preference order: JEV → OpenRouter chat LLM → mock regex."""
    if jev_available(cfg):
        return "jev"
    if _openrouter_llm_available(cfg):
        return "openrouter"
    return "mock"


def intent_classifier_backend(settings: Settings | None = None) -> str:
    """Returns mock, jev, or openrouter."""
    cfg = settings or get_settings()
    mode = cfg.agent_provider.lower().strip()
    if mode == "mock":
        return "mock"
    if mode in ("jev", "typesafe"):
        return _intent_backend_chain(cfg)
    if mode in ("openrouter", "llm"):
        return "openrouter" if _openrouter_llm_available(cfg) else "mock"
    return _intent_backend_chain(cfg)


def use_mock_intent_classifier(settings: Settings | None = None) -> bool:
    return intent_classifier_backend(settings) == "mock"


def _intent_classifier_label(cfg: Settings, backend: str) -> str:
    if backend == "mock":
        return "mock (regex)"
    if backend == "openrouter":
        return f"openrouter LLM ({cfg.openrouter_model})"
    if backend == "jev":
        jev_cfg = resolve_jev_client_config(cfg)
        if jev_cfg and "openrouter.ai" in jev_cfg.base_url:
            return f"jev / OpenRouter ({jev_cfg.model})"
        if jev_cfg:
            return f"jev / TypeSafe ({jev_cfg.model})"
        return "jev"
    return backend


def _log_intent_classifier(label: str, result: IntentClassification | None = None) -> None:
    if result is None:
        line = f"[intent] classifier={label}"
    else:
        line = (
            f"[intent] classifier={label} -> {result.intent.value} "
            f"confidence={result.confidence:.2f}"
        )
    print(line, flush=True)
    logger.info("%s", line)


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
        label = _intent_classifier_label(cfg, "mock")
        result = classify_intent_mock(user_message)
        _log_intent_classifier(label, result)
        return result

    backend = intent_classifier_backend(cfg)
    label = _intent_classifier_label(cfg, backend)

    def _run(backend_name: str) -> IntentClassification:
        if backend_name == "jev":
            raw = classify_intent_jev(user_message, chat_history, cfg)
        else:
            raw = classify_intent_openrouter(
                user_message, chat_history, cfg, system_prompt=INTENT_SYSTEM
            )
        return _normalize_llm_entities(raw, user_message, chat_history)

    try:
        result = _run(backend)
        _log_intent_classifier(label, result)
        return result
    except Exception:
        logger.exception("%s intent classification failed", backend)
        if backend == "jev" and _openrouter_llm_available(cfg):
            or_label = _intent_classifier_label(cfg, "openrouter")
            try:
                result = _run("openrouter")
                _log_intent_classifier(f"{or_label} (jev failed → openrouter)", result)
                return result
            except Exception:
                logger.exception("openrouter intent classification failed after jev")
        result = classify_intent_mock(user_message)
        _log_intent_classifier(f"{label} (failed → mock)", result)
        return result
