import json
from pathlib import Path

import pytest

from services.eval_cases import dataset_path, get_eval_case, list_eval_summaries


def test_eval_dataset_loads() -> None:
    assert dataset_path().is_file()
    cases = list_eval_summaries()
    assert len(cases) >= 5
    assert get_eval_case("emergency_escalate") is not None


def test_eval_case_ids_unique() -> None:
    raw = json.loads(dataset_path().read_text(encoding="utf-8"))
    ids = [c["id"] for c in raw["cases"]]
    assert len(ids) == len(set(ids))


def test_run_eval_structural_without_judge(monkeypatch: pytest.MonkeyPatch) -> None:
    """Agent + structural checks only (no API call to G-Eval)."""
    from agent.runtime import run_agent
    from config import get_settings
    from schemas.agent import AgentRunRequest
    from services.eval_cases import get_eval_case
    from services.eval_runner import _run_structural

    monkeypatch.setenv("AGENT_PROVIDER", "mock")
    get_settings.cache_clear()

    case = get_eval_case("book_denied_no_consent")
    assert case is not None
    response = run_agent(
        AgentRunRequest(
            message=case.message,
            patient_id=case.patient_id,
            identity_verified=case.identity_verified,
            consent_granted=case.consent_granted,
        ),
        persist=False,
    )
    structural = _run_structural(case, response)
    assert structural.passed
    assert structural.actual_policy == "DENY"


def test_policy_case_passes_on_structural_only() -> None:
    from services.eval_cases import get_eval_case
    from services.eval_runner import _overall_pass
    from schemas.eval import DeepEvalResult, StructuralCheckResult

    case = get_eval_case("book_denied_no_consent")
    assert case is not None
    structural = StructuralCheckResult(
        passed=True,
        expected_policy="DENY",
        actual_policy="DENY",
        expected_tool=None,
        actual_tool=None,
        tool_success_ok=True,
        details=[],
    )
    deepeval_fail = DeepEvalResult(
        passed=False,
        score=0.2,
        threshold=0.5,
        reason="judge disagreed",
        error=None,
        required_for_pass=False,
    )
    assert _overall_pass(case, structural, deepeval_fail) is True
