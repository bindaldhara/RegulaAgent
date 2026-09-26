import pytest

from agent.runtime import run_agent
from config import get_settings
from schemas.agent import AgentRunRequest
from schemas.enums import HandoffState, IdentityStatus, PolicyOutcome, WorkflowStep


@pytest.fixture(autouse=True)
def mock_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_PROVIDER", "mock")
    get_settings.cache_clear()


def test_search_doctor_allowed_without_identity() -> None:
    response = run_agent(AgentRunRequest(message="Search for a cardiologist tomorrow."), persist=False)
    assert response.policy is not None
    assert response.policy.outcome == PolicyOutcome.ALLOW
    assert response.proposed_action is not None
    assert response.proposed_action.tool_name == "search_doctors"


def test_book_denied_without_identity_and_consent() -> None:
    response = run_agent(AgentRunRequest(message="Book a cardiologist tomorrow."), persist=False)
    assert response.policy is not None
    assert response.policy.outcome == PolicyOutcome.DENY
    assert response.identity_status == IdentityStatus.PENDING


def test_book_allowed_with_identity_and_consent() -> None:
    response = run_agent(
        AgentRunRequest(
            message="Book a cardiologist tomorrow.",
            identity_verified=True,
            consent_granted=True,
            patient_id="patient-123",
        ),
        persist=False,
    )
    assert response.policy is not None
    assert response.policy.outcome == PolicyOutcome.ALLOW
    assert response.tool_result is not None
    assert response.current_step in (WorkflowStep.RESPONSE, WorkflowStep.AUDIT, WorkflowStep.END)


def test_emergency_escalates() -> None:
    response = run_agent(AgentRunRequest(message="I have severe chest pain."), persist=False)
    assert response.policy is not None
    assert response.policy.outcome == PolicyOutcome.ESCALATE
    assert response.handoff_state == HandoffState.QUEUED
