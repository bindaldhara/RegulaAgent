import os

import pytest

from db.connection import get_connection, init_db


@pytest.mark.skipif(
    os.environ.get("SKIP_DB_TESTS") == "1",
    reason="Set SKIP_DB_TESTS=0 and run Postgres to enable",
)
def test_schema_init_and_roundtrip() -> None:
    init_db()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO patients (external_id, full_name, email)
                VALUES ('test-patient-1', 'Test User', 'test@example.com')
                ON CONFLICT (external_id) DO NOTHING
                """
            )
            cur.execute("SELECT COUNT(*) FROM patients WHERE external_id = %s", ("test-patient-1",))
            count = cur.fetchone()[0]
    assert count == 1
