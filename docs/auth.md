# Patient login (Supabase)

Identity for the agent comes from the **Supabase session** (JWT), not from chat input or sidebar flags.

## Flow

1. User signs up or signs in in the UI (Supabase Auth).
2. Frontend stores the Supabase **access token** and calls `POST /api/v1/auth/profile` with their display name.
3. User enables **scheduling consent** → `POST /api/v1/auth/consent`.
4. `POST /api/v1/agent/run` with `Authorization: Bearer <supabase_access_token>` sets `identity_verified` and `patient_id` (Supabase `sub`) server-side.

## API

- `POST /api/v1/auth/profile` — `{ "full_name": "..." }`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/consent` — `{ "granted": true }`

## Config

See [supabase.md](supabase.md) for `SUPABASE_URL`, `SUPABASE_JWT_SECRET`, and frontend `VITE_*` keys.

Consent and display name are stored in Postgres table `patient_profiles` (keyed by Supabase user id).
