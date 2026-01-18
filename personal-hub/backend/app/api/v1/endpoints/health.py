"""Health check endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    timestamp: str
    version: str
    environment: str
    database: str
    details: dict[str, str] | None = None


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """
    Check API health status.

    Returns the health status of the API and its dependencies.
    """
    db_status = "healthy"
    db_details = None

    try:
        # Check database connection
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = "unhealthy"
        db_details = {"database_error": str(e)}

    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="1.0.0",
        environment=settings.app_env,
        database=db_status,
        details=db_details,
    )


@router.get("/health/live")
async def liveness_check() -> dict[str, str]:
    """
    Kubernetes liveness probe.

    Simple check that the service is running.
    """
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """
    Kubernetes readiness probe.

    Checks if the service is ready to accept traffic.
    """
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        return {"status": "not_ready"}
