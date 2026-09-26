"""Doctors + appointments persisted in PostgreSQL."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Any

from db.connection import get_connection
from services.healthcare_store import local_clinic_hour, normalize_specialty, resolve_date_phrase
from services.datetime_display import format_appointment_time
from services.healthcare_store import TZ
from services.doctor_matching import resolve_doctor_external_id
from services.scheduling_slots import SEED_DOCTORS, VirtualSlot, iter_slots_for_date, parse_slot_id


def _format_slot_conflict(requested: VirtualSlot, alternatives: list[VirtualSlot]) -> str:
    when = format_appointment_time(requested.starts_at)
    intro = f"The {when} slot with {requested.doctor_name} is already booked.\n\n"
    if not alternatives:
        return intro + "No other open slots for this doctor on that day. Try another date."
    blocks = [
        f"{i}. {format_appointment_time(s.starts_at)}" for i, s in enumerate(alternatives, 1)
    ]
    return intro + "Available times with this doctor:\n\n" + "\n\n".join(blocks)


def seed_healthcare_catalog() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            for external_id, full_name, specialty in SEED_DOCTORS:
                cur.execute(
                    "SELECT id FROM doctors WHERE external_id = %s",
                    (external_id,),
                )
                if cur.fetchone():
                    cur.execute(
                        """
                        UPDATE doctors
                        SET full_name = %s, specialty = %s
                        WHERE external_id = %s
                        """,
                        (full_name, specialty, external_id),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO doctors (external_id, full_name, specialty)
                        VALUES (%s, %s, %s)
                        """,
                        (external_id, full_name, specialty),
                    )


def seed_schedule_slots(days_ahead: tuple[int, ...] = (1, 2, 3)) -> None:
    """Insert catalog rows for the next few IST days (idempotent)."""
    seed_healthcare_catalog()
    doctor_map = {row["external_id"]: row["id"] for row in _doctor_rows()}
    today = datetime.now(TZ).date()
    with get_connection() as conn:
        with conn.cursor() as cur:
            for offset in days_ahead:
                target = today + timedelta(days=offset)
                for virtual in iter_slots_for_date(target):
                    doctor_uuid = doctor_map.get(virtual.doctor_external_id)
                    if doctor_uuid is None:
                        continue
                    cur.execute(
                        "SELECT 1 FROM schedule_slots WHERE external_id = %s",
                        (virtual.slot_id,),
                    )
                    if cur.fetchone():
                        continue
                    cur.execute(
                        """
                        INSERT INTO schedule_slots (external_id, doctor_id, starts_at)
                        VALUES (%s, %s, %s)
                        """,
                        (virtual.slot_id, doctor_uuid, virtual.starts_at),
                    )


def _day_bounds(target_date: date) -> tuple[datetime, datetime]:
    start = datetime(target_date.year, target_date.month, target_date.day, 0, 0, tzinfo=TZ)
    end = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, tzinfo=TZ)
    return start, end


def _slot_from_row(row: tuple[Any, ...]) -> VirtualSlot:
    return VirtualSlot(
        slot_id=row[0],
        doctor_external_id=row[1],
        doctor_name=row[2],
        specialty=row[3],
        starts_at=row[4],
    )


def _slot_by_external_id(slot_external_id: str) -> VirtualSlot | None:
    seed_schedule_slots()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ss.external_id, d.external_id, d.full_name, d.specialty, ss.starts_at
                FROM schedule_slots ss
                JOIN doctors d ON d.id = ss.doctor_id
                WHERE ss.external_id = %s
                """,
                (slot_external_id,),
            )
            row = cur.fetchone()
    return _slot_from_row(row) if row else None


def reset_healthcare_bookings() -> None:
    """Clear appointments for tests (doctors remain)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM appointments")
            cur.execute("ALTER SEQUENCE appointment_external_ref_seq RESTART WITH 1")


