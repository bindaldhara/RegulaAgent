"""Run agent workflow and optionally persist to PostgreSQL."""

from __future__ import annotations

import uuid
from typing import Any

from agent.state import AgentState
from agent.workflow import get_agent_workflow
from config import get_settings
from db.persistence import persist_agent_run
from schemas.agent import AgentRunRequest, AgentRunResponse
from schemas.enums import ConsentStatus, HandoffState, IdentityStatus, WorkflowStep


def _initial_state(request: AgentRunRequest, conversation_id: uuid.UUID, run_id: str) -> AgentState:
    identity = IdentityStatus.VERIFIED if request.identity_verified else IdentityStatus.UNVERIFIED
    consent = ConsentStatus.GRANTED if request.consent_granted else ConsentStatus.PENDING
    return AgentState(
        conversation_id=conversation_id,
        run_id=run_id,
        user_message=request.message,
        patient_id=request.patient_id,
        identity_status=identity,
        consent_status=consent,
        identity_verified_input=request.identity_verified,
        consent_granted_input=request.consent_granted,
        chat_history=[{"role": t.role, "content": t.content} for t in request.chat_history],
        voice_mode=request.voice_mode,
        handoff_state=HandoffState.NONE,
        current_step=WorkflowStep.INTENT,
        audit_events=[],
    )


def run_agent(request: AgentRunRequest, persist: bool = True) -> AgentRunResponse:
    conversation_id = request.conversation_id or uuid.uuid4()
    run_id = uuid.uuid4().hex

    graph = get_agent_workflow()
    final_state: dict[str, Any] = graph.invoke(_initial_state(request, conversation_id, run_id))

    if persist and not request.voice_mode and get_settings().postgres_host:
        try:
            persist_agent_run(conversation_id, run_id, request.message, final_state)
        except Exception:
            pass

    intent = final_state.get("intent")
    policy = final_state.get("policy_decision")
    proposed = final_state.get("proposed_action")

    return AgentRunResponse(
        conversation_id=conversation_id,
        run_id=run_id,
        reply=final_state.get("assistant_reply", ""),
        current_step=final_state.get("current_step", WorkflowStep.END),
        intent=intent,
        identity_status=final_state.get("identity_status", IdentityStatus.UNVERIFIED),
        consent_status=final_state.get("consent_status", ConsentStatus.PENDING),
        policy=policy,
        proposed_action=proposed,
        tool_result=final_state.get("tool_result"),
        handoff_state=final_state.get("handoff_state", HandoffState.NONE),
        audit_event_count=len(final_state.get("audit_events") or []),
    )
