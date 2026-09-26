from policy.engine import PolicyEngine
from schemas.agent import ProposedAction
from schemas.enums import ConsentStatus, IdentityStatus, PolicyOutcome, RiskLevel
from schemas.enums import Intent
from schemas.intent import ExtractedEntities, IntentClassification


def test_emergency_escalates() -> None:
    engine = PolicyEngine()
    intent = IntentClassification(
        intent=Intent.UNKNOWN,
        confidence=0.9,
        entities=ExtractedEntities(),
        assistant_reply="",
        is_emergency=True,
    )
    decision = engine.evaluate(intent, None, IdentityStatus.UNVERIFIED, ConsentStatus.PENDING, None)
    assert decision.outcome == PolicyOutcome.ESCALATE


def test_book_denied_without_consent() -> None:
    engine = PolicyEngine()
    intent = IntentClassification(
        intent=Intent.BOOK_APPOINTMENT,
        confidence=0.9,
        entities=ExtractedEntities(),
        assistant_reply="",
    )
    proposed = ProposedAction(tool_name="book_appointment", arguments={}, risk_level=RiskLevel.MEDIUM)
    decision = engine.evaluate(
        intent,
        proposed,
        IdentityStatus.VERIFIED,
        ConsentStatus.PENDING,
        "patient-1",
    )
    assert decision.outcome == PolicyOutcome.DENY
