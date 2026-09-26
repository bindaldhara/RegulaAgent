from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from config import get_settings
from services.patient_profiles import ProfileRow, get_profile, upsert_profile
from services.supabase_auth import decode_supabase_access_token

AuthVia = Literal["email", "phone"]


@dataclass
class PatientSession:
    patient_id: str
    full_name: str
    email: str | None
    phone: str | None
    consent_granted: bool = False
    auth_via: AuthVia | None = None


def _auth_via_from_claims(claims: dict[str, Any]) -> AuthVia:
    if claims.get("phone"):
        return "phone"
    return "email"


def _display_name_from_claims(claims: dict[str, Any]) -> str:
    meta = claims.get("user_metadata") or {}
    if isinstance(meta, dict):
        name = meta.get("full_name") or meta.get("name")
        if name:
            return str(name).strip()
    return ""


def session_from_token(token: str) -> PatientSession | None:
    settings = get_settings()
    if not settings.supabase_configured:
        return None
    claims = decode_supabase_access_token(token)
    if claims is None:
        return None
    user_id = str(claims["sub"])
    email = claims.get("email")
    phone = claims.get("phone")
    auth_via = _auth_via_from_claims(claims)

    profile = get_profile(user_id)
    if profile is not None:
        full_name = profile.full_name or _display_name_from_claims(claims)
        return PatientSession(
            patient_id=user_id,
            full_name=full_name,
            email=profile.email or email,
            phone=profile.phone or phone,
            consent_granted=profile.consent_granted,
            auth_via=auth_via,
        )

    full_name = _display_name_from_claims(claims)
    return PatientSession(
        patient_id=user_id,
        full_name=full_name,
        email=email,
        phone=phone,
        consent_granted=False,
        auth_via=auth_via,
    )


def decode_access_token(token: str) -> PatientSession | None:
    return session_from_token(token)


def profile_to_session(row: ProfileRow, auth_via: AuthVia | None) -> PatientSession:
    return PatientSession(
        patient_id=row.user_id,
        full_name=row.full_name,
        email=row.email,
        phone=row.phone,
        consent_granted=row.consent_granted,
        auth_via=auth_via,
    )


def sync_profile_from_claims(
    claims: dict[str, Any],
    full_name: str,
) -> PatientSession:
    user_id = str(claims["sub"])
    email = claims.get("email")
    phone = claims.get("phone")
    row = upsert_profile(user_id, full_name=full_name, email=email, phone=phone)
    return profile_to_session(row, _auth_via_from_claims(claims))
