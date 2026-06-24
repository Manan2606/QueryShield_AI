from fastapi import FastAPI

from app.routers.health import router as health_router


app = FastAPI(
    title="QueryShield AI API",
    version="0.1.0",
)

app.include_router(health_router)

@app.get("/")
def read_root() -> dict[str, str]:
    return {
        "message": "QueryShield AI API is running",
        "version": "0.1.0",
    }
