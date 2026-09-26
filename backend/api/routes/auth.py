from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import get_bearer_token, get_required_session
from config import get_settings
from schemas.auth import ConsentRequest, PatientProfile, ProfileUpsertRequest
from services.auth import PatientSession, profile_to_session, sync_profile_from_claims
from services.patient_profiles import set_consent
from services.supabase_auth import decode_supabase_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


def _require_supabase() -> None:
    if not get_settings().supabase_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase auth is not configured (set SUPABASE_URL)",
        )


def _to_profile(session: PatientSession) -> PatientProfile:
    return PatientProfile(
        patient_id=session.patient_id,
        full_name=session.full_name,
        email=session.email,
        phone=session.phone,
        consent_granted=session.consent_granted,
        auth_via=session.auth_via,
    )


@router.post("/profile", response_model=PatientProfile)
def upsert_profile(
    body: ProfileUpsertRequest,
    token: str = Depends(get_bearer_token),
) -> PatientProfile:
    _require_supabase()
    claims = decode_supabase_access_token(token)
    if claims is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    session = sync_profile_from_claims(claims, body.full_name)
    return _to_profile(session)


@router.get("/me", response_model=PatientProfile)
def me(session: PatientSession = Depends(get_required_session)) -> PatientProfile:
    _require_supabase()
    return _to_profile(session)


@router.post("/consent", response_model=PatientProfile)
def update_consent(
    body: ConsentRequest,
    session: PatientSession = Depends(get_required_session),
) -> PatientProfile:
    _require_supabase()
    row = set_consent(session.patient_id, body.granted)
    updated = profile_to_session(row, session.auth_via)
    return _to_profile(updated)


@router.post("/logout")
def logout() -> dict[str, str]:
    return {"status": "ok"}
