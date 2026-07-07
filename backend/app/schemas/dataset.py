from datetime import datetime

from pydantic import BaseModel


class DatasetColumnBase(BaseModel):
    name: str
    data_type: str
    nullable: bool = True
    ordinal_position: int
    sample_values: list | None = None


class DatasetColumnCreate(DatasetColumnBase):
    pass


class DatasetColumnResponse(DatasetColumnBase):
    id: int

    model_config = {"from_attributes": True}


class DatasetBase(BaseModel):
    name: str
    description: str | None = None


class DatasetCreate(DatasetBase):
    pass


class DatasetUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None


class DatasetResponse(DatasetBase):
    id: int
    owner_id: int
    source_type: str
    original_filename: str | None
    storage_path: str | None
    bigquery_table_id: str | None
    status: str
    load_error: str | None
    loaded_at: datetime | None
    row_count: int | None
    column_count: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DatasetDetailResponse(DatasetResponse):
    columns: list[DatasetColumnResponse] = []
