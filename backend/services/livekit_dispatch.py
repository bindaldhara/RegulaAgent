"""Explicit LiveKit agent dispatch (backup to token room_config)."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from livekit import api

logger = logging.getLogger(__name__)


def _http_url(livekit_wss_url: str) -> str:
    return livekit_wss_url.replace("wss://", "https://").replace("ws://", "http://")


async def _dispatch_async(
    *,
    livekit_url: str,
    api_key: str,
    api_secret: str,
    room_name: str,
    agent_name: str,
    metadata: dict[str, Any],
) -> None:
    async with api.LiveKitAPI(_http_url(livekit_url), api_key, api_secret) as lkapi:
        await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=agent_name,
                room=room_name,
                metadata=json.dumps(metadata),
            )
        )


def dispatch_voice_agent(
    *,
    livekit_url: str,
    api_key: str,
    api_secret: str,
    room_name: str,
    agent_name: str,
    metadata: dict[str, Any],
) -> None:
    try:
        asyncio.run(
            _dispatch_async(
                livekit_url=livekit_url,
                api_key=api_key,
                api_secret=api_secret,
                room_name=room_name,
                agent_name=agent_name,
                metadata=metadata,
            )
        )
    except Exception as exc:
        logger.warning("LiveKit agent dispatch failed (worker may still join via token): %s", exc)
