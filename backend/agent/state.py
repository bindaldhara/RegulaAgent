from __future__ import annotations

from typing import Annotated, Any, TypedDict
from uuid import UUID

from langgraph.graph.message import add_messages

from schemas.agent import PolicyDecision, ProposedAction
from schemas.enums import ConsentStatus, HandoffState, IdentityStatus, WorkflowStep
from schemas.intent import IntentClassification


class AgentState(TypedDict, total=False):
    conversation_id: UUID
    run_id: str
    user_message: str

    messages: Annotated[list[Any], add_messages]

    intent: IntentClassification | None
    patient_id: str | None
    identity_status: IdentityStatus
    consent_status: ConsentStatus

    current_step: WorkflowStep
    proposed_action: ProposedAction | None
    policy_decision: PolicyDecision | None
    risk_level: str | None

    tool_result: dict[str, Any] | None
    tool_error: str | None

    handoff_state: HandoffState
    handoff_reason: str | None

    assistant_reply: str
    final_outcome: str

    audit_events: list[dict[str, Any]]

    identity_verified_input: bool
    consent_granted_input: bool
    chat_history: list[dict[str, str]]
    voice_mode: bool
