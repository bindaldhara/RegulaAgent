# Deployment (Vercel + Render, free tier)

| Component | Platform | Plan |
|-----------|----------|------|
| React UI (`frontend/`) | [Vercel](https://vercel.com) | Hobby (free) |
| FastAPI API (`backend/`) | [Render](https://render.com) | Free web service |
| Postgres + Auth | Supabase | Free tier (configure locally) |

Voice (`voice_worker/`) is not deployed on Render in this setup; run it locally or add a separate worker service later.

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

Render must be allowed to clone `bindaldhara/RegulaAgent`: [Render → Account Settings → GitHub](https://dashboard.render.com/u/settings#integrations) → configure access and enable this repository. Then create the web service (or re-run deploy from the dashboard).

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
