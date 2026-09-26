# Intent classification

RegulaAgent routes each user message to **one intent**, then to a **deterministic tool** (policy + Postgres unchanged).

## Flow

```text
User message + chat history
        │
        ▼
  Intent classifier (LLM or mock)
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
| **`auto`** (default) | **OpenRouter LLM** when `OPENROUTER_API_KEY` is set; otherwise mock regex (local dev without a key). |
| **`openrouter`** / **`llm`** | Always use LLM; requires `OPENROUTER_API_KEY`. |
| **`mock`** | Regex rules only (used in `pytest`, no API cost). |

Configure in `.env`:

```env
AGENT_PROVIDER=auto
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=openai/gpt-4o-mini
```

## LLM classifier

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

Used when `AGENT_PROVIDER=mock` or when no OpenRouter key in `auto` mode. Fine for CI; brittle for natural language and voice STT. Prefer **`auto` + OpenRouter** for production and demos.
