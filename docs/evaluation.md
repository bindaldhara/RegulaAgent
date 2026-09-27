# Evaluation (DeepEval + UI)

RegulaAgent ships a small **eval case suite** for demos and regression checks. Each case runs the **same LangGraph agent as chat** (whatever `AGENT_PROVIDER` is on the API: `auto`, `openrouter`, or `mock`) and scores the reply with **DeepEval G-Eval** using your **OpenRouter** (or OpenAI) key as the judge.

## Dataset

Cases live in [`datasets/eval_cases.json`](../datasets/eval_cases.json). Each case defines:

- User `message` and optional `identity_verified` / `consent_granted` / `patient_id`
- **Structural** expectations: `expected_policy`, `expected_tool`, `tool_must_succeed`
- **Semantic** rubric: `expected_output` (used by G-Eval)

## API

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/admin/eval/status` | Agent provider, DeepEval, judge key, case count |
| `GET /api/v1/admin/eval/cases` | List cases for the UI |
| `POST /api/v1/admin/eval/cases/{id}/run` | Run one case (agent + structural + G-Eval) |

A case **passes** when:

- **Structural** checks always apply (policy, tool, no bypass).
- **G-Eval** is required for `happy_path` and `escalation` categories.
- **`policy`** and **`adversarial`** cases pass on structural alone; G-Eval is **advisory** (shown, not blocking).

G-Eval **threshold** is **0.5** (see `DEFAULT_GEVAL_THRESHOLD` in `backend/services/eval_runner.py`).

## UI

Open **http://localhost:5173/admin** (not the main chat home). Use **Run all** to execute every case in order, or **Run eval** on a single row. Results show structural pass/fail, G-Eval score, reason, and reply snippet; the header shows `passed/total` after a full run.

## Configuration

```env
AGENT_PROVIDER=auto          # same as chat: LLM intent when OPENROUTER_API_KEY is set
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=openai/gpt-4o-mini
# EVAL_JUDGE_MODEL=openai/gpt-4o-mini   # optional; avoid :free models for G-Eval JSON
```

Alternatively set `OPENAI_API_KEY` for the G-Eval judge only (direct OpenAI).

- **`auto` / `openrouter`**: eval uses LLM intent (realistic, may vary run to run).
- **`mock`**: regex intent only (stable CI-style runs; set on API if you want that for eval too).

OpenRouter requires `HTTP-Referer` / `X-Title` for the judge; the eval runner sends those using `OPENROUTER_APP_URL`.

Install DeepEval in the backend environment:

```bash
pip install -r backend/requirements.txt
```

Docker: rebuild/restart backend after pulling (`docker compose up -d --build backend`).

## Local CLI

Same runner as the API:

```bash
cd backend && PYTHONPATH=. python -c "
from services.eval_runner import run_eval_case
import json
print(json.dumps(run_eval_case('book_denied_no_consent').model_dump(), indent=2))
"
```

## Notes

- **Book with consent** needs Postgres seeded (`make migrate` / Docker `db` service).
- Each run may use **two** LLM calls when `AGENT_PROVIDER` is not `mock` (intent + G-Eval judge).
- Telemetry: `DEEPEVAL_TELEMETRY_OPT_OUT=YES` is set by default in the runner.
