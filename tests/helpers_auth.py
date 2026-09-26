import os

import jwt

TEST_USER_ID = "11111111-1111-4111-8111-111111111111"


def mint_supabase_token(
    *,
    sub: str = TEST_USER_ID,
    email: str = "jane@example.com",
    phone: str | None = None,
) -> str:
    secret = os.environ.get(
        "SUPABASE_JWT_SECRET",
        "pytest-supabase-jwt-secret-at-least-32-characters",
    )
    payload: dict[str, str] = {
        "sub": sub,
        "role": "authenticated",
        "aud": "authenticated",
        "email": email,
    }
    if phone:
        payload["phone"] = phone
    return jwt.encode(payload, secret, algorithm="HS256")
