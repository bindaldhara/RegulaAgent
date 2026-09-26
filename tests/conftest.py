"""Shared test configuration (load before app imports in test modules)."""

import os

import pytest

os.environ.setdefault(
    "SUPABASE_JWT_SECRET",
    "pytest-supabase-jwt-secret-at-least-32-characters",
)
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")


@pytest.fixture(scope="session")
def db_schema_ready() -> None:
    try:
        from db.connection import init_db

        init_db()
    except Exception as exc:
        pytest.skip(f"Postgres not available: {exc}")
