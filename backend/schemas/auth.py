from typing import Literal

from pydantic import BaseModel, Field

AuthVia = Literal["email", "phone"]


class ProfileUpsertRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)


class ConsentRequest(BaseModel):
    granted: bool


class PatientProfile(BaseModel):
    patient_id: str
    full_name: str
    email: str | None = None
    phone: str | None = None
    consent_granted: bool = False
    auth_via: AuthVia | None = None
