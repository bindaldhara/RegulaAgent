from services.doctor_matching import extract_preferred_hour, resolve_doctor_from_message


def test_resolve_ana_rivera() -> None:
    assert resolve_doctor_from_message("book Dr. Ana Rivera at 9 AM tomorrow") == "doc-cardio-1"


def test_extract_9_am() -> None:
    assert extract_preferred_hour("9 AM IST tomorrow") == 9
