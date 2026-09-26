import pytest
from fastapi.testclient import TestClient

from config import get_settings
from main import app


@pytest.fixture(autouse=True)
def mock_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_PROVIDER", "mock")
    get_settings.cache_clear()


def test_health() -> None:
    client = TestClient(app)
    assert client.get("/health").json() == {"status": "ok"}


def test_agent_run_endpoint() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/agent/run",
        json={"message": "Find a dentist tomorrow."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["reply"]
    assert body["intent"]["intent"] == "SEARCH_DOCTOR"
