from typing import Literal

from pydantic import BaseModel, Field

AuthVia = Literal["email", "phone"]


class LoginEmailRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=4)
    full_name: str = Field(min_length=1, max_length=255)


class OtpRequestRequest(BaseModel):
    phone: str = Field(min_length=10)


class OtpVerifyRequest(BaseModel):
    phone: str = Field(min_length=10)
    code: str = Field(min_length=4, max_length=8)
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


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    patient: PatientProfile


class OtpRequestResponse(BaseModel):
    message: str
    demo_code: str | None = None