def _ensure_patient(external_id: str) -> uuid.UUID:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM patients WHERE external_id = %s",
                (external_id,),
            )
            row = cur.fetchone()
            if row is not None:
                return row[0]
            cur.execute(
                """
                INSERT INTO patients (external_id, full_name)
                VALUES (%s, %s)
                RETURNING id
                """,
                (external_id, "Patient"),
            )
            row = cur.fetchone()
    if row is None:
        raise RuntimeError("patient insert failed")
    return row[0]


def _doctor_rows(specialty: str | None = None, doctor_external_id: str | None = None) -> list[dict[str, Any]]:
    seed_healthcare_catalog()
    clauses = ["external_id IS NOT NULL"]
    params: list[Any] = []
    if specialty:
        clauses.append("specialty = %s")
        params.append(specialty)
    if doctor_external_id:
        clauses.append("external_id = %s")
        params.append(doctor_external_id)
    where = " AND ".join(clauses)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, external_id, full_name, specialty
                FROM doctors
                WHERE {where}
                ORDER BY full_name
                """,
                params,
            )
            rows = cur.fetchall()
    return [
        {
            "id": r[0],
            "external_id": r[1],
            "full_name": r[2],
            "specialty": r[3],
        }
        for r in rows
    ]


def _booked_times_for_date(target_date: date) -> set[tuple[uuid.UUID, datetime]]:
    day_start = datetime(target_date.year, target_date.month, target_date.day, 0, 0, tzinfo=TZ)
    day_end = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, tzinfo=TZ)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT doctor_id, scheduled_at
                FROM appointments
                WHERE status = 'booked'
                  AND scheduled_at >= %s
                  AND scheduled_at <= %s
                """,
                (day_start, day_end),
            )
            rows = cur.fetchall()
    return {(r[0], r[1]) for r in rows}


def list_doctors(specialty: str | None) -> list[dict[str, Any]]:
    spec = normalize_specialty(specialty)
    return _doctor_rows(specialty=spec)


def list_available_slots(
    specialty: str | None,
    doctor_external_id: str | None,
    date_phrase: str | None,
) -> list[VirtualSlot]:
    seed_schedule_slots()
    target_date = resolve_date_phrase(date_phrase)
    day_start, day_end = _day_bounds(target_date)
    spec = normalize_specialty(specialty)
    clauses = [
        "ss.starts_at >= %s",
        "ss.starts_at <= %s",
        """
        NOT EXISTS (
            SELECT 1 FROM appointments a
            WHERE a.doctor_id = ss.doctor_id
              AND a.scheduled_at = ss.starts_at
              AND a.status = 'booked'
        )
        """,
    ]
    params: list[Any] = [day_start, day_end]
    if spec:
        clauses.append("d.specialty = %s")
        params.append(spec)
    if doctor_external_id:
        clauses.append("d.external_id = %s")
        params.append(doctor_external_id)
    where = " AND ".join(clauses)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT ss.external_id, d.external_id, d.full_name, d.specialty, ss.starts_at
                FROM schedule_slots ss
                JOIN doctors d ON d.id = ss.doctor_id
                WHERE {where}
                ORDER BY ss.starts_at
                """,
                params,
            )
            rows = cur.fetchall()
    return [_slot_from_row(row) for row in rows]


def _next_external_ref(cur: Any) -> str:
    cur.execute("SELECT nextval('appointment_external_ref_seq')")
    seq = cur.fetchone()[0]
    return f"appt{seq}"


def _appointment_by_idempotency(idempotency_key: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT a.external_ref, a.status, a.scheduled_at, d.full_name
                FROM appointments a
                JOIN doctors d ON d.id = a.doctor_id
                WHERE a.idempotency_key = %s
                """,
                (idempotency_key,),
            )
            row = cur.fetchone()
    if row is None:
        return None
    return {
        "appointment_id": row[0],
        "status": row[1],
        "starts_at": row[2],
        "doctor_name": row[3],
    }


