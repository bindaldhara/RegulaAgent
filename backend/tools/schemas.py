from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SearchDoctorsRequest(BaseModel):
    specialty: str | None = None


class DoctorInfo(BaseModel):
    doctor_id: str
    full_name: str
    specialty: str


class SearchDoctorsResponse(BaseModel):
    doctors: list[DoctorInfo]


class GetAvailableSlotsRequest(BaseModel):
    specialty: str | None = None
    doctor_id: str | None = None
    date: str | None = None


class SlotInfo(BaseModel):
    slot_id: str
    doctor_id: str
    doctor_name: str
    specialty: str
    starts_at: datetime


class GetAvailableSlotsResponse(BaseModel):
    slots: list[SlotInfo]


class BookAppointmentRequest(BaseModel):
    patient_id: str
    specialty: str | None = None
    doctor_id: str | None = None
    slot_id: str | None = None
    date: str | None = None
    preferred_hour: int | None = Field(default=None, ge=0, le=23)
    idempotency_key: str = Field(min_length=8)


class BookAppointmentResponse(BaseModel):
    appointment_id: str
    doctor_name: str
    starts_at: datetime
    status: str = "booked"
    idempotent_replay: bool = False


class CancelAppointmentRequest(BaseModel):
    patient_id: str
    appointment_id: str | None = None
    doctor_name: str | None = None
    date: str | None = None


class CancelAppointmentResponse(BaseModel):
    appointment_id: str
    status: str = "cancelled"


class GetPatientAppointmentsRequest(BaseModel):
    patient_id: str


class AppointmentInfo(BaseModel):
    appointment_id: str
    doctor_name: str
    specialty: str
    starts_at: datetime
    status: str


class GetPatientAppointmentsResponse(BaseModel):
    appointments: list[AppointmentInfo]
