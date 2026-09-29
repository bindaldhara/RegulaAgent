from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from agent.runtime import iter_agent_run_events, run_agent
from api.deps import get_optional_session
from schemas.agent import AgentRunRequest, AgentRunResponse
from services.auth import PatientSession

router = APIRouter(prefix="/agent", tags=["agent"])


def _apply_session(request: AgentRunRequest, session: PatientSession | None) -> AgentRunRequest:
    if session is None:
        return request
    return request.model_copy(
        update={
            "patient_id": session.patient_id,
            "identity_verified": True,
            "consent_granted": session.consent_granted,
        }
    )


@router.post("/run", response_model=AgentRunResponse)
def agent_run(
    request: AgentRunRequest,
    session: PatientSession | None = Depends(get_optional_session),
) -> AgentRunResponse:
    request = _apply_session(request, session)
    return run_agent(request, persist=not request.voice_mode)


@router.post("/run/stream")
def agent_run_stream(
    request: AgentRunRequest,
    session: PatientSession | None = Depends(get_optional_session),
) -> StreamingResponse:
    request = _apply_session(request, session)
    persist = not request.voice_mode
    return StreamingResponse(
        iter_agent_run_events(request, persist=persist),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
