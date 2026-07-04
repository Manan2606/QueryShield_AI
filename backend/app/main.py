from fastapi import FastAPI

from app.db.database import Base, engine
from app.models.audit_log import AuditLog
from app.models.user import User
from app.routers.auth import router as auth_router
from app.routers.datasets import router as datasets_router
from app.routers.health import router as health_router
from app.routers.users import router as users_router


app = FastAPI(
    title="QueryShield AI API",
    version="0.1.0",
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(datasets_router)


@app.on_event("startup")
def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/")
def read_root() -> dict[str, str]:
    return {
        "message": "QueryShield AI API is running",
        "version": "0.1.0",
    }
