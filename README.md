# RegulaAgent

Policy-bounded healthcare appointment scheduling agent: chat and voice share the same LangGraph backend (intent, identity, consent, policy, tools, audit).

**Live app:** [regula-agent.vercel.app](https://regula-agent.vercel.app)

## Architecture (production)

| Component | Platform | Role |
|-----------|----------|------|
| **Frontend** | [Vercel](https://vercel.com) | React UI; `/api/*` proxied to the backend |
| **API** | [Render](https://render.com) (`regula-agent-api`) | FastAPI: auth, chat, `POST /api/v1/agent/run` (+ `/run/stream` SSE), voice token + agent dispatch |
| **Voice worker** | [GCP Compute Engine](https://cloud.google.com/compute) | LiveKit agent: STT → API → TTS (see [docs/gcp-voice-worker.md](docs/gcp-voice-worker.md)) |
| **Postgres + Auth** | [Supabase](https://supabase.com) | Users, profiles, consent |
| **WebRTC** | [LiveKit Cloud](https://livekit.io) | Browser ↔ agent audio and data channel |

Voice scheduling logic stays on the **API**; the worker is only realtime audio glue. Do not run two workers with the same `LIVEKIT_AGENT_NAME` (e.g. suspend Render `regula-agent-voice` when using GCP).

```text
Browser (Vercel) ──HTTP──► Render API ──► OpenRouter + Supabase
Browser ──WebRTC──► LiveKit ◄── GCP voice worker ──HTTP──► Render API
```

Details: [docs/deployment.md](docs/deployment.md) · Voice: [docs/voice.md](docs/voice.md)

## Quick start (local)

1. Copy `.env.example` → `.env` and configure Supabase ([docs/supabase.md](docs/supabase.md)), optional OpenRouter and LiveKit.

2. **API**

   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r backend/requirements.txt
   AGENT_PROVIDER=mock uvicorn main:app --app-dir backend --reload
   ```

3. **Frontend**

   ```bash
   cd frontend && npm install && npm run dev
   ```

4. **Voice (optional)** — second terminal:

   ```bash
   cd voice_worker
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   brew install ffmpeg   # macOS
   python main.py dev
   ```

   See [docs/voice.md](docs/voice.md).

**Docker:** `make start` (API + UI); add LiveKit/Groq to `.env` for `voice-worker` in compose.

**Tests:** `make test` or `pytest`

## Deploy updates

| Target | Trigger |
|--------|---------|
| Vercel (UI) | Push to `main` (root `frontend/`) |
| Render (API) | Push to `main` (`docker/backend.Dockerfile`) |
| GCP (voice) | `gcloud builds submit` + restart container on VM — [docs/gcp-voice-worker.md](docs/gcp-voice-worker.md) |

## Documentation

| Topic | Doc |
|-------|-----|
| Supabase setup | [docs/supabase.md](docs/supabase.md) |
| Auth & consent | [docs/auth.md](docs/auth.md) |
| Intent / LLM | [docs/intent.md](docs/intent.md) |
| Voice (LiveKit) | [docs/voice.md](docs/voice.md) |
| Vercel + Render | [docs/deployment.md](docs/deployment.md) |
| Voice on GCP | [docs/gcp-voice-worker.md](docs/gcp-voice-worker.md) |
| Evaluation (`/admin`, DeepEval) | [docs/evaluation.md](docs/evaluation.md) |
| Day 1 milestone | [docs/day-1.md](docs/day-1.md) |

## Evaluation (admin)

Open **`/admin`** on the frontend (e.g. http://localhost:5173/admin). Each case runs **`POST /api/v1/admin/eval/cases/{id}/run`**.

Eval uses the **same `AGENT_PROVIDER` as the API** (not a separate mock override):

| `AGENT_PROVIDER` | Eval agent behavior |
|------------------|---------------------|
| **`auto`** (typical) | JEV → OpenRouter LLM (`OPENROUTER_MODEL`) → mock |
| **`jev`** | TypeSafe JEV intent |
| **`openrouter`** | OpenRouter structured LLM intent |
| **`mock`** | Regex intent only (stable, no intent API cost) |

G-Eval (reply judge) always uses `OPENROUTER_API_KEY` or `OPENAI_API_KEY`; optional `EVAL_JUDGE_MODEL`. See [docs/evaluation.md](docs/evaluation.md).

## Repo layout

```text
backend/          FastAPI + LangGraph agent
frontend/         Vite + React
voice_worker/     LiveKit voice agent
deploy/gcp/       GCP voice worker scripts
datasets/         Eval cases
tests/
docs/
```
