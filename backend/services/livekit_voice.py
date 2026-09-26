"""LiveKit access tokens with agent dispatch for Regula voice sessions."""

from __future__ import annotations

import json
import uuid
from datetime import timedelta
from typing import Any

from livekit.api import AccessToken, RoomAgentDispatch, RoomConfiguration, VideoGrants


def new_room_name() -> str:
    return f"regula-{uuid.uuid4().hex[:12]}"


def create_voice_room_token(
    *,
    api_key: str,
    api_secret: str,
    livekit_url: str,
    room_name: str,
    participant_identity: str,
    participant_name: str,
    agent_metadata: dict[str, Any],
    agent_name: str = "regula-voice",
    ttl_seconds: int = 600,
) -> tuple[str, str]:
    """Return (jwt, livekit_url) for the browser participant."""
    metadata_json = json.dumps(agent_metadata)
    grant = VideoGrants(
        room_join=True,
        room=room_name,
        can_publish=True,
        can_subscribe=True,
        can_publish_data=True,
    )
    token = (
        AccessToken(api_key, api_secret)
        .with_identity(participant_identity)
        .with_name(participant_name)
        .with_ttl(timedelta(seconds=ttl_seconds))
        .with_grants(grant)
        .with_room_config(
            RoomConfiguration(
                agents=[RoomAgentDispatch(agent_name=agent_name, metadata=metadata_json)],
            )
        )
    )
    return token.to_jwt(), livekit_url
