from enum import StrEnum


class Intent(StrEnum):
    BOOK_APPOINTMENT = "BOOK_APPOINTMENT"
    CANCEL_APPOINTMENT = "CANCEL_APPOINTMENT"
    SEARCH_DOCTOR = "SEARCH_DOCTOR"
    CHECK_APPOINTMENT = "CHECK_APPOINTMENT"
    UNKNOWN = "UNKNOWN"


class WorkflowStep(StrEnum):
    INTENT = "intent"
    IDENTITY = "identity"
    CONSENT = "consent"
    ACTION = "action"
    POLICY = "policy"
    TOOL = "tool"
    RESULT_VALIDATION = "result_validation"
    RESPONSE = "response"
    AUDIT = "audit"
    HANDOFF = "handoff"
    END = "end"


class IdentityStatus(StrEnum):
    UNVERIFIED = "unverified"
    PENDING = "pending"
    VERIFIED = "verified"


class ConsentStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    GRANTED = "granted"
    DENIED = "denied"


class PolicyOutcome(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    ESCALATE = "ESCALATE"


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class HandoffState(StrEnum):
    NONE = "none"
    QUEUED = "queued"
    ACTIVE = "active"
