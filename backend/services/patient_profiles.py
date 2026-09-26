"""Patient display name and scheduling consent (Supabase user id)."""

from __future__ import annotations

from dataclasses import dataclass

from db.connection import get_connection


@dataclass
class ProfileRow:
    user_id: str
    full_name: str
    email: str | None
    phone: str | None
    consent_granted: bool


def get_profile(user_id: str) -> ProfileRow | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT user_id, full_name, email, phone, consent_granted
                FROM patient_profiles
                WHERE user_id = %s::uuid
                """,
                (user_id,),
            )
            row = cur.fetchone()
    if row is None:
        return None
    return ProfileRow(
        user_id=str(row[0]),
        full_name=row[1],
        email=row[2],
        phone=row[3],
        consent_granted=bool(row[4]),
    )


def upsert_profile(
    user_id: str,
    *,
    full_name: str,
    email: str | None,
    phone: str | None,
) -> ProfileRow:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO patient_profiles (user_id, full_name, email, phone)
                VALUES (%s::uuid, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    full_name = EXCLUDED.full_name,
                    email = COALESCE(EXCLUDED.email, patient_profiles.email),
                    phone = COALESCE(EXCLUDED.phone, patient_profiles.phone),
                    updated_at = NOW()
                RETURNING user_id, full_name, email, phone, consent_granted
                """,
                (user_id, full_name.strip(), email, phone),
            )
            row = cur.fetchone()
    if row is None:
        raise RuntimeError("profile upsert failed")
    return ProfileRow(
        user_id=str(row[0]),
        full_name=row[1],
        email=row[2],
        phone=row[3],
        consent_granted=bool(row[4]),
    )


def set_consent(user_id: str, granted: bool) -> ProfileRow:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE patient_profiles
                SET consent_granted = %s, updated_at = NOW()
                WHERE user_id = %s::uuid
                RETURNING user_id, full_name, email, phone, consent_granted
                """,
                (granted, user_id),
            )
            row = cur.fetchone()
            if row is None:
                cur.execute(
                    """
                    INSERT INTO patient_profiles (user_id, full_name, consent_granted)
                    VALUES (%s::uuid, '', %s)
                    RETURNING user_id, full_name, email, phone, consent_granted
                    """,
                    (user_id, granted),
                )
                row = cur.fetchone()
    if row is None:
        raise RuntimeError("consent update failed")
    return ProfileRow(
        user_id=str(row[0]),
        full_name=row[1],
        email=row[2],
        phone=row[3],
        consent_granted=bool(row[4]),
    )
