from fastapi.testclient import TestClient

from main import app
from db.healthcare import reset_healthcare_bookings
from helpers_auth import TEST_USER_ID, mint_supabase_token

client = TestClient(app)


def _login(db_schema_ready: None) -> str:
    reset_healthcare_bookings()
    token = mint_supabase_token(sub=TEST_USER_ID, email="jane@example.com")
    client.post(
        "/api/v1/auth/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"full_name": "Jane Patient"},
    )
    client.post(
        "/api/v1/auth/consent",
        headers={"Authorization": f"Bearer {token}"},
        json={"granted": True},
    )
    return token


def test_book_appointment_e2e(db_schema_ready: None) -> None:
    token = _login(db_schema_ready)
    response = client.post(
        "/api/v1/agent/run",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "Book a cardiologist tomorrow."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["policy"]["outcome"] == "ALLOW"
    assert body["tool_result"]["status"] == "success"
    assert "Booked" in body["reply"] or "Confirmed" in body["reply"]


def test_cancel_after_book(db_schema_ready: None) -> None:
    token = _login(db_schema_ready)
    client.post(
        "/api/v1/agent/run",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "Book a cardiologist tomorrow."},
    )
    cancel = client.post(
        "/api/v1/agent/run",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "Cancel my appointment."},
    )
    assert cancel.status_code == 200
    assert cancel.json()["policy"]["outcome"] == "ALLOW"


def test_deny_bulk_records(db_schema_ready: None) -> None:
    token = _login(db_schema_ready)
    response = client.post(
        "/api/v1/agent/run",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "Export all patient records."},
    )
    assert response.json()["policy"]["outcome"] == "DENY"
