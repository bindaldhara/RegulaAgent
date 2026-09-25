"""Persist agent runs with parameterized SQL."""

from __future__ import annotations

import json
import uuid
from typing import Any

from db.connection import get_connection


def persist_agent_run(
    conversation_id: uuid.UUID,
    run_id: str,
    user_message: str,
    state: dict[str, Any],
) -> None:
    intent = state.get("intent")
    intent_str = str(intent.intent) if intent else None
    assistant_reply = state.get("assistant_reply", "")
    metadata = json.dumps({"run_id": run_id})

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO conversations (id, updated_at)
                VALUES (%s, NOW())
                ON CONFLICT (id) DO UPDATE SET updated_at = NOW()
                """,
                (conversation_id,),
            )

            cur.execute(
                """
                INSERT INTO messages (conversation_id, role, content, intent)
                VALUES (%s, 'user', %s, %s)
                """,
                (conversation_id, user_message, intent_str),
            )

            cur.execute(
                """
                INSERT INTO messages (conversation_id, role, content, metadata_json)
                VALUES (%s, 'assistant', %s, %s::jsonb)
                """,
                (conversation_id, assistant_reply, metadata),
            )

            cur.execute(
                """
                INSERT INTO agent_runs (
                    conversation_id, run_id, status, current_step, final_outcome, finished_at
                )
                VALUES (%s, %s, 'completed', %s, %s, NOW())
                RETURNING id
                """,
                (
                    conversation_id,
                    run_id,
                    str(state.get("current_step")),
                    state.get("final_outcome"),
                ),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("agent_runs insert did not return id")
            agent_run_id = row[0]

            policy = state.get("policy_decision")
            proposed = state.get("proposed_action")
            if policy:
                cur.execute(
                    """
                    INSERT INTO policy_decisions (
                        agent_run_id, decision, risk_level, reason, proposed_action
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        agent_run_id,
                        str(policy.outcome),
                        str(policy.risk_level),
                        policy.reason,
                        proposed.tool_name if proposed else None,
                    ),
                )

            for event in state.get("audit_events") or []:
                cur.execute(
                    """
                    INSERT INTO audit_events (agent_run_id, conversation_id, event_type, payload)
                    VALUES (%s, %s, %s, %s::jsonb)
                    """,
                    (
                        agent_run_id,
                        conversation_id,
                        event["event_type"],
                        json.dumps(event.get("payload")),
                    ),
                )
