from pydantic import BaseModel, Field

from schemas.enums import Intent


class ExtractedEntities(BaseModel):
    specialty: str | None = None
    doctor_name: str | None = None
    date: str | None = None
    slot: str | None = None
    appointment_id: str | None = None


class IntentClassification(BaseModel):
    """Structured LLM output for intent routing."""

    intent: Intent
    confidence: float = Field(ge=0.0, le=1.0)
    entities: ExtractedEntities = Field(default_factory=ExtractedEntities)
    assistant_reply: str = Field(
        description="Short natural-language reply to the patient for this turn."
    )
    is_emergency: bool = False
