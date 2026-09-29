# Patient chat UI

## Run

```bash
make start
```

Open http://localhost:5173 (API at http://localhost:8000).

Local frontend only (backend already running):

```bash
cd frontend && npm install && npm run dev
```

### `Failed to resolve import "motion/react"`

Docker kept an old `node_modules` volume from before `motion` was added. Fix:

```bash
make rebuild
```

Or locally: `cd frontend && npm install`.

## Features

| Area | Behavior |
|------|----------|
| Chat | Multi-turn messages; `conversation_id` sent on each request |
| Streaming | `POST /api/v1/agent/run/stream` (SSE): workflow **step** events, then **token** chunks of the reply, then **done** with full `AgentRunResponse`. Chat UI uses this by default. Voice still uses non-streaming `/run`. |

### Streaming on Vercel (production)

Vercel’s `/api` **rewrite to Render buffers the full response**, so SSE often looks broken (one blob, no typing, or missing `done`). Fix:

1. **Vercel** env: `VITE_API_BASE_URL=https://regula-agent-api.onrender.com` (your Render API URL, no trailing slash).
2. Redeploy the frontend.

The browser then calls Render **directly** for `/run/stream` only (CORS is open on the API). Other `/api` calls can stay on the Vercel rewrite.

### Debug checklist

| Symptom | Likely cause |
|---------|----------------|
| Network shows `/run` not `/run/stream` | Old frontend build |
| `/run/stream` → **404** | Redeploy Render API |
| `/run/stream` → **200** but one big response | Vercel proxy buffering → set `VITE_API_BASE_URL` |
| Error “Stream ended without a done event” | Proxy truncated body or parser bug (update frontend) |
| Works on `localhost:5173`, not on Vercel | Missing `VITE_API_BASE_URL` on Vercel |

Local dev: Vite proxies `/api` to `localhost:8000` — streaming works without `VITE_API_BASE_URL`.

### Frontend behavior

Chat uses `runAgentStream` (`frontend/src/api/agentStream.ts`): reads SSE, appends **token** chunks to the assistant bubble, updates workflow pills on **step**, finalizes on **done**. While tokens are arriving you see a violet cursor (`▍`) and **Thinking…** hides once text starts. If the network delivers one large chunk, the client still paints tokens frame-by-frame so typing is visible.
| Sign in | Email/password or phone OTP (demo); consent checkbox after login |
| Runtime panel | Workflow step, intent, policy outcome/risk, tool proposal, tool status, handoff |
| Motion | [Motion](https://motion.dev) + [Motionsites](https://motionsites.ai)-inspired layout — glow hero, pill prompts, glass cards, gradient CTAs |

## Demo flow

1. **Sign in** with Supabase (create an account or use your project test user).

Booking confirmations use short refs **`appt1`**, **`appt2`**, … All scheduling (slots, “tomorrow”, times shown) is in **IST** (Asia/Kolkata), e.g. `2026-09-26 9 AM IST`.

Signing in or signing out **starts a new chat** so messages and the runtime panel never carry over between accounts. Appointment data itself is always loaded for the **current** Supabase user on each request.
2. Send: `Book a cardiologist tomorrow.` → policy **DENY** until scheduling consent is checked.
3. Enable **I agree to schedule on my behalf**, send again → policy **ALLOW** (tool still deferred until mock APIs land).

See [auth.md](auth.md).
