from fastapi import APIRouter, HTTPException

from schemas.eval import EvalCaseSummary, EvalRunResponse, EvalStatusResponse
from services.eval_cases import list_eval_summaries
from services.eval_runner import (
    deepeval_available,
    judge_configured,
    run_eval_case,
)
from config import get_settings

router = APIRouter(prefix="/admin/eval", tags=["admin-eval"])


@router.get("/status", response_model=EvalStatusResponse)
def eval_status() -> EvalStatusResponse:
    settings = get_settings()
    model = (settings.eval_judge_model or settings.openrouter_model) if judge_configured() else None
    return EvalStatusResponse(
        deepeval_available=deepeval_available(),
        judge_configured=judge_configured(),
        judge_model=model,
        case_count=len(list_eval_summaries()),
    )


@router.get("/cases", response_model=list[EvalCaseSummary])
def eval_cases() -> list[EvalCaseSummary]:
    return list_eval_summaries()


@router.post("/cases/{case_id}/run", response_model=EvalRunResponse)
def eval_run_case(case_id: str) -> EvalRunResponse:
    try:
        return run_eval_case(case_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown eval case: {case_id}")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
