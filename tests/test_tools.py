from db.healthcare import reset_healthcare_bookings
from tools.router import execute_tool
from tools.schemas import BookAppointmentRequest
from tools.handlers import book_appointment


def test_idempotent_booking(db_schema_ready: None) -> None:
    reset_healthcare_bookings()
    req = BookAppointmentRequest(
        patient_id="patient-1",
        specialty="cardiology",
        date="tomorrow",
        idempotency_key="idem-test-001",
    )
    first = book_appointment(req)
    second = book_appointment(req)
    assert first.appointment_id == "appt1"
    assert first.appointment_id == second.appointment_id
    assert second.idempotent_replay is True


def test_search_doctors(db_schema_ready: None) -> None:
    reset_healthcare_bookings()
    result = execute_tool("search_doctors", {"specialty": "cardiology"})
    assert result["status"] == "success"
    assert len(result["data"]["doctors"]) >= 1
