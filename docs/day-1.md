# Day 1 — Complete

## Delivered

| Block | Status |
|-------|--------|
| Skeleton (FastAPI, React, Postgres, Docker) | Done |
| LangGraph workflow + DENY / ESCALATE | Done |
| Structured intents + entities | Done |
| Mock tools + Pydantic schemas | Done |
| PolicyEngine + risk levels | Done |
| Tool registry + router (validation, idempotency) | Done |
| Chat UI + login + runtime panel | Done |
| Audit persistence (psycopg SQL) | Done |

## Tools (Postgres-backed bookings)

- `search_doctors` — catalog in `doctors` table (seeded on migrate)
- `get_available_slots` — reads `schedule_slots` minus booked rows in `appointments` (see [scheduling-slots.md](scheduling-slots.md))
- `book_appointment` — persists to `appointments` (`appt1`, …; idempotent via `run_id`)
- `cancel_appointment`
- `get_patient_appointments`

## Demo booking

1. Sign in + grant consent.
2. `Book a cardiologist tomorrow.`
3. `Cancel my appointment.`

## Tests

```bash
AGENT_PROVIDER=mock pytest -q
```
