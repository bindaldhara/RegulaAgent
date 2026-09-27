from typing import Any

from pydantic import BaseModel, Field

from schemas.agent import ChatHistoryTurn


class EvalCaseSummary(BaseModel):
    id: str
    title: str
    category: str
    message: str


class EvalCaseDefinition(BaseModel):
    id: str
    title: str
    category: str
    message: str
    identity_verified: bool = False
    consent_granted: bool = False
    patient_id: str | None = None
    chat_history: list[ChatHistoryTurn] = Field(default_factory=list)
    expected_policy: str
    expected_tool: str | None = None
    tool_must_succeed: bool = False
    expected_output: str
    evaluation_criteria: str | None = None


class StructuralCheckResult(BaseModel):
    passed: bool
    expected_policy: str
    actual_policy: str | None
    expected_tool: str | None
    actual_tool: str | None
    tool_success_ok: bool
    details: list[str] = Field(default_factory=list)


class DeepEvalResult(BaseModel):
    passed: bool
    score: float | None = None
    threshold: float
    reason: str | None = None
    error: str | None = None
    required_for_pass: bool = True


class EvalRunResponse(BaseModel):
    case_id: str
    passed: bool
    structural: StructuralCheckResult
    deepeval: DeepEvalResult
    reply: str
    run_id: str
    agent_snapshot: dict[str, Any] = Field(default_factory=dict)


class EvalStatusResponse(BaseModel):
    deepeval_available: bool
    judge_configured: bool
    judge_model: str | None = None
    case_count: int
    agent_provider_for_eval: str = "mock"
