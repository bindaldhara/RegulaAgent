"""Central policy + risk decisions: ALLOW, DENY, ESCALATE."""

from __future__ import annotations

from typing import Any

from schemas.agent import PolicyDecision, ProposedAction
from schemas.enums import ConsentStatus, IdentityStatus, Intent, PolicyOutcome, RiskLevel
from schemas.intent import IntentClassification

_BLOCKED_TOOLS = frozenset(
    {"get_patient_records", "list_all_patients", "list_all_patients_records"}
)


class PolicyEngine:
    def evaluate(
        self,
        intent: IntentClassification | None,
        proposed: ProposedAction | None,
        identity_status: IdentityStatus,
        consent_status: ConsentStatus,
        patient_id: str | None,
        tool_args: dict[str, Any] | None = None,
    ) -> PolicyDecision:
        if intent and intent.is_emergency:
            return PolicyDecision(
                outcome=PolicyOutcome.ESCALATE,
                risk_level=RiskLevel.CRITICAL,
                reason="Emergency symptoms reported; human handoff required.",
            )

        if proposed and proposed.tool_name in _BLOCKED_TOOLS:
            return PolicyDecision(
                outcome=PolicyOutcome.DENY,
                risk_level=RiskLevel.HIGH,
                reason="Protected patient data access is not allowed.",
            )

        if proposed and proposed.tool_name == "get_patient_appointments":
            if identity_status != IdentityStatus.VERIFIED:
                return PolicyDecision(
                    outcome=PolicyOutcome.DENY,
                    risk_level=RiskLevel.HIGH,
                    reason="Authorization required for protected patient data.",
                )
            if tool_args and patient_id and tool_args.get("patient_id") not in (None, patient_id):
                return PolicyDecision(
                    outcome=PolicyOutcome.DENY,
                    risk_level=RiskLevel.HIGH,
                    reason="Cannot access another patient's appointments.",
                )

        if proposed and proposed.risk_level == RiskLevel.MEDIUM:
            if identity_status != IdentityStatus.VERIFIED:
                return PolicyDecision(
                    outcome=PolicyOutcome.DENY,
                    risk_level=RiskLevel.MEDIUM,
                    reason="Identity verification required before booking or cancellation.",
                )
            if consent_status != ConsentStatus.GRANTED:
                return PolicyDecision(
                    outcome=PolicyOutcome.DENY,
                    risk_level=RiskLevel.MEDIUM,
                    reason="Explicit consent required before protected scheduling actions.",
                )

        if intent and intent.intent == Intent.UNKNOWN and proposed is None:
            return PolicyDecision(
                outcome=PolicyOutcome.DENY,
                risk_level=RiskLevel.LOW,
                reason="No actionable intent; cannot invoke tools.",
            )

        if proposed is None:
            return PolicyDecision(
                outcome=PolicyOutcome.ALLOW,
                risk_level=RiskLevel.LOW,
                reason="No tool invocation required.",
            )

        return PolicyDecision(
            outcome=PolicyOutcome.ALLOW,
            risk_level=proposed.risk_level,
            reason="Action permitted by policy.",
        )
