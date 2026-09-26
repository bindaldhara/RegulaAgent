from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from schemas.enums import RiskLevel
from tools import handlers
from tools.schemas import (
    BookAppointmentRequest,
    CancelAppointmentRequest,
    GetAvailableSlotsRequest,
    GetPatientAppointmentsRequest,
    SearchDoctorsRequest,
)


@dataclass(frozen=True)
class ToolSpec:
    name: str
    risk_level: RiskLevel
    request_model: type[BaseModel]
    handler: Callable[[BaseModel], Any]
    requires_patient: bool = False


REGISTRY: dict[str, ToolSpec] = {
    "search_doctors": ToolSpec(
        name="search_doctors",
        risk_level=RiskLevel.LOW,
        request_model=SearchDoctorsRequest,
        handler=lambda req: handlers.search_doctors(req),
    ),
    "get_available_slots": ToolSpec(
        name="get_available_slots",
        risk_level=RiskLevel.LOW,
        request_model=GetAvailableSlotsRequest,
        handler=lambda req: handlers.get_available_slots(req),
    ),
    "book_appointment": ToolSpec(
        name="book_appointment",
        risk_level=RiskLevel.MEDIUM,
        request_model=BookAppointmentRequest,
        handler=lambda req: handlers.book_appointment(req),
        requires_patient=True,
    ),
    "cancel_appointment": ToolSpec(
        name="cancel_appointment",
        risk_level=RiskLevel.MEDIUM,
        request_model=CancelAppointmentRequest,
        handler=lambda req: handlers.cancel_appointment(req),
        requires_patient=True,
    ),
    "get_patient_appointments": ToolSpec(
        name="get_patient_appointments",
        risk_level=RiskLevel.HIGH,
        request_model=GetPatientAppointmentsRequest,
        handler=lambda req: handlers.get_patient_appointments(req),
        requires_patient=True,
    ),
}


def get_tool(name: str) -> ToolSpec | None:
    return REGISTRY.get(name)
