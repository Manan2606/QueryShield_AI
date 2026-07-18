from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str


class DatabaseHealthResponse(BaseModel):
    status: str
    database: str
    schema_ready: bool = True
    migration_current: bool = True


class ReadinessResponse(BaseModel):
    status: str
    database: str
    schema_ready: bool = True
    migration_current: bool = True
    config_ready: bool = True
