from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from agent.intent_classifier import classify_intent, intent_classifier_backend
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


def test_available_dentists() -> None:
    result = classify_intent("get the drs available for dentist")
    assert result.intent == Intent.SEARCH_DOCTOR
    assert result.entities.specialty == "dentistry"


def test_list_available_slots() -> None:
    result = classify_intent("get available slots for Dr. Ana Rivera")
    assert result.intent == Intent.LIST_AVAILABLE_SLOTS
    assert result.entities.doctor_name == "Dr. Ana Rivera"


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


def test_slots_for_sophia_mehta_lists_slots_not_all_doctors() -> None:
    from agent.nodes import intent_node

    msg = "What slots available for Dr. Sophia Mehta?"
    result = classify_intent(msg)
    assert result.intent == Intent.LIST_AVAILABLE_SLOTS
    state = intent_node({"user_message": msg, "chat_history": []})
    assert state["intent"].intent == Intent.LIST_AVAILABLE_SLOTS
    assert state["intent"].entities.doctor_name == "Dr. Sofia Mehta"


def test_date_follow_up_after_slot_question() -> None:
    from datetime import datetime

    from agent.nodes import intent_node
    from services.healthcare_store import TZ

    history = [
        {"role": "user", "content": "What slots available for Dr. Sophia Mehta?"},
        {"role": "assistant", "content": "I'll check open appointment times."},
    ]
    state = intent_node({"user_message": "28th September", "chat_history": history})
    year = datetime.now(TZ).year
    assert state["intent"].intent == Intent.LIST_AVAILABLE_SLOTS
    assert state["intent"].entities.doctor_name == "Dr. Sofia Mehta"
    assert state["intent"].entities.date == f"{year}-09-28"


def test_slots_for_sophia_mehta_extracts_doctor() -> None:
    msg = "what are the available slots for Dr. Sophia Mehta for tomorrow"
    result = classify_intent(msg)
    assert result.intent == Intent.LIST_AVAILABLE_SLOTS
    assert result.entities.doctor_name == "Dr. Sofia Mehta"
    assert result.entities.date == "tomorrow"


def test_auto_prefers_jev_when_typesafe_key_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_PROVIDER", "auto")
    monkeypatch.setenv("TYPESAFE_API_KEY", "ts-test-key")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    get_settings.cache_clear()
    assert intent_classifier_backend() == "jev"


def test_auto_uses_jev_via_openrouter_when_only_or_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_PROVIDER", "auto")
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    get_settings.cache_clear()
    assert intent_classifier_backend() == "jev"


def test_auto_openrouter_llm_when_jev_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_PROVIDER", "auto")
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    get_settings.cache_clear()
    with patch("agent.intent_classifier.jev_available", return_value=False):
        assert intent_classifier_backend() == "openrouter"


def test_jev_maps_choice_to_intent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_PROVIDER", "jev")
    monkeypatch.setenv("TYPESAFE_API_KEY", "ts-test-key")
    get_settings.cache_clear()

    choice_answer = SimpleNamespace(
        choice="list_available_slots",
        confidence=0.91,
        probabilities={"list_available_slots": 0.91},
    )
    mock_response = SimpleNamespace(
        choices={"intent": choice_answer},
        nouls={
            "medical_emergency": SimpleNamespace(noul=0.0),
            "unauthorized_records": SimpleNamespace(noul=0.0),
        },
    )
    mock_client = MagicMock()
    mock_client.system_one.return_value = mock_response
    mock_client.__enter__.return_value = mock_client

    with patch("services.intent_jev.TypeSafeClient", return_value=mock_client) as client_cls:
        result = classify_intent("What times are open for Dr. Ana Rivera tomorrow?")

    client_cls.assert_called_once()
    assert client_cls.call_args.kwargs["base_url"] == "https://api.typesafe.ai"
    assert result.intent == Intent.LIST_AVAILABLE_SLOTS
    assert result.confidence >= 0.9
    assert result.entities.doctor_name == "Dr. Ana Rivera"


def test_jev_via_openrouter_client_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_PROVIDER", "jev")
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setenv("OPENROUTER_JEV_MODEL", "~typesafe/jev-latest")
    get_settings.cache_clear()

    choice_answer = SimpleNamespace(choice="book_appointment", confidence=0.88, probabilities={})
    mock_response = SimpleNamespace(
        choices={"intent": choice_answer},
        nouls={
            "medical_emergency": SimpleNamespace(noul=0.0),
            "unauthorized_records": SimpleNamespace(noul=0.0),
        },
    )
    mock_client = MagicMock()
    mock_client.system_one.return_value = mock_response
    mock_client.__enter__.return_value = mock_client

    with patch("services.intent_jev.TypeSafeClient", return_value=mock_client) as client_cls:
        result = classify_intent("Book a cardiologist tomorrow.")

    kwargs = client_cls.call_args.kwargs
    assert kwargs["base_url"] == "https://openrouter.ai/api"
    assert kwargs["model"] == "~typesafe/jev-latest"
    assert result.intent == Intent.BOOK_APPOINTMENT


def test_cancel_does_not_extract_of_as_appointment_id() -> None:
    msg = "Cancel the appointment of tomorrow for Dr. James Kim."
    result = classify_intent(msg)
    assert result.intent == Intent.CANCEL_APPOINTMENT
    assert result.entities.appointment_id is None
    assert result.entities.doctor_name == "Dr. James Kim"
    assert result.entities.date == "tomorrow"
