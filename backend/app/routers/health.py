from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.health import DatabaseHealthResponse, HealthResponse


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return {
        "status": "healthy",
        "service": "queryshield-ai-pro-backend",
    }


@router.get("/health/db", response_model=DatabaseHealthResponse)
def database_health_check(db: Session = Depends(get_db)) -> DatabaseHealthResponse:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed",
        ) from exc

    return {
        "status": "healthy",
        "database": "connected",
    }
