"""LangGraph node implementations for the RegulaAgent workflow."""

from __future__ import annotations

from typing import Any

from agent.intent_classifier import classify_intent
from config import get_settings
from policy.engine import PolicyEngine
from schemas.agent import PolicyDecision, ProposedAction
from schemas.enums import (
    ConsentStatus,
    HandoffState,
    IdentityStatus,
    Intent,
    PolicyOutcome,
    RiskLevel,
    WorkflowStep,
)
from schemas.intent import IntentClassification
from services.datetime_display import format_appointment_time
from services.doctor_matching import resolve_doctor_external_id
from services.entity_context import enrich_booking_entities
from tools.router import ToolExecutionError, execute_tool

_POLICY = PolicyEngine()
_PROTECTED_INTENTS = {Intent.BOOK_APPOINTMENT, Intent.CANCEL_APPOINTMENT, Intent.CHECK_APPOINTMENT}


def _append_audit(state: dict[str, Any], event_type: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    events = list(state.get("audit_events") or [])
    events.append({"event_type": event_type, "payload": payload})
    return events


def intent_node(state: dict[str, Any]) -> dict[str, Any]:
    message = state["user_message"]
    classification = classify_intent(message, get_settings())
    if classification.intent in (Intent.BOOK_APPOINTMENT, Intent.LIST_AVAILABLE_SLOTS):
        entities = enrich_booking_entities(
            classification.entities,
            message,
            state.get("chat_history"),
        )
        classification = classification.model_copy(update={"entities": entities})
    return {
        "intent": classification,
        "current_step": WorkflowStep.INTENT,
        "handoff_state": HandoffState.QUEUED if classification.is_emergency else HandoffState.NONE,
        "handoff_reason": "emergency_symptoms" if classification.is_emergency else None,
        "audit_events": _append_audit(
            state,
            "intent_classified",
            {"intent": classification.intent, "confidence": classification.confidence},
        ),
    }


def identity_node(state: dict[str, Any]) -> dict[str, Any]:
    intent = state.get("intent")
    if not intent:
        return {"current_step": WorkflowStep.IDENTITY}

    if intent.intent not in _PROTECTED_INTENTS:
        return {
            "identity_status": IdentityStatus.UNVERIFIED,
            "current_step": WorkflowStep.IDENTITY,
            "audit_events": _append_audit(state, "identity_skipped", {"reason": "public_intent"}),
        }

    if state.get("identity_verified_input") or state.get("identity_status") == IdentityStatus.VERIFIED:
        return {
            "identity_status": IdentityStatus.VERIFIED,
            "current_step": WorkflowStep.IDENTITY,
            "audit_events": _append_audit(state, "identity_verified", {}),
        }

    return {
        "identity_status": IdentityStatus.PENDING,
        "current_step": WorkflowStep.IDENTITY,
        "assistant_reply": "Please sign in to continue with booking or viewing your appointments.",
        "audit_events": _append_audit(state, "identity_required", {"intent": intent.intent}),
    }


def consent_node(state: dict[str, Any]) -> dict[str, Any]:
    intent: IntentClassification | None = state.get("intent")
    if not intent or intent.intent not in _PROTECTED_INTENTS:
        return {
            "consent_status": ConsentStatus.NOT_REQUIRED,
            "current_step": WorkflowStep.CONSENT,
            "audit_events": _append_audit(state, "consent_not_required", {}),
        }

    if state.get("identity_status") != IdentityStatus.VERIFIED:
        return {"consent_status": ConsentStatus.PENDING, "current_step": WorkflowStep.CONSENT}

    if state.get("consent_granted_input"):
        return {
            "consent_status": ConsentStatus.GRANTED,
            "current_step": WorkflowStep.CONSENT,
            "audit_events": _append_audit(state, "consent_granted", {}),
        }

    return {
        "consent_status": ConsentStatus.PENDING,
        "current_step": WorkflowStep.CONSENT,
        "assistant_reply": (
            "Please confirm scheduling consent in the sign-in panel (checkbox) to book or cancel."
        ),
        "audit_events": _append_audit(state, "consent_required", {}),
    }


def _intent_to_action(intent: IntentClassification) -> ProposedAction | None:
    entities = intent.entities
    if intent.intent == Intent.SEARCH_DOCTOR:
        return ProposedAction(
            tool_name="search_doctors",
            arguments={"specialty": entities.specialty},
            risk_level=RiskLevel.LOW,
        )
    if intent.intent == Intent.LIST_AVAILABLE_SLOTS:
        return ProposedAction(
            tool_name="get_available_slots",
            arguments={
                "specialty": entities.specialty,
                "doctor_id": resolve_doctor_external_id(entities.doctor_name),
                "date": entities.date,
            },
            risk_level=RiskLevel.LOW,
        )
    if intent.intent == Intent.BOOK_APPOINTMENT:
        doctor_id = resolve_doctor_external_id(entities.doctor_name)
        return ProposedAction(
            tool_name="book_appointment",
            arguments={
                "specialty": entities.specialty,
                "date": entities.date,
                "slot_id": entities.slot,
                "doctor_id": doctor_id,
                "preferred_hour": entities.preferred_hour,
            },
            risk_level=RiskLevel.MEDIUM,
        )
    if intent.intent == Intent.CANCEL_APPOINTMENT:
        return ProposedAction(
            tool_name="cancel_appointment",
            arguments={"appointment_id": entities.appointment_id},
            risk_level=RiskLevel.MEDIUM,
        )
    if intent.intent == Intent.CHECK_APPOINTMENT:
        return ProposedAction(
            tool_name="get_patient_appointments",
            arguments={},
            risk_level=RiskLevel.HIGH,
        )
    return None


def action_node(state: dict[str, Any]) -> dict[str, Any]:
    intent = state.get("intent")
    if not intent:
        return {"current_step": WorkflowStep.ACTION, "proposed_action": None}

    proposed = _intent_to_action(intent)
    return {
        "proposed_action": proposed,
        "current_step": WorkflowStep.ACTION,
        "audit_events": _append_audit(
            state,
            "action_proposed",
            {"tool": proposed.tool_name if proposed else None},
        ),
    }


def policy_node(state: dict[str, Any]) -> dict[str, Any]:
    intent = state.get("intent")
    proposed = state.get("proposed_action")
    decision = _POLICY.evaluate(
        intent=intent,
        proposed=proposed,
        identity_status=state.get("identity_status", IdentityStatus.UNVERIFIED),
        consent_status=state.get("consent_status", ConsentStatus.PENDING),
        patient_id=state.get("patient_id"),
        tool_args=proposed.arguments if proposed else None,
    )
    updates: dict[str, Any] = {
        "policy_decision": decision,
        "risk_level": decision.risk_level,
        "current_step": WorkflowStep.POLICY,
    }
    if decision.outcome == PolicyOutcome.ESCALATE:
        updates["handoff_state"] = HandoffState.QUEUED
        updates["audit_events"] = _append_audit(state, "policy_escalate", {"reason": decision.reason})
    elif decision.outcome == PolicyOutcome.DENY:
        updates["audit_events"] = _append_audit(state, "policy_deny", {"reason": decision.reason})
    else:
        updates["audit_events"] = _append_audit(
            state,
            "policy_allow",
            {"tool": proposed.tool_name if proposed else None},
        )
    return updates


def tool_node(state: dict[str, Any]) -> dict[str, Any]:
    proposed = state.get("proposed_action")
    if not proposed:
        return {"current_step": WorkflowStep.TOOL, "tool_result": None}

    try:
        result = execute_tool(
            proposed.tool_name,
            proposed.arguments,
            patient_id=state.get("patient_id"),
            idempotency_key=state.get("run_id"),
        )
        return {
            "tool_result": result,
            "tool_error": None,
            "current_step": WorkflowStep.TOOL,
            "audit_events": _append_audit(
                state,
                "tool_executed",
                {"tool": proposed.tool_name, "status": result.get("status")},
            ),
        }
    except ToolExecutionError as exc:
        return {
            "tool_result": None,
            "tool_error": str(exc),
            "current_step": WorkflowStep.TOOL,
            "audit_events": _append_audit(
                state,
                "tool_failed",
                {"tool": proposed.tool_name, "error": str(exc)},
            ),
        }


def result_validation_node(state: dict[str, Any]) -> dict[str, Any]:
    ok = state.get("tool_error") is None and (
        state.get("tool_result") is None or state.get("tool_result", {}).get("status") == "success"
    )
    return {
        "current_step": WorkflowStep.RESULT_VALIDATION,
        "audit_events": _append_audit(state, "result_validated", {"ok": ok}),
    }


def _format_tool_reply(tool_name: str, data: dict[str, Any]) -> str:
    if tool_name == "search_doctors":
        doctors = data.get("doctors") or []
        if not doctors:
            return "I couldn't find doctors for that specialty."
        lines = [f"• {d['full_name']} ({d['specialty']})" for d in doctors]
        return "Here are available doctors:\n" + "\n".join(lines)
    if tool_name == "get_available_slots":
        slots = data.get("slots") or []
        if not slots:
            return "No open slots for that date."
        lines = [
            f"{i}. {s['doctor_name']} — {format_appointment_time(s['starts_at'])}"
            for i, s in enumerate(slots[:5], 1)
        ]
        return "Available slots:\n\n" + "\n".join(lines)
    if tool_name == "book_appointment":
        replay = data.get("idempotent_replay")
        prefix = "Confirmed (existing booking): " if replay else "Booked: "
        when = format_appointment_time(data["starts_at"])
        return f"{prefix}{data['doctor_name']} on {when} (ref {data['appointment_id']})."
    if tool_name == "cancel_appointment":
        return f"Cancelled appointment {data['appointment_id']}."
    if tool_name == "get_patient_appointments":
        appts = data.get("appointments") or []
        if not appts:
            return "You have no appointments on file."
        blocks: list[str] = []
        for i, a in enumerate(appts, 1):
            when = format_appointment_time(a["starts_at"])
            status = str(a.get("status", "booked"))
            ref = a.get("appointment_id", "")
            blocks.append(f"{i}. {a['doctor_name']}\n   {when} · {status} · {ref}")
        return "Your appointments:\n\n" + "\n\n".join(blocks)
    return "Done."


def response_node(state: dict[str, Any]) -> dict[str, Any]:
    intent = state.get("intent")
    policy = state.get("policy_decision")

    if policy and policy.outcome == PolicyOutcome.ESCALATE:
        reply = intent.assistant_reply if intent else "Connecting you to a human agent."
        return {
            "assistant_reply": reply,
            "current_step": WorkflowStep.HANDOFF,
            "final_outcome": "escalated",
        }

    if policy and policy.outcome == PolicyOutcome.DENY:
        reply = state.get("assistant_reply") or policy.reason
        return {
            "assistant_reply": reply,
            "current_step": WorkflowStep.RESPONSE,
            "final_outcome": "denied",
        }

    if state.get("tool_error"):
        err = state["tool_error"]
        if "already booked" in err.lower() or err.startswith("The "):
            reply = err
        else:
            reply = f"I couldn't complete that action: {err}"
        return {
            "assistant_reply": reply,
            "current_step": WorkflowStep.RESPONSE,
            "final_outcome": "tool_failed",
        }

    tool_result = state.get("tool_result")
    proposed = state.get("proposed_action")
    if tool_result and tool_result.get("status") == "success" and proposed:
        reply = _format_tool_reply(proposed.tool_name, tool_result.get("data", {}))
        return {
            "assistant_reply": reply,
            "current_step": WorkflowStep.RESPONSE,
            "final_outcome": "completed",
        }

    if state.get("assistant_reply"):
        reply = state["assistant_reply"]
    elif intent:
        reply = intent.assistant_reply
    else:
        reply = "How can I help with your healthcare scheduling today?"

    return {
        "assistant_reply": reply,
        "current_step": WorkflowStep.RESPONSE,
        "final_outcome": "completed",
    }


def audit_node(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "current_step": WorkflowStep.AUDIT,
        "audit_events": _append_audit(
            state,
            "run_completed",
            {"outcome": state.get("final_outcome"), "step": WorkflowStep.END},
        ),
    }
