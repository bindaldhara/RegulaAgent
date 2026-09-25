# Patient login (demo)

Production-shaped sign-in for the chat UI. Identity for the agent comes from the **session token**, not from sidebar flags or raw patient IDs.

## Methods

Enter **your name** in the form; that name is stored in the session and shown in the UI (with email or phone).

| Method | Demo credentials |
|--------|------------------|
| Email + password | `jane@example.com` / `demo1234` or `alex@example.com` / `demo1234` |
| Phone OTP | `+1555010001` (Jane) or `+1555020002` (Alex) — code **`123456`** (shown in UI; no real SMS) |

## API

- `POST /api/v1/auth/login` — email login → JWT
- `POST /api/v1/auth/otp/request` — mock send code
- `POST /api/v1/auth/otp/verify` — phone login → JWT
- `GET /api/v1/auth/me` — current patient (Bearer token)
- `POST /api/v1/auth/consent` — `{ "granted": true }` updates token + scheduling consent

`POST /api/v1/agent/run` with `Authorization: Bearer <token>` sets `identity_verified` and `patient_id` server-side. Consent follows the token after `/auth/consent`.

## Config

`AUTH_SECRET` and `AUTH_TOKEN_TTL_SECONDS` in `.env` (see `.env.example`).
