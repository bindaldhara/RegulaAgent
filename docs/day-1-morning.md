# Day 1 — Morning (through break)

## Completed scope

| Block | Deliverable |
|-------|-------------|
| 09:00–09:45 | Monorepo skeleton, Docker Compose, env config, PostgreSQL schema (psycopg + SQL) |
| 09:45–11:00 | `AgentState`, LangGraph workflow, ALLOW / DENY / ESCALATE branches |
| 11:00–12:00 | Pydantic structured intents, mock + OpenRouter classifiers, entity slots |

## Agent API

`POST /api/v1/agent/run`

| Field | Purpose |
|-------|---------|
| `message` | Patient utterance |
| `identity_verified` | Simulates verified patient for protected actions |
| `consent_granted` | Simulates scheduling consent |
| `patient_id` | Optional patient identifier |

## Workflow branches

- **ESCALATE**: emergency symptoms → skip identity/consent → policy → handoff response
- **DENY**: missing identity/consent for booking/cancel, unknown intent, protected data patterns
- **ALLOW**: public doctor search; booking/cancel when identity + consent are satisfied (tool execution deferred until afternoon)

## Chat UI

Patient chat lives in `frontend/` and calls `POST /api/v1/agent/run` via the Vite `/api` proxy.

- Message history with `conversation_id` continuity
- Session panel: patient ID, identity verified, consent granted (demo controls)
- Runtime panel: workflow step, intent, policy, proposed tool, tool status, handoff

Start with Docker: `make start` → http://localhost:5173

## Afternoon (remaining)

Mock healthcare tools, full policy/risk engine, tool router, end-to-end booking.
