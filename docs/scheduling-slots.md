# How available slots work

## Tables

| Table | Role |
|-------|------|
| `doctors` | Catalog of clinicians (`external_id` e.g. `doc-cardio-1`) |
| `schedule_slots` | **Persisted** bookable times (IST): `external_id`, `doctor_id`, `starts_at` |
| `appointments` | Confirmed bookings (`status = 'booked'`) |

## Seeding

On `make migrate` / `init_db()`:

1. `seed_healthcare_catalog()` — upserts doctors.
2. `seed_schedule_slots()` — for **today + 1/2/3 days**, inserts rows for each doctor at **9:00, 11:00, 14:00 IST** (same rules as `scheduling_slots.py`). Existing `external_id` rows are skipped.

## Availability query

`list_available_slots()` (used by tool `get_available_slots` and booking):

```sql
SELECT schedule_slots … JOIN doctors …
WHERE starts_at on requested day
  AND (optional specialty / doctor filters)
  AND NOT EXISTS (
    booked appointment for same doctor_id + starts_at
  )
ORDER BY starts_at
```

So a slot is **available** iff it exists in `schedule_slots` and no active booking occupies that doctor and time.

## Chat context

Slot and booking requests merge missing **date**, **specialty**, and **doctor** from recent **user** turns only (`entity_context.py`). Assistant messages (e.g. “Dr. Sofia Mehta — 11 AM”) are ignored so a new specialty like “cardiologist” is not pinned to the previous dentist.

## Booking

`book_appointment` inserts into `appointments`; the slot row stays in `schedule_slots` and is excluded by the `NOT EXISTS` check above.

## Changing the template

Edit hours/doctors in `backend/services/scheduling_slots.py` (`SEED_DOCTORS`, `(9, 11, 14)`), then run `make migrate` to add new catalog rows. To extend the rolling window, adjust `days_ahead` in `seed_schedule_slots()`.
