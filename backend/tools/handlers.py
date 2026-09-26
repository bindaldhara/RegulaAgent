from __future__ import annotations

from db import healthcare as healthcare_db
from tools.schemas import (
    AppointmentInfo,
    BookAppointmentRequest,
    BookAppointmentResponse,
    CancelAppointmentRequest,
    CancelAppointmentResponse,
    DoctorInfo,
    GetAvailableSlotsRequest,
    GetAvailableSlotsResponse,
    GetPatientAppointmentsRequest,
    GetPatientAppointmentsResponse,
    SearchDoctorsRequest,
    SearchDoctorsResponse,
    SlotInfo,
)


def search_doctors(req: SearchDoctorsRequest) -> SearchDoctorsResponse:
    rows = healthcare_db.list_doctors(req.specialty)
    return SearchDoctorsResponse(
        doctors=[
            DoctorInfo(doctor_id=r["external_id"], full_name=r["full_name"], specialty=r["specialty"])
            for r in rows
        ]
    )


def get_available_slots(req: GetAvailableSlotsRequest) -> GetAvailableSlotsResponse:
    slots = healthcare_db.list_available_slots(req.specialty, req.doctor_id, req.date)
    return GetAvailableSlotsResponse(
        slots=[
            SlotInfo(
                slot_id=s.slot_id,
                doctor_id=s.doctor_external_id,
                doctor_name=s.doctor_name,
                specialty=s.specialty,
                starts_at=s.starts_at,
            )
            for s in slots
        ]
    )


def book_appointment(req: BookAppointmentRequest) -> BookAppointmentResponse:
    data = healthcare_db.book_appointment(
        patient_external_id=req.patient_id,
        specialty=req.specialty,
        doctor_external_id=req.doctor_id,
        slot_id=req.slot_id,
        date_phrase=req.date,
        preferred_hour=req.preferred_hour,
        idempotency_key=req.idempotency_key,
    )
    return BookAppointmentResponse(
        appointment_id=data["appointment_id"],
        doctor_name=data["doctor_name"],
        starts_at=data["starts_at"],
        status=data.get("status", "booked"),
        idempotent_replay=bool(data.get("idempotent_replay")),
    )


def cancel_appointment(req: CancelAppointmentRequest) -> CancelAppointmentResponse:
    data = healthcare_db.cancel_appointment(
        patient_external_id=req.patient_id,
        appointment_ref=req.appointment_id,
    )
    return CancelAppointmentResponse(appointment_id=data["appointment_id"], status=data["status"])


def get_patient_appointments(req: GetPatientAppointmentsRequest) -> GetPatientAppointmentsResponse:
    rows = healthcare_db.list_patient_appointments(req.patient_id)
    return GetPatientAppointmentsResponse(
        appointments=[
            AppointmentInfo(
                appointment_id=r["appointment_id"],
                doctor_name=r["doctor_name"],
                specialty=r["specialty"],
                starts_at=r["starts_at"],
                status=r["status"],
            )
            for r in rows
        ]
    )
