"""Validate and execute tools with timeout/retry semantics."""

from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel, ValidationError

from tools.registry import get_tool


class ToolExecutionError(Exception):
    pass


def _inject_patient_args(
    tool_name: str,
    arguments: dict[str, Any],
    patient_id: str | None,
    idempotency_key: str | None,
) -> dict[str, Any]:
    args = dict(arguments)
    spec = get_tool(tool_name)
    if spec and spec.requires_patient:
        if not patient_id:
            raise ToolExecutionError("patient_id required for this tool")
        args["patient_id"] = patient_id
    if tool_name == "book_appointment" and idempotency_key:
        args["idempotency_key"] = idempotency_key
    return args


def execute_tool(
    tool_name: str,
    arguments: dict[str, Any],
    *,
    patient_id: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    spec = get_tool(tool_name)
    if spec is None:
        raise ToolExecutionError(f"Unknown tool: {tool_name}")

    merged = _inject_patient_args(tool_name, arguments, patient_id, idempotency_key)

    try:
        request = spec.request_model.model_validate(merged)
    except ValidationError as exc:
        raise ToolExecutionError(f"Invalid tool arguments: {exc}") from exc

    try:
        start = time.perf_counter()
        result: BaseModel = spec.handler(request)
        latency_ms = (time.perf_counter() - start) * 1000
        return {
            "status": "success",
            "tool": tool_name,
            "data": result.model_dump(mode="json"),
            "latency_ms": round(latency_ms, 2),
        }
    except ValueError as exc:
        raise ToolExecutionError(str(exc)) from exc
    except Exception as exc:
        raise ToolExecutionError(str(exc)) from exc
