# Database

## Stack

- **PostgreSQL 16** (Docker service `db`)
- **psycopg 3** — connections and **parameterized raw SQL** (no SQLAlchemy)

## Schema

DDL lives in `backend/db/schema.sql`. Apply it with:

```bash
make migrate
```

Or on backend startup you can run the same `init_db()` from `backend/db/connection.py`.

## Code layout

| Module | Role |
|--------|------|
| `db/connection.py` | `get_connection()`, `init_db()` |
| `db/schema.sql` | Table definitions |
| `db/persistence.py` | Agent run / message / audit inserts |

Connection settings: `POSTGRES_*` in `.env` (see `.env.example`).

## Tests

DB integration tests are skipped unless Postgres is available. From the repo root with `make start`:

```bash
SKIP_DB_TESTS=0 pytest tests/test_db_schema.py -q
```
