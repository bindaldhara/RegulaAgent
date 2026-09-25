from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Literal

AuthVia = Literal["email", "phone"]

import jwt

from config import get_settings
from services.demo_patients import DEMO_OTP_CODE, DEMO_PATIENTS_BY_EMAIL, DEMO_PATIENTS_BY_PHONE, DemoPatient

ALGORITHM = "HS256"


@dataclass
class PatientSession:
    patient_id: str
    full_name: str
    email: str | None
    phone: str | None
    consent_granted: bool = False
    auth_via: AuthVia | None = None


def authenticate_email(email: str, password: str) -> DemoPatient | None:
    patient = DEMO_PATIENTS_BY_EMAIL.get(email.strip().lower())
    if patient and patient.password == password:
        return patient
    return None


def patient_for_phone(phone: str) -> DemoPatient | None:
    normalized = phone.strip().replace(" ", "").replace("-", "")
    if not normalized.startswith("+") and len(normalized) == 10:
        normalized = f"+1{normalized}"
    return DEMO_PATIENTS_BY_PHONE.get(normalized)


def verify_otp(code: str) -> bool:
    return code.strip() == DEMO_OTP_CODE


def create_access_token(session: PatientSession) -> str:
    settings = get_settings()
    now = int(time.time())
    payload = {
        "sub": session.patient_id,
        "name": session.full_name,
        "email": session.email,
        "phone": session.phone,
        "consent": session.consent_granted,
        "auth_via": session.auth_via,
        "iat": now,
        "exp": now + settings.auth_token_ttl_seconds,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.auth_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> PatientSession | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.auth_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
    return PatientSession(
        patient_id=str(payload["sub"]),
        full_name=str(payload.get("name", "")),
        email=payload.get("email"),
        phone=payload.get("phone"),
        consent_granted=bool(payload.get("consent", False)),
        auth_via=payload.get("auth_via"),
    )


def session_from_patient(
    patient: DemoPatient,
    consent_granted: bool = False,
    auth_via: AuthVia | None = None,
    display_name: str | None = None,
) -> PatientSession:
    return PatientSession(
        patient_id=patient.external_id,
        full_name=(display_name or patient.full_name).strip(),
        email=patient.email,
        phone=patient.phone,
        consent_granted=consent_granted,
        auth_via=auth_via,
    )


def issue_token_for_patient(patient: DemoPatient, consent_granted: bool = False) -> str:
    return create_access_token(session_from_patient(patient, consent_granted=consent_granted))


def reissue_with_consent(session: PatientSession, consent_granted: bool) -> str:
    return create_access_token(
        PatientSession(
            patient_id=session.patient_id,
            full_name=session.full_name,
            email=session.email,
            phone=session.phone,
            consent_granted=consent_granted,
            auth_via=session.auth_via,
        )
    )
