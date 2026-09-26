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
