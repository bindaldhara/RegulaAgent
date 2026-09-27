# Deployment (Vercel + Render, free tier)

## Free tier only (no paid hosting)

This project is set up to use **free plans only** on Vercel and Render:

| Service | Name | Plan (must stay) |
|---------|------|------------------|
| Vercel | `regula-agent` | **Hobby** — do not enable Pro or paid add-ons |
| Render | `regula-agent-api` | **Free** web service |
| Render | `regula-agent-voice` | **Free** web service |

Do **not** upgrade these to Starter/Standard on Render or Pro on Vercel. In the Render dashboard, confirm **Instance type → Free** for both services.

**Third-party free tiers** (usage limits apply; overages are on your accounts, not Vercel/Render):

- **Supabase** — free project for Postgres + Auth  
- **LiveKit Cloud** — free tier for WebRTC rooms  
- **Groq** — free API key for voice STT (`GROQ_API_KEY`)  
- **OpenRouter** — use `OPENROUTER_MODEL=openrouter/free` to avoid paid models  
- **Edge TTS** — no key (used by voice worker)

Paid voice modes (`VOICE_AUDIO_MODE=openai`, etc.) are not used in production env on Render.

| Component | Platform | Plan |
|-----------|----------|------|
| React UI (`frontend/`) | [Vercel](https://vercel.com) | Hobby (free) |
| FastAPI API (`backend/`) | [Render](https://render.com) | Free web service |
| Postgres + Auth | Supabase | Free tier (configure locally) |

Voice (`voice_worker/`) runs as a second **free** Render web service when deployed (see `render.yaml` / dashboard). The worker is tuned for **512Mi** (`num_idle_processes=0`, process executor, streaming Edge TTS decode). If Render logs show **Out of memory**, close extra voice tabs and redeploy the latest worker; do not run multiple concurrent voice rooms on the free instance.

**Log noise:** `event loop blocked` lines from `livekit.agents` are warnings (slow SSL/VAD on 512MB CPU), not necessarily a crash. The worker sets `record=False` and `OTEL_SDK_DISABLED=true` on Render to avoid telemetry deadlocks.

- **Worker URL (health only):** https://regula-agent-voice.onrender.com  
- **Dashboard:** https://dashboard.render.com/web/srv-dasd0nojo6nc73b91m20  

Local-only alternative: `docker compose up voice-worker` with production API URL in `REGULA_BACKEND_URL`.

### Voice worker on GCP (recommended if Render OOMs)

Use a small **Compute Engine** VM (default **e2-small**, 2 GB RAM) instead of Render for `voice_worker` only. Step-by-step: **[docs/gcp-voice-worker.md](gcp-voice-worker.md)** (`deploy/gcp/provision-voice-gce.sh`). Set Vercel `VITE_VOICE_WAKE_URL` to `http://YOUR_VM_IP:8080/` and suspend Render `regula-agent-voice` so a single `regula-voice` agent registers.

## Architecture

- The browser loads the static app from Vercel.
- `/api/*` requests are rewritten to the Render backend (`frontend/vercel.json`).
- The API uses Supabase Postgres and JWT verification via env vars on Render.

## Render — API

- **Service:** `regula-agent-api`
- **Runtime:** Docker (`docker/backend.Dockerfile`, repo root context)
- **Health check:** `/health`
- **URL:** `https://regula-agent-api.onrender.com` (may include a suffix if the name is taken)

Set the same backend secrets as local `.env` (see `.env.example`): `SUPABASE_*`, `DATABASE_URL` or `POSTGRES_*`, `OPENROUTER_*`, optional `LIVEKIT_*`.

Update `OPENROUTER_APP_URL` to your Vercel production URL after the frontend is live.

Free Render services spin down after inactivity; the first request after idle can take ~30–60s.

### Private GitHub repo

If the repo is private, Render must be allowed to clone it: [Render → Account Settings → GitHub](https://dashboard.render.com/u/settings#integrations) → configure access and enable this repository.

**Option A — Blueprint:** open [Render Blueprint deploy](https://dashboard.render.com/select-repo?type=blueprint), select `RegulaAgent`, and apply the repo’s `render.yaml`. Paste secret env vars when prompted (`sync: false` keys).

**Option B — Manual web service:** New → Web Service → repo `RegulaAgent`, Docker, `docker/backend.Dockerfile`, context `.`, plan **Free**, region **Singapore**, health path `/health`.

**Live service (MCP):** [regula-agent-api](https://regula-agent-api.onrender.com) — dashboard [Render](https://dashboard.render.com/web/srv-dascrk17lnhs738l971g).

## Vercel — frontend

- **Project:** linked to `bindaldhara/RegulaAgent`, root directory `frontend`
- **Build:** `npm run build` → `dist/`

Required env vars (Production + Preview):

- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`

In Supabase → Authentication → URL configuration, add your Vercel site URL to **Site URL** and **Redirect URLs**.

If the Render service URL differs from `regula-agent-api.onrender.com`, update the rewrite target in `frontend/vercel.json` and redeploy Vercel.

## Deploy updates

Push to `main`. Render and Vercel auto-deploy when connected to the GitHub repo.
