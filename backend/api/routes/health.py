from fastapi import APIRouter

from config import get_settings
from db.connection import get_connection

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/db")
def health_db() -> dict[str, str]:
    settings = get_settings()
    parsed_host = settings.postgres_host
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        return {"status": "error", "detail": str(exc), "postgres_host": parsed_host}
    return {"status": "ok", "postgres_host": parsed_host}
