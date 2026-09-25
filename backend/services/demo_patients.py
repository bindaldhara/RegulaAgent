"""Demo patient accounts for local login (not real PHI)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DemoPatient:
    external_id: str
    full_name: str
    email: str | None
    phone: str | None
    password: str


DEMO_PATIENTS_BY_EMAIL: dict[str, DemoPatient] = {
    "jane@example.com": DemoPatient(
        external_id="patient-jane-doe",
        full_name="Jane Doe",
        email="jane@example.com",
        phone="+1555010001",
        password="demo1234",
    ),
    "alex@example.com": DemoPatient(
        external_id="patient-alex-rivera",
        full_name="Alex Rivera",
        email="alex@example.com",
        phone="+1555020002",
        password="demo1234",
    ),
}

DEMO_PATIENTS_BY_PHONE: dict[str, DemoPatient] = {
    p.phone: p for p in DEMO_PATIENTS_BY_EMAIL.values() if p.phone
}

# Mock OTP for demo phone login
DEMO_OTP_CODE = "123456"
