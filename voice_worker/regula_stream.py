"""Consume RegulaAgent POST /api/v1/agent/run/stream (SSE)."""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

logger = logging.getLogger("regula-voice.stream")

OnStatus = Callable[[str], Awaitable[None]]
OnStep = Callable[[str], Awaitable[None]]
OnToken = Callable[[str], Awaitable[None]]


def _parse_sse_data(data_lines: list[str]) -> dict[str, Any]:
    return json.loads("\n".join(data_lines))


async def _dispatch_sse(
    event: str | None,
    data: dict[str, Any],
    *,
    on_status: OnStatus | None,
    on_step: OnStep | None,
    on_token: OnToken | None,
    reply_parts: list[str],
) -> dict[str, Any] | None:
    name = event or "message"
    if name == "status":
        message = data.get("message")
        if isinstance(message, str) and on_status:
            await on_status(message)
    elif name == "step":
        step = data.get("step")
        if isinstance(step, str) and on_step:
            await on_step(step)
    elif name == "token":
        text = data.get("text")
        if isinstance(text, str):
            reply_parts.append(text)
            if on_token:
                await on_token(text)
    elif name == "done":
        return data
    elif name == "error":
        message = data.get("message", "stream error")
        raise RuntimeError(str(message))
    return None


async def _consume_sse_block(
    event: str | None,
    data_lines: list[str],
    *,
    on_status: OnStatus | None,
    on_step: OnStep | None,
    on_token: OnToken | None,
    reply_parts: list[str],
) -> dict[str, Any] | None:
    if not data_lines:
        return None
    data = _parse_sse_data(data_lines)
    return await _dispatch_sse(
        event,
        data,
        on_status=on_status,
        on_step=on_step,
        on_token=on_token,
        reply_parts=reply_parts,
    )


async def call_regula_stream(
    client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    *,
    on_status: OnStatus | None = None,
    on_step: OnStep | None = None,
    on_token: OnToken | None = None,
) -> dict[str, Any]:
    reply_parts: list[str] = []
    done_payload: dict[str, Any] | None = None
    event_name: str | None = None
    data_lines: list[str] = []

    req_headers = {**headers, "Accept": "text/event-stream"}

    async with client.stream("POST", url, headers=req_headers, json=payload) as response:
        if response.status_code == 404:
            raise httpx.HTTPStatusError(
                "stream not available",
                request=response.request,
                response=response,
            )
        if response.status_code >= 400:
            body = await response.aread()
            raise RuntimeError(
                f"Regula stream HTTP {response.status_code}: {body[:300]!r}"
            )

        async for line in response.aiter_lines():
            if line.startswith(":"):
                continue
            if line == "":
                result = await _consume_sse_block(
                    event_name,
                    data_lines,
                    on_status=on_status,
                    on_step=on_step,
                    on_token=on_token,
                    reply_parts=reply_parts,
                )
                event_name = None
                data_lines = []
                if result is not None:
                    done_payload = result
                continue
            if line.startswith("event:"):
                event_name = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].strip())

        if data_lines:
            result = await _consume_sse_block(
                event_name,
                data_lines,
                on_status=on_status,
                on_step=on_step,
                on_token=on_token,
                reply_parts=reply_parts,
            )
            if result is not None:
                done_payload = result

    if done_payload is None:
        raise RuntimeError("Stream ended without done event")

    if not done_payload.get("reply") and reply_parts:
        done_payload = {**done_payload, "reply": "".join(reply_parts)}
    return done_payload


async def call_regula_json(
    client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = await client.post(url, headers=headers, json=payload)
    if response.status_code >= 400:
        raise RuntimeError(f"Regula API HTTP {response.status_code}: {response.text[:300]}")
    return response.json()
