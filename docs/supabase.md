# Supabase (auth + Postgres)

RegulaAgent uses **Supabase Auth** in the browser and **Supabase Postgres** for profiles, consent, and agent audit tables.

## 1. Create a project

1. [supabase.com](https://supabase.com) → New project.
2. **Project Settings → API**: copy **Project URL**, **anon public** key, and **JWT Secret**.
3. **Project Settings → Database**: copy the **URI** connection string (Session pooler is fine for the API).

## 2. Apply schema

In the Supabase **SQL Editor**, run the contents of:

- `backend/db/schema.sql`

Or from your machine (with `DATABASE_URL` set):

```bash
make migrate
```

## 3. Configure env

Copy `.env.example` → `.env` and set:

| Variable | Where |
|----------|--------|
| `SUPABASE_URL` | API → Project URL |
| `SUPABASE_JWT_SECRET` | API → **JWT Secret** (legacy HS256 projects). New projects with **JWT signing keys** can verify via JWKS using `SUPABASE_URL` only. |
| `DATABASE_URL` | Database → Connection string (only if password is URL-safe) |
| `POSTGRES_HOST` / `POSTGRES_USER` / `POSTGRES_PASSWORD` / … | **Recommended** when the DB password contains `+`, `@`, `/`, etc. |

If `GET /api/v1/auth/me` returns **500**, check backend logs for `failed to resolve host` — that means `DATABASE_URL` was parsed incorrectly. Remove `DATABASE_URL` and use `POSTGRES_*` with the raw password from the Supabase dashboard.
| `VITE_SUPABASE_URL` | Same as `SUPABASE_URL` (**required for the UI**) |
| `VITE_SUPABASE_ANON_KEY` | API → **anon public** key (**required for the UI**; not the JWT secret) |

`SUPABASE_URL` / `SUPABASE_JWT_SECRET` are for the **API only**. The chat UI will not start auth until **both** `VITE_*` variables are set in the same `.env` at the repo root.

## 4. Auth providers

- **Email**: enabled by default. For local dev, consider **Authentication → Providers → Email → Confirm email** off so sign-up returns a session immediately.
- **Phone**: enable **Phone** in Supabase and configure an SMS provider (Twilio, etc.) for real OTP.

## 5. Run the app

```bash
make start
```

With **only Supabase** (no local Docker Postgres), ensure `DATABASE_URL` points at Supabase and start API + UI:

```bash
docker compose up --build backend frontend
```

For **local Postgres** in Docker as well:

```bash
docker compose --profile local up --build
```

Set `DATABASE_URL` to local only if you are not using Supabase DB (not recommended once you adopt Supabase).

## 6. Backend API (after Supabase login)

The UI signs in with `@supabase/supabase-js`, then calls:

- `POST /api/v1/auth/profile` — save display name (`Bearer` = Supabase access token)
- `GET /api/v1/auth/me` — profile + consent
- `POST /api/v1/auth/consent` — scheduling consent flag

`POST /api/v1/agent/run` uses the same Bearer token; `patient_id` is the Supabase user UUID (`sub`).
