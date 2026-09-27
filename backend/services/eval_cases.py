"""Load evaluation cases from datasets/eval_cases.json."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from schemas.eval import EvalCaseDefinition, EvalCaseSummary


def _dataset_candidates() -> list[Path]:
    here = Path(__file__).resolve()
    return [
        here.parents[2] / "datasets" / "eval_cases.json",
        Path("/datasets/eval_cases.json"),
        here.parents[1] / "datasets" / "eval_cases.json",
    ]


def dataset_path() -> Path:
    for path in _dataset_candidates():
        if path.is_file():
            return path
    raise FileNotFoundError(
        "eval_cases.json not found. Expected repo datasets/ or /datasets in Docker."
    )


def reload_eval_cases() -> None:
    load_eval_cases.cache_clear()


@lru_cache
def load_eval_cases() -> list[EvalCaseDefinition]:
    raw = json.loads(dataset_path().read_text(encoding="utf-8"))
    return [EvalCaseDefinition.model_validate(item) for item in raw.get("cases", [])]


def get_eval_case(case_id: str) -> EvalCaseDefinition | None:
    for case in load_eval_cases():
        if case.id == case_id:
            return case
    return None


def list_eval_summaries() -> list[EvalCaseSummary]:
    return [
        EvalCaseSummary(
            id=c.id,
            title=c.title,
            category=c.category,
            message=c.message,
        )
        for c in load_eval_cases()
    ]
