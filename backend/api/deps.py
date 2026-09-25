from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services.auth import PatientSession, decode_access_token

_bearer = HTTPBearer(auto_error=False)


def get_optional_session(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> PatientSession | None:
    if credentials is None or credentials.scheme.lower() != "bearer":
        return None
    return decode_access_token(credentials.credentials)


def get_required_session(
    session: PatientSession | None = Depends(get_optional_session),
) -> PatientSession:
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not signed in")
    return session
