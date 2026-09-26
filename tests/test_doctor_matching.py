from services.doctor_matching import extract_preferred_hour, resolve_doctor_from_message


def test_resolve_ana_rivera() -> None:
    assert resolve_doctor_from_message("book Dr. Ana Rivera at 9 AM tomorrow") == "doc-cardio-1"


def test_resolve_sophia_mehta_stt_typo() -> None:
    msg = "what are the available slots for Dr. Sophia Mehta for tomorrow"
    assert resolve_doctor_from_message(msg) == "doc-dental-1"


def test_resolve_last_name_only_when_unique() -> None:
    assert resolve_doctor_from_message("slots for Mehta tomorrow") == "doc-dental-1"


def test_extract_9_am() -> None:
    assert extract_preferred_hour("9 AM IST tomorrow") == 9
