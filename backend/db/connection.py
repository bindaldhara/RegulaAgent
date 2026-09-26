"""PostgreSQL access via psycopg (raw SQL). Works with Supabase or local Postgres."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg import Connection

from config import get_settings

_SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def _conninfo() -> str:
    return get_settings().resolved_database_url


@contextmanager
def get_connection() -> Generator[Connection, None, None]:
    conn = psycopg.connect(_conninfo())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    sql = _SCHEMA_PATH.read_text(encoding="utf-8")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
    from db.healthcare import seed_healthcare_catalog, seed_schedule_slots

    seed_healthcare_catalog()
    seed_schedule_slots()
