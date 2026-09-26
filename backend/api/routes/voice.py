from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import get_bearer_token, get_optional_session
from config import get_settings
from schemas.agent import ChatHistoryTurn, VoiceTokenRequest, VoiceTokenResponse
from services.auth import PatientSession
from services.livekit_dispatch import dispatch_voice_agent
from services.livekit_voice import create_voice_room_token, new_room_name

router = APIRouter(prefix="/voice", tags=["voice"])


@router.get("/status")
def voice_status() -> dict[str, object]:
    settings = get_settings()
    return {
        "enabled": settings.livekit_configured,
        "url": settings.livekit_url or None,
        "agent_name": settings.livekit_agent_name,
    }


@router.post("/token", response_model=VoiceTokenResponse)
def voice_token(
    body: VoiceTokenRequest,
    bearer: str = Depends(get_bearer_token),
    session: PatientSession | None = Depends(get_optional_session),
) -> VoiceTokenResponse:
    settings = get_settings()
    if not settings.livekit_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LiveKit is not configured (LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET).",
        )

    room_name = new_room_name()
    identity = session.patient_id if session else f"guest-{uuid.uuid4().hex[:8]}"
    display_name = session.full_name if session and session.full_name else "Patient"

    history = [{"role": t.role, "content": t.content} for t in body.chat_history[-20:]]
    agent_metadata = {
        "access_token": bearer,
        "conversation_id": str(body.conversation_id) if body.conversation_id else None,
        "chat_history": history,
        "patient_id": session.patient_id if session else None,
        "consent_granted": bool(session and session.consent_granted),
    }

    jwt, url = create_voice_room_token(
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
        livekit_url=settings.livekit_url,
        room_name=room_name,
        participant_identity=identity,
        participant_name=display_name,
        agent_metadata=agent_metadata,
        agent_name=settings.livekit_agent_name,
    )

    dispatch_voice_agent(
        livekit_url=settings.livekit_url,
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
        room_name=room_name,
        agent_name=settings.livekit_agent_name,
        metadata=agent_metadata,
    )

    return VoiceTokenResponse(
        token=jwt,
        url=url,
        room_name=room_name,
        agent_metadata_preview={k: v for k, v in agent_metadata.items() if k != "access_token"},
    )
