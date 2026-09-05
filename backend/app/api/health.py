"""Health check API endpoint."""
import platform
from datetime import datetime, timezone

from fastapi import APIRouter

from app.database import check_db_connection
from app.schemas import HealthResponse

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Health check")
def health_check():
    """
    Verify that the backend is running and the database is reachable.
    Returns status='ok' when both are healthy.
    """
    db_ok = check_db_connection()
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        database="connected" if db_ok else "unreachable",
        version="1.0.0",
    )
