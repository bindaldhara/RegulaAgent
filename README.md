# RegulaAgent

Policy-bounded healthcare appointment scheduling agent (2-day implementation plan).

## Day 1 — complete

See [docs/day-1.md](docs/day-1.md). Book/cancel via chat after sign-in + consent.

## Day 1 progress (summary)

- Monorepo: `backend/`, `frontend/`, `tests/`, `datasets/`
- FastAPI backend, React + Vite + Tailwind scaffold
- **Supabase Auth** (frontend) + JWT verification on the API; **Supabase Postgres** via `DATABASE_URL` and **psycopg** + raw SQL (`backend/db/schema.sql`)
- LangGraph workflow: Intent → Identity → Consent → Action → Policy → Tool → Result validation → Response → Audit
- Structured intent classification with entity extraction — **LLM via OpenRouter** by default (`AGENT_PROVIDER=auto`); mock regex for tests — see [docs/intent.md](docs/intent.md)

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
make start                  # Docker: API + chat UI (http://localhost:5173)
```

Configure Supabase first: [docs/supabase.md](docs/supabase.md).

Optional voice: [docs/voice.md](docs/voice.md) (LiveKit + `voice_worker`).

Evaluation UI + DeepEval: [docs/evaluation.md](docs/evaluation.md).

Production (Vercel + Render, free tier): [docs/deployment.md](docs/deployment.md).

