# Database

## Stack

- **PostgreSQL** — hosted on **Supabase** (recommended) or local Docker (`docker compose --profile local`)
- **psycopg 3** — connections and **parameterized raw SQL** (no ORM)

## Schema

DDL lives in `backend/db/schema.sql`. Apply it in Supabase SQL Editor or:

```bash
make migrate
```

Includes `patient_profiles` (Supabase user id, name, consent), **`doctors`**, **`schedule_slots`** (persisted IST catalog), **`appointments`** (bookings with refs `appt1`, `appt2`, …), plus agent audit tables.

See [scheduling-slots.md](scheduling-slots.md) for how availability is computed.

## Connection

Set **`DATABASE_URL`** to your Supabase connection string (see `.env.example`).

If `DATABASE_URL` is unset, the API falls back to `POSTGRES_*` (local Docker Postgres).

## Code layout

| Module | Role |
|--------|------|
| `db/connection.py` | `get_connection()`, `init_db()` |
| `db/schema.sql` | Table definitions |
| `db/persistence.py` | Agent run / message / audit inserts |
| `services/patient_profiles.py` | Name + consent for Supabase users |

## Tests

DB tests need a reachable Postgres (`DATABASE_URL` or local `POSTGRES_*`):

```bash
SKIP_DB_TESTS=0 pytest tests/test_db_schema.py -q
```

Auth and Day 1 E2E tests also run migrations via the `db_schema_ready` fixture.
