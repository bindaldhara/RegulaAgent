from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from schemas.enums import (
    ConsentStatus,
    HandoffState,
    IdentityStatus,
    PolicyOutcome,
    RiskLevel,
    WorkflowStep,
)
from schemas.intent import ExtractedEntities, IntentClassification


class ProposedAction(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.LOW


class PolicyDecision(BaseModel):
    outcome: PolicyOutcome
    risk_level: RiskLevel
    reason: str


class ChatHistoryTurn(BaseModel):
    role: str
    content: str


class AgentRunRequest(BaseModel):
    message: str
    conversation_id: UUID | None = None
    patient_id: str | None = None
    identity_verified: bool = False
    consent_granted: bool = False
    chat_history: list[ChatHistoryTurn] = Field(default_factory=list)


class AgentRunResponse(BaseModel):
    conversation_id: UUID
    run_id: str
    reply: str
    current_step: WorkflowStep
    intent: IntentClassification | None = None
    identity_status: IdentityStatus
    consent_status: ConsentStatus
    policy: PolicyDecision | None = None
    proposed_action: ProposedAction | None = None
    tool_result: dict[str, Any] | None = None
    handoff_state: HandoffState
    audit_event_count: int = 0
