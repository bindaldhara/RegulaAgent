# RegulaAgent

Policy-bounded healthcare appointment scheduling agent (2-day implementation plan).

## Day 1 progress (through morning break)

- Monorepo: `backend/`, `frontend/`, `tests/`, `datasets/`
- FastAPI backend, React + Vite + Tailwind scaffold, PostgreSQL via Docker Compose
- PostgreSQL via **psycopg** + raw SQL (`backend/db/schema.sql`): patients, doctors, appointments, conversations, messages, agent runs, tool calls, policy decisions, audit events
- LangGraph workflow: Intent → Identity → Consent → Action → Policy → Tool → Result validation → Response → Audit
- Structured intent classification (`BOOK_APPOINTMENT`, `CANCEL_APPOINTMENT`, `SEARCH_DOCTOR`, `CHECK_APPOINTMENT`, `UNKNOWN`) with entity extraction
- Mock intent provider for local dev; OpenRouter when `AGENT_PROVIDER=openrouter`

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
pip install pytest httpx
AGENT_PROVIDER=mock uvicorn main:app --app-dir backend --reload
```

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/agent/run \
  -H 'Content-Type: application/json' \
  -d '{"message":"Book a cardiologist tomorrow."}' | python3 -m json.tool
```

```bash
make test
make start                  # Docker: Postgres + API + chat UI (http://localhost:5173)
```

See [docs/day-1-morning.md](docs/day-1-morning.md) for details.
