from fastapi import APIRouter, Depends

from api.deps import get_required_session
from schemas.auth import (
    AuthResponse,
    ConsentRequest,
    LoginEmailRequest,
    OtpRequestRequest,
    OtpRequestResponse,
    OtpVerifyRequest,
    PatientProfile,
)
from services.auth import (
    authenticate_email,
    patient_for_phone,
    reissue_with_consent,
    session_from_patient,
    verify_otp,
)
from services.demo_patients import DEMO_OTP_CODE

router = APIRouter(prefix="/auth", tags=["auth"])


def _auth_response(patient_session) -> AuthResponse:
    from services.auth import create_access_token

    token = create_access_token(patient_session)
    return AuthResponse(
        access_token=token,
        patient=PatientProfile(
            patient_id=patient_session.patient_id,
            full_name=patient_session.full_name,
            email=patient_session.email,
            phone=patient_session.phone,
            consent_granted=patient_session.consent_granted,
            auth_via=patient_session.auth_via,
        ),
    )


@router.post("/login", response_model=AuthResponse)
def login_email(body: LoginEmailRequest) -> AuthResponse:
    patient = authenticate_email(body.email, body.password)
    if patient is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Invalid email or password")
    return _auth_response(
        session_from_patient(patient, auth_via="email", display_name=body.full_name)
    )


@router.post("/otp/request", response_model=OtpRequestResponse)
def request_otp(body: OtpRequestRequest) -> OtpRequestResponse:
    if patient_for_phone(body.phone) is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Phone number not registered in demo")
    return OtpRequestResponse(
        message="Verification code sent (demo — no real SMS).",
        demo_code=DEMO_OTP_CODE,
    )


@router.post("/otp/verify", response_model=AuthResponse)
def verify_otp_login(body: OtpVerifyRequest) -> AuthResponse:
    if not verify_otp(body.code):
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Invalid verification code")
    patient = patient_for_phone(body.phone)
    if patient is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Phone number not registered in demo")
    return _auth_response(
        session_from_patient(patient, auth_via="phone", display_name=body.full_name)
    )


@router.get("/me", response_model=PatientProfile)
def me(session=Depends(get_required_session)) -> PatientProfile:
    return PatientProfile(
        patient_id=session.patient_id,
        full_name=session.full_name,
        email=session.email,
        phone=session.phone,
        consent_granted=session.consent_granted,
        auth_via=session.auth_via,
    )


@router.post("/consent", response_model=AuthResponse)
def update_consent(body: ConsentRequest, session=Depends(get_required_session)) -> AuthResponse:
    token = reissue_with_consent(session, body.granted)
    return AuthResponse(
        access_token=token,
        patient=PatientProfile(
            patient_id=session.patient_id,
            full_name=session.full_name,
            email=session.email,
            phone=session.phone,
            consent_granted=body.granted,
            auth_via=session.auth_via,
        ),
    )


@router.post("/logout")
def logout() -> dict[str, str]:
    return {"status": "ok"}
