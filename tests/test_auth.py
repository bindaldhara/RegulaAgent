from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_login_and_agent_identity() -> None:
    bad = client.post(
        "/api/v1/auth/login",
        json={"email": "jane@example.com", "password": "wrong", "full_name": "Jane Patient"},
    )
    assert bad.status_code == 401

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "jane@example.com", "password": "demo1234", "full_name": "Jane Patient"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    run = client.post(
        "/api/v1/agent/run",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "Book a cardiologist tomorrow."},
    )
    assert run.status_code == 200
    body = run.json()
    assert body["identity_status"] == "verified"
    assert body["policy"]["outcome"] == "DENY"  # consent not granted yet

    consent = client.post(
        "/api/v1/auth/consent",
        headers={"Authorization": f"Bearer {token}"},
        json={"granted": True},
    )
    assert consent.status_code == 200
    token2 = consent.json()["access_token"]

    run2 = client.post(
        "/api/v1/agent/run",
        headers={"Authorization": f"Bearer {token2}"},
        json={"message": "Book a cardiologist tomorrow."},
    )
    assert run2.json()["policy"]["outcome"] == "ALLOW"


def test_otp_login() -> None:
    req = client.post("/api/v1/auth/otp/request", json={"phone": "+1555010001"})
    assert req.status_code == 200
    verify = client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": "+1555010001", "code": "123456", "full_name": "Alex Patient"},
    )
    assert verify.status_code == 200
    body = verify.json()
    assert body["patient"]["full_name"] == "Alex Patient"
    assert body["patient"]["auth_via"] == "phone"
    assert body["patient"]["phone"] == "+1555010001"

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.json()["auth_via"] == "phone"
