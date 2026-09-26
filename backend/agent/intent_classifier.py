"""Structured intent classification (mock + OpenRouter LLM)."""

from __future__ import annotations

import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from config import Settings, get_settings
from schemas.enums import Intent
from schemas.intent import ExtractedEntities, IntentClassification
from services.doctor_matching import extract_preferred_hour, resolve_doctor_from_message
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


def _extract_specialty(text: str) -> str | None:
    lower = text.lower()
    for token, specialty in _SPECIALTY_MAP.items():
        if token in lower:
            return specialty
    return None


def _extract_date(text: str) -> str | None:
    lower = text.lower()
    for phrase in ("tomorrow", "today", "next week", "monday", "tuesday", "wednesday", "thursday", "friday"):
        if phrase in lower:
            return phrase
    match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    if match:
        return match.group(1)
    return None


def _doctor_name_from_message(text: str) -> str | None:
    lower = text.lower()
    for _, full_name, _ in SEED_DOCTORS:
        if full_name.lower() in lower:
            return full_name
        last = full_name.split()[-1]
        first = full_name.split()[1] if full_name.startswith("Dr.") else ""
        if last.lower() in lower and (not first or first.lower() in lower):
            return full_name
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
    match = re.search(r"\b(?:appt|appointment)[\s#-]*([a-z0-9-]+)\b", text, re.I)
    return match.group(1).lower() if match else None


def classify_intent_mock(user_message: str) -> IntentClassification:
    text = user_message.lower()
    entities = ExtractedEntities(
        specialty=_extract_specialty(user_message),
        doctor_name=_doctor_name_from_message(user_message),
        date=_extract_date(user_message),
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

    if re.search(r"\b(?:available|open)\s+slots?\b", text) or re.search(
        r"\b(?:get|show|list|what are)\b.*\bslots?\b", text
    ):
        return IntentClassification(
            intent=Intent.LIST_AVAILABLE_SLOTS,
            confidence=0.86,
            entities=entities,
            assistant_reply="I'll check open appointment times for that doctor and date.",
        )

    if (
        re.search(r"\b(?:drs?|doctors?)\b.*\bavailable\b", text)
        or re.search(r"\bavailable\b.*\b(?:drs?|doctors?)\b", text)
        or re.search(
            r"\b(?:get|show|list|find|which)\b.*\b(?:drs?|doctors?)\b", text
        )
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


_INTENT_SYSTEM = """You classify patient messages for a healthcare scheduling assistant.
Return structured JSON only via the schema.

Intents:
- BOOK_APPOINTMENT
- CANCEL_APPOINTMENT
- SEARCH_DOCTOR
- LIST_AVAILABLE_SLOTS
- CHECK_APPOINTMENT
- UNKNOWN

Extract entities when present: specialty, doctor_name, date, slot, appointment_id.
Set is_emergency true for chest pain, stroke, can't breathe, severe bleeding, etc.
Keep assistant_reply to one short helpful sentence."""


def classify_intent_llm(user_message: str, settings: Settings | None = None) -> IntentClassification:
    cfg = settings or get_settings()
    if not cfg.openrouter_api_key:
        return classify_intent_mock(user_message)

    model = ChatOpenAI(
        model=cfg.openrouter_model,
        api_key=cfg.openrouter_api_key,
        base_url=cfg.openrouter_base_url,
        default_headers={
            "HTTP-Referer": cfg.openrouter_app_url,
            "X-Title": "RegulaAgent",
        },
        temperature=0,
    )
    structured = model.with_structured_output(IntentClassification)
    return structured.invoke(
        [
            SystemMessage(content=_INTENT_SYSTEM),
            HumanMessage(content=user_message),
        ]
    )


def classify_intent(user_message: str, settings: Settings | None = None) -> IntentClassification:
    cfg = settings or get_settings()
    if cfg.agent_provider == "mock":
        return classify_intent_mock(user_message)
    return classify_intent_llm(user_message, cfg)