def book_appointment(
    *,
    patient_external_id: str,
    specialty: str | None,
    doctor_external_id: str | None,
    slot_id: str | None,
    date_phrase: str | None,
    preferred_hour: int | None = None,
    idempotency_key: str,
) -> dict[str, Any]:
    existing = _appointment_by_idempotency(idempotency_key)
    if existing:
        return {**existing, "idempotent_replay": True}

    patient_uuid = _ensure_patient(patient_external_id)
    target_date = resolve_date_phrase(date_phrase)

    chosen: VirtualSlot | None = None
    if slot_id:
        chosen = _slot_by_external_id(slot_id)
        if chosen is None:
            try:
                ext, starts_at = parse_slot_id(slot_id)
                doctors = _doctor_rows(doctor_external_id=ext)
                if doctors:
                    doc = doctors[0]
                    chosen = VirtualSlot(
                        slot_id=slot_id,
                        doctor_external_id=ext,
                        doctor_name=doc["full_name"],
                        specialty=doc["specialty"],
                        starts_at=starts_at,
                    )
            except ValueError:
                chosen = None

    def _slot_matches_hour(slot: VirtualSlot, hour: int) -> bool:
        return local_clinic_hour(slot.starts_at) == hour

    if chosen is None and doctor_external_id and preferred_hour is not None:
        available = list_available_slots(specialty, doctor_external_id, date_phrase)
        hour_slots = [s for s in available if _slot_matches_hour(s, preferred_hour)]
        if not hour_slots:
            if available:
                labels = ", ".join(
                    format_appointment_time(s.starts_at).split(" ", 1)[1] for s in available
                )
                raise ValueError(
                    f"That time is not offered for this doctor on that date. Open times: {labels}."
                )
            raise ValueError("No open slots for this doctor on that date.")
        chosen = hour_slots[0]

    if chosen is None and doctor_external_id:
        doctor_slots = list_available_slots(specialty, doctor_external_id, date_phrase)
        if preferred_hour is not None:
            doctor_slots = [s for s in doctor_slots if _slot_matches_hour(s, preferred_hour)]
        if not doctor_slots:
            name = next((n for e, n, _ in SEED_DOCTORS if e == doctor_external_id), "this doctor")
            if preferred_hour is not None:
                raise ValueError(f"No open slot at that time for {name} on that date.")
            raise ValueError(f"No open slots for {name} on that date.")
        chosen = doctor_slots[0]

    if chosen is None:
        slots = list_available_slots(specialty, doctor_external_id, date_phrase)
        if preferred_hour is not None:
            slots = [s for s in slots if _slot_matches_hour(s, preferred_hour)]
        if not slots:
            raise ValueError("No available slots for the requested specialty, doctor, and time.")
        chosen = slots[0]

    doctors = _doctor_rows(doctor_external_id=chosen.doctor_external_id)
    if not doctors:
        raise ValueError("Doctor not found.")
    doctor_uuid = doctors[0]["id"]

    booked = _booked_times_for_date(chosen.starts_at.date())
    if (doctor_uuid, chosen.starts_at) in booked:
        alternatives = list_available_slots(None, chosen.doctor_external_id, date_phrase)
        raise ValueError(_format_slot_conflict(chosen, alternatives))

    with get_connection() as conn:
        with conn.cursor() as cur:
            external_ref = _next_external_ref(cur)
            cur.execute(
                """
                INSERT INTO appointments (
                    external_ref, patient_id, doctor_id, scheduled_at, status, idempotency_key
                )
                VALUES (%s, %s, %s, %s, 'booked', %s)
                RETURNING external_ref, scheduled_at
                """,
                (external_ref, patient_uuid, doctor_uuid, chosen.starts_at, idempotency_key),
            )
            row = cur.fetchone()
    if row is None:
        raise RuntimeError("appointment insert failed")

    return {
        "appointment_id": row[0],
        "doctor_name": chosen.doctor_name,
        "starts_at": row[1],
        "status": "booked",
        "idempotent_replay": False,
    }


