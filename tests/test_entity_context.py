from schemas.intent import ExtractedEntities
from services.entity_context import enrich_booking_entities


def test_cardiologist_slots_not_pinned_to_prior_dentist_reply() -> None:
    from agent.intent_classifier import classify_intent

    message = "available slots for a cardiologist tomorrow"
    classification = classify_intent(message)
    history = [
        {"role": "user", "content": "get the drs available for dentist"},
        {
            "role": "assistant",
            "content": "Here are available doctors:\n• Dr. Sofia Mehta (dentistry)",
        },
        {"role": "user", "content": "available slots for a dentist tomorrow"},
        {
            "role": "assistant",
            "content": (
                "Available slots:\n\n1. Dr. Sofia Mehta — 2026-09-26 11 AM IST\n"
                "2. Dr. Sofia Mehta — 2026-09-26 2 PM IST"
            ),
        },
    ]
    enriched = enrich_booking_entities(classification.entities, message, history)
    assert enriched.specialty == "cardiology"
    assert enriched.doctor_name is None
    assert enriched.preferred_hour is None


def test_follow_up_inherits_doctor_and_date() -> None:
    entities = ExtractedEntities(preferred_hour=11)
    history = [
        {
            "role": "user",
            "content": "Book Dr. Ana Rivera at 9 AM IST tomorrow",
        },
        {
            "role": "assistant",
            "content": "The 2026-09-26 9 AM IST slot with Dr. Ana Rivera is already booked.",
        },
    ]
    enriched = enrich_booking_entities(entities, "okay then book at 11 AM", history)
    assert enriched.doctor_name == "Dr. Ana Rivera"
    assert enriched.date == "tomorrow"
    assert enriched.preferred_hour == 11
    assert enriched.specialty == "cardiology"
