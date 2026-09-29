"""Run agent workflow and optionally persist to PostgreSQL."""

from __future__ import annotations

import json
import queue
import re
import threading
import uuid
from collections.abc import Iterator
from typing import Any

from agent.state import AgentState
from agent.workflow import get_agent_workflow
from config import get_settings
from db.persistence import persist_agent_run
from schemas.agent import AgentRunRequest, AgentRunResponse
from schemas.enums import ConsentStatus, HandoffState, IdentityStatus, WorkflowStep


def _initial_state(request: AgentRunRequest, conversation_id: uuid.UUID, run_id: str) -> AgentState:
    identity = IdentityStatus.VERIFIED if request.identity_verified else IdentityStatus.UNVERIFIED
    consent = ConsentStatus.GRANTED if request.consent_granted else ConsentStatus.PENDING
    return AgentState(
        conversation_id=conversation_id,
        run_id=run_id,
        user_message=request.message,
        patient_id=request.patient_id,
        identity_status=identity,
        consent_status=consent,
        identity_verified_input=request.identity_verified,
        consent_granted_input=request.consent_granted,
        chat_history=[{"role": t.role, "content": t.content} for t in request.chat_history],
        voice_mode=request.voice_mode,
        handoff_state=HandoffState.NONE,
        current_step=WorkflowStep.INTENT,
        audit_events=[],
    )


def _build_response(
    conversation_id: uuid.UUID,
    run_id: str,
    final_state: dict[str, Any],
) -> AgentRunResponse:
    intent = final_state.get("intent")
    policy = final_state.get("policy_decision")
    proposed = final_state.get("proposed_action")
    return AgentRunResponse(
        conversation_id=conversation_id,
        run_id=run_id,
        reply=final_state.get("assistant_reply", ""),
        current_step=final_state.get("current_step", WorkflowStep.END),
        intent=intent,
        identity_status=final_state.get("identity_status", IdentityStatus.UNVERIFIED),
        consent_status=final_state.get("consent_status", ConsentStatus.PENDING),
        policy=policy,
        proposed_action=proposed,
        tool_result=final_state.get("tool_result"),
        handoff_state=final_state.get("handoff_state", HandoffState.NONE),
        audit_event_count=len(final_state.get("audit_events") or []),
    )


def _persist_run(
    request: AgentRunRequest,
    conversation_id: uuid.UUID,
    run_id: str,
    final_state: dict[str, Any],
    persist: bool,
) -> None:
    if persist and not request.voice_mode and get_settings().postgres_host:
        try:
            persist_agent_run(conversation_id, run_id, request.message, final_state)
        except Exception:
            pass


def run_agent(request: AgentRunRequest, persist: bool = True) -> AgentRunResponse:
    conversation_id = request.conversation_id or uuid.uuid4()
    run_id = uuid.uuid4().hex

    graph = get_agent_workflow()
    final_state: dict[str, Any] = graph.invoke(_initial_state(request, conversation_id, run_id))

    _persist_run(request, conversation_id, run_id, final_state, persist)
    return _build_response(conversation_id, run_id, final_state)


def _sse_line(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, default=str)}\n\n"


def _iter_reply_chunks(reply: str) -> Iterator[str]:
    text = reply or ""
    if not text:
        return
    parts = re.split(r"(\s+)", text)
    for part in parts:
        if part:
            yield part


def iter_agent_run_events(
    request: AgentRunRequest,
    persist: bool = True,
) -> Iterator[str]:
    """Server-Sent Events: step updates, reply chunks, then full AgentRunResponse."""
    conversation_id = request.conversation_id or uuid.uuid4()
    run_id = uuid.uuid4().hex
    graph = get_agent_workflow()
    final_state: dict[str, Any] = {}
    last_step: str | None = None

    try:
        yield ": regula-agent-stream\n\n"
        yield _sse_line("status", {"phase": "intent", "message": "Understanding your request…"})

        initial = _initial_state(request, conversation_id, run_id)
        event_queue: queue.Queue[tuple[str, Any]] = queue.Queue()

        def _run_graph() -> None:
            try:
                state: dict[str, Any] = {}
                for state in graph.stream(initial, stream_mode="values"):
                    step = state.get("current_step")
                    step_value = (
                        step.value if isinstance(step, WorkflowStep) else str(step) if step else None
                    )
                    if step_value:
                        event_queue.put(("step", step_value))
                event_queue.put(("finished", state))
            except Exception as exc:
                event_queue.put(("error", exc))

        worker = threading.Thread(target=_run_graph, daemon=True)
        worker.start()

        while worker.is_alive() or not event_queue.empty():
            try:
                kind, payload = event_queue.get(timeout=1.0)
            except queue.Empty:
                yield ": keep-alive\n\n"
                continue

            if kind == "error":
                raise payload
            if kind == "step":
                step_value = str(payload)
                if step_value != last_step:
                    last_step = step_value
                    yield _sse_line("step", {"step": step_value})
            elif kind == "finished":
                final_state = payload
                break

        if not final_state:
            raise RuntimeError("Workflow finished without state")

        _persist_run(request, conversation_id, run_id, final_state, persist)
        response = _build_response(conversation_id, run_id, final_state)
        for chunk in _iter_reply_chunks(response.reply):
            yield _sse_line("token", {"text": chunk})
        yield _sse_line("done", response.model_dump(mode="json"))
    except Exception as exc:
        yield _sse_line("error", {"message": str(exc)})
