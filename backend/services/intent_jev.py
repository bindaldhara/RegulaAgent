"""Intent classification via TypeSafe JEV (System One Choice + safety Nouls)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from typesafe_sdk import Choice, Noul, TypeSafeClient

from config import Settings, get_settings
from schemas.enums import Intent
from schemas.intent import ExtractedEntities, IntentClassification
from services.intent_llm import _format_history
from services.scheduling_slots import SEED_DOCTORS

_CHOICE_KEY_TO_INTENT: dict[str, Intent] = {
    "search_doctor": Intent.SEARCH_DOCTOR,
    "list_available_slots": Intent.LIST_AVAILABLE_SLOTS,
    "book_appointment": Intent.BOOK_APPOINTMENT,
    "cancel_appointment": Intent.CANCEL_APPOINTMENT,
    "check_appointment": Intent.CHECK_APPOINTMENT,
    "unknown": Intent.UNKNOWN,
}

_EMERGENCY_NOUL_THRESHOLD = 0.85
_UNAUTHORIZED_RECORDS_NOUL_THRESHOLD = 0.85

_OPENROUTER_JEV_BASE_URL = "https://openrouter.ai/api"


@dataclass(frozen=True)
class JevClientConfig:
    api_key: str
    base_url: str
    model: str
    headers: dict[str, str]


def resolve_jev_client_config(settings: Settings | None = None) -> JevClientConfig | None:
    cfg = settings or get_settings()
    if cfg.typesafe_api_key:
        return JevClientConfig(
            api_key=cfg.typesafe_api_key.strip(),
            base_url="https://api.typesafe.ai",
            model=cfg.typesafe_model,
            headers={},
        )
    if cfg.openrouter_api_key:
        return JevClientConfig(
            api_key=cfg.openrouter_api_key.strip(),
            base_url=_OPENROUTER_JEV_BASE_URL,
            model=cfg.openrouter_jev_model.strip() or "~typesafe/jev-latest",
            headers={
                "HTTP-Referer": cfg.openrouter_app_url or "http://localhost:5173",
                "X-Title": "RegulaAgent",
            },
        )
    return None


def jev_available(settings: Settings | None = None) -> bool:
    return resolve_jev_client_config(settings) is not None


def _intent_choice_criteria() -> dict[str, str]:
    return {
        "search_doctor": (
            "Patient wants to find doctors or specialists by specialty; list who is available "
            "(not specific appointment times)."
        ),
        "list_available_slots": (
            "Patient wants open appointment times / slots for a doctor, specialty, or date."
        ),
        "book_appointment": "Patient wants to book, schedule, or reserve a visit.",
        "cancel_appointment": "Patient wants to cancel an existing appointment.",
        "check_appointment": (
            "Patient wants to see their own upcoming or existing appointments."
        ),
        "unknown": (
            "Unclear request, off-topic, unsafe non-scheduling ask, or cannot be routed."
        ),
    }


def _build_state(user_message: str, chat_history: list[dict[str, Any]] | None) -> str:
    payload = {
        "role": "RegulaAgent healthcare scheduling assistant",
        "doctor_catalog": [
            {"name": name, "specialty": specialty} for _, name, specialty in SEED_DOCTORS
        ],
        "conversation": _format_history(chat_history),
        "current_message": user_message,
        "routing_notes": (
            "Use the full conversation when the current message is a short follow-up "
            "(e.g. a date, 'slots available?', or a doctor name). "
            "Distinguish SEARCH_DOCTOR (who is available) from LIST_AVAILABLE_SLOTS "
            "(which times are open). CHECK_APPOINTMENT is only for the signed-in patient's bookings."
        ),
    }
    return json.dumps(payload, ensure_ascii=False)


def _assistant_reply_for(intent: Intent, entities: ExtractedEntities) -> str:
    if intent == Intent.SEARCH_DOCTOR:
        return "I'll search for doctors that match what you asked for."
    if intent == Intent.LIST_AVAILABLE_SLOTS:
        return "I'll check open appointment times for that doctor and date."
    if intent == Intent.BOOK_APPOINTMENT:
        specialty = entities.specialty or "provider"
        date_phrase = entities.date or "your preferred date"
        return f"Sure. Let me check available {specialty} appointments for {date_phrase}."
    if intent == Intent.CANCEL_APPOINTMENT:
        return "I can help cancel an appointment once we verify your identity."
    if intent == Intent.CHECK_APPOINTMENT:
        return "I'll look up your appointments after we verify your identity."
    return (
        "I can help you find a doctor, book, cancel, or check appointments. "
        "What would you like to do?"
    )


def _confidence_from_choice(choice_answer: Any) -> float:
    conf = getattr(choice_answer, "confidence", None)
    if conf is not None:
        return max(0.0, min(1.0, float(conf)))
    probs = getattr(choice_answer, "probabilities", None) or {}
    if probs:
        return max(float(v) for v in probs.values())
    return 0.5


def classify_intent_jev(
    user_message: str,
    chat_history: list[dict[str, Any]] | None,
    settings: Settings | None = None,
) -> IntentClassification:
    client_cfg = resolve_jev_client_config(settings)
    if not client_cfg:
        raise RuntimeError(
            "JEV intent classification requires TYPESAFE_API_KEY or OPENROUTER_API_KEY"
        )

    state = _build_state(user_message, chat_history)
    questions = {
        "intent": Choice(
            instructions=(
                "What is the patient's primary scheduling intent for the **current** message, "
                "using the conversation when needed?"
            ),
            criteria=_intent_choice_criteria(),
        ),
        "medical_emergency": Noul(
            instructions=(
                "The message describes a possible medical emergency such as chest pain, stroke, "
                "cannot breathe, severe bleeding, heart attack, unconsciousness, or suicidal crisis."
            ),
        ),
        "unauthorized_records": Noul(
            instructions=(
                "The user is asking for bulk, database-wide, or another person's protected "
                "patient records (e.g. all patients, SSNs, someone else's chart)."
            ),
        ),
    }

    with TypeSafeClient(
        api_key=client_cfg.api_key,
        base_url=client_cfg.base_url,
        model=client_cfg.model,
        headers=client_cfg.headers or None,
    ) as client:
        response = client.system_one(state, questions)

    emergency_noul = float(response.nouls["medical_emergency"].noul)
    if emergency_noul >= _EMERGENCY_NOUL_THRESHOLD:
        return IntentClassification(
            intent=Intent.UNKNOWN,
            confidence=max(_confidence_from_choice(response.choices["intent"]), 0.9),
            entities=ExtractedEntities(),
            assistant_reply=(
                "This may be a medical emergency. I'm connecting you to a human clinician "
                "and you should call emergency services if you are in immediate danger."
            ),
            is_emergency=True,
        )

    records_noul = float(response.nouls["unauthorized_records"].noul)
    if records_noul >= _UNAUTHORIZED_RECORDS_NOUL_THRESHOLD:
        return IntentClassification(
            intent=Intent.UNKNOWN,
            confidence=0.9,
            entities=ExtractedEntities(),
            assistant_reply="I can't help with bulk or unauthorized patient record access.",
        )

    choice_key = str(response.choices["intent"].choice).strip().lower()
    intent = _CHOICE_KEY_TO_INTENT.get(choice_key, Intent.UNKNOWN)
    confidence = _confidence_from_choice(response.choices["intent"])
    if intent == Intent.UNKNOWN and confidence < 0.5:
        confidence = min(confidence, 0.45)

    entities = ExtractedEntities()
    return IntentClassification(
        intent=intent,
        confidence=confidence,
        entities=entities,
        assistant_reply=_assistant_reply_for(intent, entities),
        is_emergency=False,
    )
