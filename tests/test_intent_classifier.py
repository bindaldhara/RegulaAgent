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


def test_cancel_does_not_extract_of_as_appointment_id() -> None:
    msg = "Cancel the appointment of tomorrow for Dr. James Kim."
    result = classify_intent(msg)
    assert result.intent == Intent.CANCEL_APPOINTMENT
    assert result.entities.appointment_id is None
    assert result.entities.doctor_name == "Dr. James Kim"
    assert result.entities.date == "tomorrow"
