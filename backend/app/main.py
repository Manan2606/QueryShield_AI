from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings, validate_production_settings
from app.db.readiness import run_startup_migrations
from app.routers.audit_logs import router as audit_logs_router
from app.routers.auth import router as auth_router
from app.routers.datasets import router as datasets_router
from app.routers.health import router as health_router
from app.routers.queries import router as queries_router
from app.routers.users import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    validate_production_settings()
    run_startup_migrations()
    yield


app = FastAPI(
    title="QueryShield AI API",
    version="0.1.0",
    lifespan=lifespan,
)

if settings.frontend_origins_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.frontend_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(audit_logs_router)
app.include_router(datasets_router)
app.include_router(queries_router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {
        "message": "QueryShield AI API is running",
        "version": "0.1.0",
    }
