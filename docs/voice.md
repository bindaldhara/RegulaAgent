# Voice (LiveKit)

Voice uses **LiveKit** for WebRTC audio and a **voice worker** that calls the same `POST /api/v1/agent/run` path as chat (policy, tools, audit unchanged).

## Architecture

```text
Browser (mic) ──WebRTC──► LiveKit room ◄── voice worker (STT / thin LLM / TTS)
                              │
                              └── HTTP ──► RegulaAgent API ──► LangGraph + Postgres
```

Final transcripts call RegulaAgent directly; scheduling stays in the API (policy + tools). The worker speaks replies with TTS (`session.say`) after each API response — chat text is synced separately on the `regula.agent` data channel.

## Default audio (free)

| | Provider | Model / voice |
|---|----------|----------------|
| **STT** | [Groq](https://console.groq.com) (free tier) | `whisper-large-v3-turbo` (`VOICE_GROQ_STT_MODEL`) |
| **TTS** | Microsoft Edge (no key) | `en-US-JennyNeural` (`VOICE_EDGE_TTS_VOICE`) |

Set `GROQ_API_KEY` in `.env`. `VOICE_AUDIO_MODE=free` is the default.

Paid alternates: `VOICE_AUDIO_MODE=openai|openrouter|livekit` (see `.env.example`).

## Environment

| Variable | Where | Purpose |
|----------|--------|---------|
| `LIVEKIT_URL` | API + worker | `wss://…` (LiveKit Cloud or self-hosted) |
| `LIVEKIT_API_KEY` | API + worker | Project API key |
| `LIVEKIT_API_SECRET` | API + worker | Project secret |
| `LIVEKIT_AGENT_NAME` | API + worker | Default `regula-voice` (must match worker registration) |
| `GROQ_API_KEY` | voice worker | Free-tier STT (required for `VOICE_AUDIO_MODE=free`) |
| `VOICE_AUDIO_MODE` | voice worker | `free` (default), `openai`, `openrouter`, or `livekit` |
| `REGULA_BACKEND_URL` | voice worker | Default `http://backend:8000` in Docker |
| `VOICE_FILLER` | voice worker | Short phrase while the API runs (default `One moment.`) |
| `VOICE_TTS_MAX_CHARS` | voice worker | Cap spoken reply length (default `1200`) |
| `VOICE_GROQ_STT_MODEL` | voice worker | Default `whisper-large-v3-turbo`; use `whisper-large-v3` for max accuracy |

Add the same LiveKit vars to `.env` (see `.env.example`).

### Latency

Voice calls use `voice_mode: true` on `POST /api/v1/agent/run` (skips Postgres audit persistence per turn). List replies (slots, appointments) are the same full text as chat; long speech is capped only by `VOICE_TTS_MAX_CHARS` in the worker. The worker reuses one HTTP connection, plays a brief filler while scheduling runs, starts TTS in parallel with chat sync, and uses faster Groq STT by default. Worker logs include `api_ms=` and `total_ms=` per turn.

## Troubleshooting (nothing happens when you speak)

1. **Voice worker running** — `docker compose up --build` includes `voice-worker`. Or locally: `cd voice_worker && python main.py dev`
2. **UI: “Agent in room”** — If it stays on **Waiting for agent…**, the worker is not connected or `LIVEKIT_AGENT_NAME` ≠ `regula-voice`.
3. **`GROQ_API_KEY`** — Required for free STT (get a key at console.groq.com). TTS uses Edge and needs no key.
4. **Scheduling consent** — Booking/cancel by voice still needs the consent checkbox (same as chat).
5. **Opening line** — As soon as **Agent in room** appears, you should hear *“Hey! I'm Regula…”* (played from `on_enter`, not after the call ends). Speak only after that. If **Heard** stays empty, check mic permission and `docker compose logs voice-worker` for TTS errors.
6. **No sound but “Agent in room”** — Browsers block autoplay unless you allow speaker output. On production, the Render wake can take 30–60s after you click **Voice**, so the click no longer counts as a “user gesture” for audio. Tap **Tap to hear Regula speak** in the voice card (or **Enable speaker**). The worker waits up to ~20s for that tap before speaking; you can tap again to replay the greeting.

7. **Render OOM (512Mi)** — If the voice service crashes with “Ran out of memory”, wait for a redeploy and retry voice once. The worker streams TTS through ffmpeg in small chunks to stay under the free-tier limit; avoid starting multiple voice tabs at once.

### `publisher data channel '_reliable' closed unexpectedly`

Usually **harmless**: it often appears when you click **End voice**, refresh the page, or lose network — the browser disconnects and LiveKit closes the reliable data channel. If voice **works** until you hang up, you can ignore it.

If it happens **during** a call (agent drops, no speech):

- Check `docker compose logs voice-worker` for STT/TTS or `GROQ_API_KEY` errors.
- Confirm **Agent in room** in the UI before speaking.
- Retry on a stable network; avoid ending voice while the agent is still speaking.

### Page goes black after you speak

Usually a **React crash** in the runtime panel (e.g. formatting intent/status when voice metadata was partial). The UI now sends full `run_id` from the worker, guards formatters/`RuntimePanel`, scopes LiveKit CSS so the room does not cover the viewport, and wraps the app in an error boundary (reload instead of a blank screen).

If it still happens: open the browser **console** for the error, confirm chat still shows the assistant reply (API may have succeeded even if audio dropped), and rebuild the frontend (`npm run dev` or `docker compose up --build`).

## Run locally

1. Configure LiveKit Cloud (or local server) and set `.env`.
2. API: `pip install -r backend/requirements.txt` and run uvicorn as usual.
3. Worker (separate terminal):

   ```bash
   cd voice_worker
   python3 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   brew install ffmpeg         # macOS — required for Edge TTS → PCM
   ```

   Load env from the repo root `.env` (the worker reads `../.env` automatically), or export:

   ```bash
   export LIVEKIT_URL=... LIVEKIT_API_KEY=... LIVEKIT_API_SECRET=...
   export REGULA_BACKEND_URL=http://127.0.0.1:8000   # or https://regula-agent-api.onrender.com
   export GROQ_API_KEY=...   # free at console.groq.com
   python main.py dev
   ```

   Use the venv Python (`source .venv/bin/activate`) — system `python3` will not have `httpx` until you install there.

4. Frontend: `npm install` in `frontend/`, then `npm run dev`.
5. Sign in → click **Voice** next to **Send** in the chat composer.

## Docker

```bash
docker compose up --build
```

Starts API, frontend, and `voice-worker` when `LIVEKIT_*` and `GROQ_API_KEY` are in `.env`.

`voice-worker` mounts `./voice_worker` into the container. After pulling or editing worker code, **recreate** it:

```bash
docker compose up -d --force-recreate voice-worker
docker compose logs -f voice-worker
```

On join you should see `build=2026-03-26-voice-reply-tts`, `Playing opening greeting`, and after you speak `TTS reply (...)` before audio plays. The worker image includes **ffmpeg** (Edge TTS MP3 decode). If you see chat updates but no sound, click **Enable speaker** in the voice card and check worker logs for TTS errors.

## API

- `GET /api/v1/voice/status` — `{ enabled, url }`
- `POST /api/v1/voice/token` — Bearer required; returns `{ token, url, room_name }` and dispatches agent `regula-voice` with session metadata (JWT, conversation id, chat history).

## UI sync

After each tool call, the worker publishes a `regula.agent` data message so the chat transcript and runtime panel can update without typing.
