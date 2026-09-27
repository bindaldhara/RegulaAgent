# Evaluation (DeepEval + UI)

RegulaAgent ships a small **eval case suite** for demos and regression checks. Each case runs the real LangGraph agent (`AGENT_PROVIDER=mock` for stable intent) and scores the reply with **DeepEval G-Eval** using your **OpenRouter** (or OpenAI) key as the judge.

## Dataset

Cases live in [`datasets/eval_cases.json`](../datasets/eval_cases.json). Each case defines:

- User `message` and optional `identity_verified` / `consent_granted` / `patient_id`
- **Structural** expectations: `expected_policy`, `expected_tool`, `tool_must_succeed`
- **Semantic** rubric: `expected_output` (used by G-Eval)

## API

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/admin/eval/status` | DeepEval installed, judge API key present, case count |
| `GET /api/v1/admin/eval/cases` | List cases for the UI |
| `POST /api/v1/admin/eval/cases/{id}/run` | Run one case (agent + structural + G-Eval) |

A case **passes** when:

- **Structural** checks always apply (policy, tool, no bypass).
- **G-Eval** is required for `happy_path` and `escalation` categories.
- **`policy`** and **`adversarial`** cases pass on structural alone; G-Eval is **advisory** (shown, not blocking).

## UI

Open **http://localhost:5173/admin** (not the main chat home). Each case has **Run eval** — results show structural pass/fail, G-Eval score, reason, and reply snippet.

## Configuration

```env
OPENROUTER_API_KEY=sk-or-v1-...   # judge + optional live agent
OPENROUTER_MODEL=openai/gpt-4o-mini
```

Alternatively set `OPENAI_API_KEY` for the judge only (direct OpenAI, no extra headers).

OpenRouter requires `HTTP-Referer` / `X-Title`; the eval runner sends those automatically using `OPENROUTER_APP_URL`.

Install DeepEval in the backend environment:

```bash
pip install -r backend/requirements.txt
```

Docker: rebuild backend after pulling (`docker compose build backend`).

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
- G-Eval uses a small LLM call per run (cost + a few seconds latency).
- Telemetry: `DEEPEVAL_TELEMETRY_OPT_OUT=YES` is set by default in the runner.