def _select_booked_appointment_row(
    cur: Any,
    *,
    patient_uuid: uuid.UUID,
    appointment_ref: str | None,
    doctor_external_id: str | None,
    target_date: date | None,
) -> tuple[str, uuid.UUID, str] | None:
    if appointment_ref:
        cur.execute(
            """
            SELECT a.external_ref, a.patient_id, a.status, a.scheduled_at, d.external_id
            FROM appointments a
            JOIN doctors d ON d.id = a.doctor_id
            WHERE a.external_ref = %s
            """,
            (appointment_ref.lower(),),
        )
        rows = [cur.fetchone()]
    else:
        cur.execute(
            """
            SELECT a.external_ref, a.patient_id, a.status, a.scheduled_at, d.external_id
            FROM appointments a
            JOIN doctors d ON d.id = a.doctor_id
            WHERE a.patient_id = %s AND a.status = 'booked'
            ORDER BY a.scheduled_at ASC, a.created_at DESC
            """,
            (patient_uuid,),
        )
        rows = cur.fetchall()

    candidates: list[tuple[str, uuid.UUID, str]] = []
    for row in rows:
        if row is None:
            continue
        ref, owner_id, status, scheduled_at, doc_ext = row
        if status != "booked" or owner_id != patient_uuid:
            continue
        if doctor_external_id and doc_ext != doctor_external_id:
            continue
        if target_date is not None:
            appt_date = scheduled_at.astimezone(TZ).date()
            if appt_date != target_date:
                continue
        candidates.append((ref, owner_id, status))

    if not candidates:
        return None
    if len(candidates) > 1 and not appointment_ref:
        raise ValueError(
            "Multiple booked appointments match. Say the reference (for example appt6) or be more specific."
        )
    return candidates[0]


def cancel_appointment(
    *,
    patient_external_id: str,
    appointment_ref: str | None,
    doctor_name: str | None = None,
    date_phrase: str | None = None,
) -> dict[str, Any]:
    patient_uuid = _ensure_patient(patient_external_id)
    doctor_external_id = resolve_doctor_external_id(doctor_name) if doctor_name else None
    target_date = resolve_date_phrase(date_phrase) if date_phrase else None

    with get_connection() as conn:
        with conn.cursor() as cur:
            if not appointment_ref and not doctor_external_id and target_date is None:
                cur.execute(
                    """
                    SELECT external_ref, patient_id, status
                    FROM appointments
                    WHERE patient_id = %s AND status = 'booked'
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (patient_uuid,),
                )
                legacy = cur.fetchone()
                row = legacy[:3] if legacy else None
            else:
                row = _select_booked_appointment_row(
                    cur,
                    patient_uuid=patient_uuid,
                    appointment_ref=appointment_ref,
                    doctor_external_id=doctor_external_id,
                    target_date=target_date,
                )
            if row is None:
                raise ValueError("Appointment not found.")
            ref, owner_id, status = row
            if owner_id != patient_uuid:
                raise ValueError("You may only cancel your own appointments.")
            if status != "booked":
                raise ValueError("Appointment not found.")
            cur.execute(
                """
                UPDATE appointments SET status = 'cancelled'
                WHERE external_ref = %s
                RETURNING external_ref
                """,
                (ref,),
            )
    return {"appointment_id": ref, "status": "cancelled"}


def list_patient_appointments(patient_external_id: str) -> list[dict[str, Any]]:
    patient_uuid = _ensure_patient(patient_external_id)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT a.external_ref, d.full_name, d.specialty, a.scheduled_at, a.status
                FROM appointments a
                JOIN doctors d ON d.id = a.doctor_id
                WHERE a.patient_id = %s
                ORDER BY a.scheduled_at
                """,
                (patient_uuid,),
            )
            rows = cur.fetchall()
    return [
        {
            "appointment_id": r[0],
            "doctor_name": r[1],
            "specialty": r[2],
            "starts_at": r[3],
            "status": r[4],
        }
        for r in rows
    ]
