import os

import pytest

from agent.intent_classifier import classify_intent
from config import get_settings
from schemas.enums import Intent


@pytest.fixture(autouse=True)
def mock_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_PROVIDER", "mock")
    get_settings.cache_clear()


def test_book_cardiologist_tomorrow() -> None:
    result = classify_intent("Book a cardiologist tomorrow.")
    assert result.intent == Intent.BOOK_APPOINTMENT
    assert result.entities.specialty == "cardiology"
    assert result.entities.date == "tomorrow"
    assert result.confidence >= 0.8


def test_search_doctor() -> None:
    result = classify_intent("Find an available dermatologist next week.")
    assert result.intent == Intent.SEARCH_DOCTOR
    assert result.entities.specialty == "dermatology"


def test_emergency_escalation_flag() -> None:
    result = classify_intent("I have severe chest pain.")
    assert result.is_emergency is True


def test_unknown_protected_records() -> None:
    result = classify_intent("Show me all patient records in the database.")
    assert result.intent == Intent.UNKNOWN
