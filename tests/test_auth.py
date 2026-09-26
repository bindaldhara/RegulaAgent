from fastapi.testclient import TestClient

from main import app
from helpers_auth import TEST_USER_ID, mint_supabase_token

client = TestClient(app)


def test_profile_consent_and_agent_identity(db_schema_ready: None) -> None:
    token = mint_supabase_token(email="jane@example.com")

    profile = client.post(
        "/api/v1/auth/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"full_name": "Jane Patient"},
    )
    assert profile.status_code == 200
    assert profile.json()["full_name"] == "Jane Patient"

    run = client.post(
        "/api/v1/agent/run",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "Book a cardiologist tomorrow."},
    )
    assert run.status_code == 200
    body = run.json()
    assert body["identity_status"] == "verified"
    assert body["policy"]["outcome"] == "DENY"

    consent = client.post(
        "/api/v1/auth/consent",
        headers={"Authorization": f"Bearer {token}"},
        json={"granted": True},
    )
    assert consent.status_code == 200
    assert consent.json()["consent_granted"] is True

    run2 = client.post(
        "/api/v1/agent/run",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "Book a cardiologist tomorrow."},
    )
    assert run2.json()["policy"]["outcome"] == "ALLOW"


def test_me_phone_auth_via(db_schema_ready: None) -> None:
    token = mint_supabase_token(sub=TEST_USER_ID, email="jane@example.com", phone="+1555010001")

    client.post(
        "/api/v1/auth/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"full_name": "Alex Patient"},
    )
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    body = me.json()
    assert body["auth_via"] == "phone"
    assert body["phone"] == "+1555010001"
