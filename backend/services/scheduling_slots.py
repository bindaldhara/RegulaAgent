"""Virtual slot catalog (IST). Booked state comes from Postgres."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime

from services.healthcare_store import TZ

SLOT_ID_RE = re.compile(r"^slot-(doc-[a-z]+-\d+)-(\d{12})$")

SEED_DOCTORS: tuple[tuple[str, str, str], ...] = (
    ("doc-cardio-1", "Dr. Ana Rivera", "cardiology"),
    ("doc-cardio-2", "Dr. James Kim", "cardiology"),
    ("doc-dental-1", "Dr. Sofia Mehta", "dentistry"),
)


@dataclass(frozen=True)
class VirtualSlot:
    slot_id: str
    doctor_external_id: str
    doctor_name: str
    specialty: str
    starts_at: datetime


def parse_slot_id(slot_id: str) -> tuple[str, datetime]:
    match = SLOT_ID_RE.match(slot_id)
    if not match:
        raise ValueError(f"Invalid slot id: {slot_id}")
    doctor_external_id = match.group(1)
    raw = match.group(2)
    starts_at = datetime.strptime(raw, "%Y%m%d%H%M").replace(tzinfo=TZ)
    return doctor_external_id, starts_at


def iter_slots_for_date(target_date: date) -> list[VirtualSlot]:
    doctors = {ext: (name, spec) for ext, name, spec in SEED_DOCTORS}
    slots: list[VirtualSlot] = []
    for ext_id, (name, specialty) in doctors.items():
        for hour in (9, 11, 14):
            start = datetime(
                target_date.year,
                target_date.month,
                target_date.day,
                hour,
                0,
                tzinfo=TZ,
            )
            slot_id = f"slot-{ext_id}-{start.strftime('%Y%m%d%H%M')}"
            slots.append(
                VirtualSlot(
                    slot_id=slot_id,
                    doctor_external_id=ext_id,
                    doctor_name=name,
                    specialty=specialty,
                    starts_at=start,
                )
            )
    slots.sort(key=lambda s: s.starts_at)
    return slots
