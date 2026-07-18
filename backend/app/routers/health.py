from fastapi import APIRouter, HTTPException, status

from app.core.config import validate_production_settings
from app.db.readiness import DatabaseReadinessError, verify_database_ready
from app.schemas.health import DatabaseHealthResponse, HealthResponse, ReadinessResponse


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return {
        "status": "healthy",
        "service": "queryshield-ai-pro-backend",
    }


def _verify_readiness() -> None:
    validate_production_settings()
    verify_database_ready()


@router.get("/health/db", response_model=DatabaseHealthResponse)
def database_health_check() -> DatabaseHealthResponse:
    try:
        verify_database_ready()
    except DatabaseReadinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return {
        "status": "healthy",
        "database": "connected",
        "schema_ready": True,
        "migration_current": True,
    }


@router.get("/ready", response_model=ReadinessResponse)
def readiness_check() -> ReadinessResponse:
    try:
        _verify_readiness()
    except (DatabaseReadinessError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return {
        "status": "ready",
        "database": "connected",
        "schema_ready": True,
        "migration_current": True,
        "config_ready": True,
    }
