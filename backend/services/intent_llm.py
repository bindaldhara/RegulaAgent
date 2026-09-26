"""LLM intent classification via OpenRouter (structured output)."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from config import Settings, get_settings
from schemas.intent import IntentClassification
from services.scheduling_slots import SEED_DOCTORS


def _catalog_block() -> str:
    lines = [f"- {name} ({specialty})" for _, name, specialty in SEED_DOCTORS]
    return "\n".join(lines)


def _format_history(history: list[dict[str, Any]] | None) -> str:
    if not history:
        return "(no prior messages)"
    lines: list[str] = []
    for turn in history[-10:]:
        role = str(turn.get("role") or "user")
        content = (turn.get("content") or "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines) if lines else "(no prior messages)"


def classify_intent_openrouter(
    user_message: str,
    chat_history: list[dict[str, Any]] | None,
    settings: Settings | None = None,
    *,
    system_prompt: str,
) -> IntentClassification:
    cfg = settings or get_settings()
    if not cfg.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY required for LLM intent classification")

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
    payload = {
        "conversation": _format_history(chat_history),
        "current_message": user_message,
    }
    return structured.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
        ]
    )


def build_intent_system_prompt() -> str:
    return f"""You are the intent router for RegulaAgent, a healthcare scheduling assistant.

Classify the patient's **current** message using the conversation when needed (follow-ups like "28th September" or "slots available?" inherit doctor/specialty/date from earlier turns).

## Intents (pick exactly one)
- SEARCH_DOCTOR — who is available for a specialty; list doctors (not time slots).
- LIST_AVAILABLE_SLOTS — open appointment times for a doctor/specialty/date.
- BOOK_APPOINTMENT — book/schedule/reserve a visit.
- CANCEL_APPOINTMENT — cancel a booking (use appointment_id when given, else doctor + date).
- CHECK_APPOINTMENT — list the signed-in patient's existing appointments.
- UNKNOWN — unclear, off-topic, or unsafe non-scheduling requests.

## Tool mapping (for your reasoning; the backend calls tools from intent)
- SEARCH_DOCTOR → search_doctors
- LIST_AVAILABLE_SLOTS → get_available_slots
- BOOK_APPOINTMENT → book_appointment
- CANCEL_APPOINTMENT → cancel_appointment
- CHECK_APPOINTMENT → get_patient_appointments

## Doctors in catalog (use exact full names in doctor_name when possible)
{_catalog_block()}

## Entity extraction
- specialty: dentistry, cardiology, dermatology, pediatrics, etc.
- doctor_name: exact catalog name when identifiable (tolerate STT typos like Sophia → Dr. Sofia Mehta).
- date: natural phrases (tomorrow, next week) or ISO YYYY-MM-DD.
- appointment_id: appt1, appt2, … only when explicitly mentioned.
- slot / preferred_hour: when the patient names a time.

## Safety
- is_emergency=true for chest pain, stroke, can't breathe, severe bleeding, suicide, etc. Use intent UNKNOWN with a calm escalation reply.
- Deny bulk/unauthorized patient record access (intent UNKNOWN).

## Output
Return structured fields only. confidence 0–1. assistant_reply: one short sentence."""


INTENT_SYSTEM = build_intent_system_prompt()
