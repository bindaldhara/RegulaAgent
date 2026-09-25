"""LangGraph node implementations for the RegulaAgent workflow."""

from __future__ import annotations

from typing import Any

from agent.intent_classifier import classify_intent
from config import get_settings
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

_PROTECTED_INTENTS = {Intent.BOOK_APPOINTMENT, Intent.CANCEL_APPOINTMENT, Intent.CHECK_APPOINTMENT}
_HIGH_RISK_TOOLS = {"get_patient_records", "list_all_patients"}


def _append_audit(state: dict[str, Any], event_type: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    events = list(state.get("audit_events") or [])
    events.append({"event_type": event_type, "payload": payload})
    return events


def intent_node(state: dict[str, Any]) -> dict[str, Any]:
    message = state["user_message"]
    classification = classify_intent(message, get_settings())
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
        "assistant_reply": "Before I continue, please confirm your patient ID and date of birth.",
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
        return {
            "consent_status": ConsentStatus.PENDING,
            "current_step": WorkflowStep.CONSENT,
        }

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
            "I need your consent to access scheduling actions on your behalf. "
            "Reply yes to continue."
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
    if intent.intent == Intent.BOOK_APPOINTMENT:
        return ProposedAction(
            tool_name="book_appointment",
            arguments={
                "specialty": entities.specialty,
                "date": entities.date,
                "slot": entities.slot,
                "doctor_name": entities.doctor_name,
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
            arguments={"patient_id": None},
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

    if intent and intent.is_emergency:
        decision = PolicyDecision(
            outcome=PolicyOutcome.ESCALATE,
            risk_level=RiskLevel.CRITICAL,
            reason="Emergency symptoms reported; human handoff required.",
        )
        return {
            "policy_decision": decision,
            "risk_level": decision.risk_level,
            "current_step": WorkflowStep.POLICY,
            "handoff_state": HandoffState.QUEUED,
            "audit_events": _append_audit(state, "policy_escalate", {"reason": decision.reason}),
        }

    if proposed and proposed.tool_name in _HIGH_RISK_TOOLS:
        decision = PolicyDecision(
            outcome=PolicyOutcome.DENY,
            risk_level=RiskLevel.HIGH,
            reason="Protected patient data access is not allowed.",
        )
        return {
            "policy_decision": decision,
            "risk_level": decision.risk_level,
            "current_step": WorkflowStep.POLICY,
            "audit_events": _append_audit(state, "policy_deny", {"reason": decision.reason}),
        }

    if proposed and proposed.risk_level == RiskLevel.MEDIUM:
        if state.get("identity_status") != IdentityStatus.VERIFIED:
            decision = PolicyDecision(
                outcome=PolicyOutcome.DENY,
                risk_level=RiskLevel.MEDIUM,
                reason="Identity verification required before booking or cancellation.",
            )
            return {
                "policy_decision": decision,
                "risk_level": decision.risk_level,
                "current_step": WorkflowStep.POLICY,
                "audit_events": _append_audit(state, "policy_deny", {"reason": decision.reason}),
            }
        if state.get("consent_status") != ConsentStatus.GRANTED:
            decision = PolicyDecision(
                outcome=PolicyOutcome.DENY,
                risk_level=RiskLevel.MEDIUM,
                reason="Explicit consent required before protected scheduling actions.",
            )
            return {
                "policy_decision": decision,
                "risk_level": decision.risk_level,
                "current_step": WorkflowStep.POLICY,
                "audit_events": _append_audit(state, "policy_deny", {"reason": decision.reason}),
            }

    if proposed and proposed.risk_level == RiskLevel.HIGH:
        if state.get("identity_status") != IdentityStatus.VERIFIED:
            decision = PolicyDecision(
                outcome=PolicyOutcome.DENY,
                risk_level=RiskLevel.HIGH,
                reason="Authorization required for protected patient data.",
            )
            return {
                "policy_decision": decision,
                "risk_level": decision.risk_level,
                "current_step": WorkflowStep.POLICY,
                "audit_events": _append_audit(state, "policy_deny", {"reason": decision.reason}),
            }

    if intent and intent.intent == Intent.UNKNOWN and proposed is None:
        decision = PolicyDecision(
            outcome=PolicyOutcome.DENY,
            risk_level=RiskLevel.LOW,
            reason="No actionable intent; cannot invoke tools.",
        )
        return {
            "policy_decision": decision,
            "risk_level": decision.risk_level,
            "current_step": WorkflowStep.POLICY,
            "audit_events": _append_audit(state, "policy_deny", {"reason": decision.reason}),
        }

    decision = PolicyDecision(
        outcome=PolicyOutcome.ALLOW,
        risk_level=proposed.risk_level if proposed else RiskLevel.LOW,
        reason="Action permitted by policy.",
    )
    return {
        "policy_decision": decision,
        "risk_level": decision.risk_level,
        "current_step": WorkflowStep.POLICY,
        "audit_events": _append_audit(state, "policy_allow", {"tool": proposed.tool_name if proposed else None}),
    }


def tool_node(state: dict[str, Any]) -> dict[str, Any]:
    """Placeholder until Day 1 afternoon mock healthcare tools are implemented."""
    proposed = state.get("proposed_action")
    if not proposed:
        return {"current_step": WorkflowStep.TOOL, "tool_result": None}

    result = {
        "status": "deferred",
        "message": f"Tool `{proposed.tool_name}` will execute after mock APIs are wired (Day 1 PM).",
        "arguments": proposed.arguments,
    }
    return {
        "tool_result": result,
        "current_step": WorkflowStep.TOOL,
        "audit_events": _append_audit(state, "tool_deferred", {"tool": proposed.tool_name}),
    }


def result_validation_node(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "current_step": WorkflowStep.RESULT_VALIDATION,
        "audit_events": _append_audit(state, "result_validated", {"ok": True}),
    }


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

    if state.get("assistant_reply"):
        reply = state["assistant_reply"]
    elif intent:
        reply = intent.assistant_reply
    else:
        reply = "How can I help with your healthcare scheduling today?"

    tool_result = state.get("tool_result")
    if tool_result and tool_result.get("status") == "deferred":
        reply = f"{reply}\n\n({tool_result['message']})"

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
