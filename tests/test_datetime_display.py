from services.datetime_display import format_appointment_time


def test_format_appointment_time_clinic_ist() -> None:
    label = format_appointment_time("2026-09-26T09:00:00+05:30")
    assert label == "2026-09-26 9 AM IST"
