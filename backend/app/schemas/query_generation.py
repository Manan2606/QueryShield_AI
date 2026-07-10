from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class QueryGenerateRequest(BaseModel):
    dataset_id: int
    question: str = Field(..., max_length=2000)

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        question = value.strip()
        if not question:
            raise ValueError("Question cannot be empty")
        return question


class QueryGenerateResponse(BaseModel):
    id: int
    dataset_id: int
    question: str
    generated_sql: str
    model_name: str | None
    status: str
    created_at: datetime
    validation_status: str
    is_safe: bool | None
    validation_errors: list[str] | None
    validation_warnings: list[str] | None
    validated_at: datetime | None


class QueryRequestSummary(BaseModel):
    id: int
    dataset_id: int
    question: str
    generated_sql: str | None
    model_name: str | None
    status: str
    error_message: str | None
    created_at: datetime
    validation_status: str
    is_safe: bool | None
    validation_errors: list[str] | None
    validation_warnings: list[str] | None
    validated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
