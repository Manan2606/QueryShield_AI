from pydantic import BaseModel


class BigQueryLoadResponse(BaseModel):
    message: str
    dataset_id: int
    status: str
    bigquery_table_id: str
    row_count: int | None = None
    column_count: int | None = None


class BigQueryTableField(BaseModel):
    name: str
    type: str
    mode: str


class BigQueryTableInfoResponse(BaseModel):
    dataset_id: int
    bigquery_table_id: str
    num_rows: int | None = None
    num_bytes: int | None = None
    schema: list[BigQueryTableField]
