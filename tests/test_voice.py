import pytest
from fastapi.testclient import TestClient

from config import get_settings
from main import app


def test_voice_status_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LIVEKIT_URL", raising=False)
    monkeypatch.delenv("LIVEKIT_API_KEY", raising=False)
    monkeypatch.delenv("LIVEKIT_API_SECRET", raising=False)
    get_settings.cache_clear()

    client = TestClient(app)
    body = client.get("/api/v1/voice/status").json()
    assert body["enabled"] is False
