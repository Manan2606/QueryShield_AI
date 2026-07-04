from pydantic import BaseModel


class CSVColumnDetected(BaseModel):
    name: str
    data_type: str
    nullable: bool
    ordinal_position: int
    sample_values: list[str] | None = None


class CSVUploadResponse(BaseModel):
    message: str
    dataset_id: int
    filename: str
    row_count: int
    column_count: int
    columns: list[CSVColumnDetected]


class CSVPreviewResponse(BaseModel):
    dataset_id: int
    columns: list[str]
    rows: list[dict]
