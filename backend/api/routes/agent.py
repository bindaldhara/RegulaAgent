from fastapi import APIRouter, Depends

from agent.runtime import run_agent
from api.deps import get_optional_session
from schemas.agent import AgentRunRequest, AgentRunResponse
from services.auth import PatientSession

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/run", response_model=AgentRunResponse)
def agent_run(
    request: AgentRunRequest,
    session: PatientSession | None = Depends(get_optional_session),
) -> AgentRunResponse:
    if session is not None:
        request = request.model_copy(
            update={
                "patient_id": session.patient_id,
                "identity_verified": True,
                "consent_granted": session.consent_granted,
            }
        )
    return run_agent(request, persist=True)
