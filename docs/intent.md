# Intent classification

RegulaAgent routes each user message to **one intent**, then to a **deterministic tool** (policy + Postgres unchanged).

## Flow

```text
User message + chat history
        │
        ▼
  Intent classifier (JEV, OpenRouter, or mock)
        │
        ▼
  enrich_booking_entities (doctor/date from follow-ups)
        │
        ▼
  refine_intent_from_history (short follow-ups)
        │
        ▼
  action_node → proposed tool → policy → tool → reply
```

## Modes (`AGENT_PROVIDER`)

| Value | Behavior |
|--------|----------|
| **`auto`** (default) | **1.** JEV if `TYPESAFE_API_KEY` or `OPENROUTER_API_KEY` (JEV on OpenRouter: [`~typesafe/jev-latest`](https://openrouter.ai/~typesafe/jev-latest)) → **2.** OpenRouter chat LLM (`OPENROUTER_MODEL`) if JEV is unavailable → **3.** mock regex. If JEV throws at runtime, **2.** then **3.** are tried in the same order. |
| **`jev`** / **`typesafe`** | Same chain as **`auto`** (JEV → OpenRouter LLM → mock). |
| **`openrouter`** / **`llm`** | OpenRouter **chat** LLM only (skip JEV); then mock if no key. |
| **`mock`** | Regex rules only (used in `pytest`, no API cost). |

Configure in `.env`:

```env
AGENT_PROVIDER=auto

# TypeSafe direct — https://console.typesafe.ai (optional if you use OpenRouter for JEV)
TYPESAFE_API_KEY=
TYPESAFE_MODEL=jev-latest

OPENROUTER_API_KEY=sk-or-v1-...
# JEV on OpenRouter (intent in auto/jev modes); not the chat model below
OPENROUTER_JEV_MODEL=~typesafe/jev-latest
OPENROUTER_MODEL=openai/gpt-4o-mini
# Optional: cap wait time for OpenRouter intent (seconds); then fallback to mock
INTENT_OPENROUTER_TIMEOUT_SECONDS=45
```

**`openrouter` mode:** use a **chat** model in `OPENROUTER_MODEL` (e.g. `openai/gpt-4o-mini`). Do not put `~typesafe/jev-latest` or `typesafe/jev-*` there — that slug is only for JEV (`OPENROUTER_JEV_MODEL` / `auto`). Wrong model + `openrouter` mode can hang or error.

## JEV classifier (TypeSafe System One)

- **Credentials:** `TYPESAFE_API_KEY` → `https://api.typesafe.ai`, or **`OPENROUTER_API_KEY`** → `https://openrouter.ai/api/v1/systemone` with `OPENROUTER_JEV_MODEL` (default `~typesafe/jev-latest`). Same `typesafe-sdk` client; billed on the key you use. Do **not** put the JEV slug in `OPENROUTER_MODEL` (that field is only for chat LLM intent in `openrouter` mode).
- One **`system_one`** call with a **Choice** question for routing intent and **Noul** questions for medical emergency and unauthorized record access.
- State is JSON: conversation transcript, current message, doctor catalog, and routing notes (follow-ups inherit context).
- Returns **choice + confidence** (and probabilities); no free-text generation — `assistant_reply` is filled from intent templates, then entities are normalized from the message (same as OpenRouter path).
- **Safety**: regex emergency / bulk-records short-circuit still runs before JEV; Nouls add a second line of defense when JEV is used.
- On API failure, falls back to **mock** rules and logs an error.

See [TypeSafe intent routing](https://docs.typesafe.ai/patterns/intent-routing) for the general pattern.

## OpenRouter LLM classifier

- **Structured output** (`IntentClassification` Pydantic schema): `intent`, `confidence`, `entities`, `assistant_reply`, `is_emergency`.
- **Chat history** (last ~10 turns) is sent with the current message so follow-ups like “28th September” or “slots available?” keep context.
- System prompt includes the **doctor catalog** and **intent → tool** mapping.
- After the LLM returns, entities are **normalized** (canonical doctor names, dates, `appt*` ids) — not re-classified with regex.
- **Safety**: emergency and bulk-records phrases are still short-circuited before the LLM (no tool call).
- On LLM failure, the worker falls back to **mock** rules and logs an error.

## Intents → tools

| Intent | Tool |
|--------|------|
| `SEARCH_DOCTOR` | `search_doctors` |
| `LIST_AVAILABLE_SLOTS` | `get_available_slots` |
| `BOOK_APPOINTMENT` | `book_appointment` |
| `CANCEL_APPOINTMENT` | `cancel_appointment` |
| `CHECK_APPOINTMENT` | `get_patient_appointments` |

## Mock regex

Used when `AGENT_PROVIDER=mock`, or when both JEV and OpenRouter LLM are unavailable (or fail) in `auto` / `jev` mode. Fine for CI; brittle for natural language and voice STT. Prefer **`auto`** with keys set for production and demos.
