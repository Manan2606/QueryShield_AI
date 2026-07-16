from datetime import datetime
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.database import get_db
from app.models.dataset_column import DatasetColumn
from app.models.user import User
from app.schemas.bigquery import BigQueryLoadResponse, BigQueryTableInfoResponse
from app.schemas.dataset import DatasetCreate, DatasetDetailResponse, DatasetResponse, DatasetUpdate
from app.schemas.upload import CSVPreviewResponse, CSVUploadResponse
from app.services.audit_service import create_audit_log
from app.services.bigquery_service import get_bigquery_table_info as fetch_bigquery_table_info
from app.services.bigquery_service import load_csv_to_bigquery
from app.services.csv_service import analyze_csv, preview_csv, save_upload_file, validate_csv_file
from app.services.storage_service import get_upload_storage
from app.services.dataset_service import (
    DatasetDeletionBlocked,
    create_dataset,
    delete_user_dataset,
    get_user_dataset_by_id,
    list_user_datasets,
    update_user_dataset,
)


router = APIRouter(prefix="/datasets", tags=["datasets"])


def _add_audit_log(
    db: Session,
    user_id: int,
    action: str,
    dataset_id: int,
    details: dict | None = None,
) -> None:
    create_audit_log(db, user_id, action, "dataset", str(dataset_id), details)


@router.post("", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
def create_dataset_endpoint(
    dataset_in: DatasetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DatasetResponse:
    dataset = create_dataset(db, current_user.id, dataset_in)
    create_audit_log(db, current_user.id, "dataset.created", "dataset", str(dataset.id), {"dataset_id": dataset.id, "name": dataset.name})
    db.commit()
    return DatasetResponse.model_validate(dataset)


@router.get("", response_model=list[DatasetResponse])
def list_datasets(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DatasetResponse]:
    datasets = list_user_datasets(db, current_user.id, skip=skip, limit=limit)
    return [DatasetResponse.model_validate(dataset) for dataset in datasets]


@router.get("/{dataset_id}", response_model=DatasetDetailResponse)
def read_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DatasetDetailResponse:
    dataset = get_user_dataset_by_id(db, current_user.id, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    return DatasetDetailResponse.model_validate(dataset)


@router.patch("/{dataset_id}", response_model=DatasetResponse)
def update_dataset(
    dataset_id: int,
    dataset_in: DatasetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DatasetResponse:
    dataset = update_user_dataset(db, current_user.id, dataset_id, dataset_in)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    create_audit_log(db, current_user.id, "dataset.updated", "dataset", str(dataset.id), {"dataset_id": dataset.id})
    db.commit()
    return DatasetResponse.model_validate(dataset)


@router.delete("/{dataset_id}")
def delete_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    try:
        dataset = delete_user_dataset(db, current_user.id, dataset_id)
    except DatasetDeletionBlocked as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    create_audit_log(db, current_user.id, "dataset.deleted", "dataset", str(dataset.id), {"dataset_id": dataset.id, "name": dataset.name})
    db.commit()
    return {"message": "Dataset deleted successfully"}


@router.post("/{dataset_id}/upload-csv", response_model=CSVUploadResponse)
def upload_csv(
    dataset_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CSVUploadResponse:
    dataset = get_user_dataset_by_id(db, current_user.id, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    try:
        validate_csv_file(file)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        original_filename, storage_path, analysis_path = save_upload_file(file, dataset_id)
        storage = get_upload_storage()
        try:
            analysis = analyze_csv(analysis_path)
        finally:
            storage.cleanup_local_path(analysis_path)
    except ValueError as exc:
        dataset.status = "failed"
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    db.query(DatasetColumn).filter(DatasetColumn.dataset_id == dataset.id).delete(synchronize_session=False)

    for column_data in analysis["columns"]:
        column = DatasetColumn(
            dataset_id=dataset.id,
            name=column_data["name"],
            data_type=column_data["data_type"],
            nullable=column_data["nullable"],
            ordinal_position=column_data["ordinal_position"],
            sample_values=column_data["sample_values"],
        )
        db.add(column)

    dataset.original_filename = original_filename
    dataset.storage_path = storage_path
    dataset.status = "schema_detected"
    dataset.row_count = analysis["row_count"]
    dataset.column_count = analysis["column_count"]
    create_audit_log(db, current_user.id, "dataset.csv_uploaded", "dataset", str(dataset.id), {"dataset_id": dataset.id, "filename": original_filename})
    create_audit_log(
        db,
        current_user.id,
        "dataset.schema_detected",
        "dataset",
        str(dataset.id),
        {"dataset_id": dataset.id, "row_count": analysis["row_count"], "column_count": analysis["column_count"]},
    )
    db.commit()
    db.refresh(dataset)

    return CSVUploadResponse(
        message="CSV uploaded and schema detected successfully",
        dataset_id=dataset.id,
        filename=original_filename,
        row_count=analysis["row_count"],
        column_count=analysis["column_count"],
        columns=[
            {
                "name": column["name"],
                "data_type": column["data_type"],
                "nullable": column["nullable"],
                "ordinal_position": column["ordinal_position"],
                "sample_values": column["sample_values"],
            }
            for column in analysis["columns"]
        ],
    )


@router.get("/{dataset_id}/preview", response_model=CSVPreviewResponse)
def preview_dataset_csv(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CSVPreviewResponse:
    dataset = get_user_dataset_by_id(db, current_user.id, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    if not dataset.storage_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No CSV file uploaded for this dataset")

    storage = get_upload_storage()
    preview_path = storage.local_path_for_read(dataset.storage_path)
    try:
        preview = preview_csv(preview_path, limit=settings.CSV_PREVIEW_ROWS)
    finally:
        storage.cleanup_local_path(preview_path)
    return CSVPreviewResponse(dataset_id=dataset.id, columns=preview["columns"], rows=preview["rows"])


@router.post("/{dataset_id}/load-bigquery", response_model=BigQueryLoadResponse)
def load_dataset_to_bigquery(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BigQueryLoadResponse:
    dataset = get_user_dataset_by_id(db, current_user.id, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    if not dataset.storage_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No CSV file uploaded for this dataset")
    storage = get_upload_storage()
    if not storage.exists(dataset.storage_path):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded CSV file was not found")

    columns = (
        db.query(DatasetColumn)
        .filter(DatasetColumn.dataset_id == dataset.id)
        .order_by(DatasetColumn.ordinal_position)
        .all()
    )
    if not columns:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No detected schema found for this dataset")

    dataset.status = "loading"
    dataset.load_error = None
    _add_audit_log(db, current_user.id, "dataset.bigquery_load_started", dataset.id)
    db.commit()
    db.refresh(dataset)

    try:
        load_result = load_csv_to_bigquery(dataset, columns)
    except Exception as exc:
        error_message = str(exc)
        dataset.status = "failed"
        dataset.load_error = error_message
        _add_audit_log(
            db,
            current_user.id,
            "dataset.bigquery_load_failed",
            dataset.id,
            {"error": error_message},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load dataset into BigQuery: {error_message}",
        ) from exc

    dataset.status = "loaded"
    dataset.bigquery_table_id = load_result["bigquery_table_id"]
    dataset.load_error = None
    dataset.loaded_at = datetime.utcnow()
    _add_audit_log(
        db,
        current_user.id,
        "dataset.bigquery_load_succeeded",
        dataset.id,
        {"bigquery_table_id": dataset.bigquery_table_id, "job_id": load_result.get("job_id")},
    )
    db.commit()
    db.refresh(dataset)

    return BigQueryLoadResponse(
        message="Dataset loaded into BigQuery successfully",
        dataset_id=dataset.id,
        status=dataset.status,
        bigquery_table_id=dataset.bigquery_table_id or "",
        row_count=load_result.get("row_count"),
        column_count=load_result.get("column_count"),
    )


@router.get("/{dataset_id}/bigquery-info", response_model=BigQueryTableInfoResponse)
def get_dataset_bigquery_info(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BigQueryTableInfoResponse:
    dataset = get_user_dataset_by_id(db, current_user.id, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    if not dataset.bigquery_table_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dataset has not been loaded into BigQuery")

    try:
        table_info = fetch_bigquery_table_info(dataset.bigquery_table_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch BigQuery table info: {exc}",
        ) from exc

    return BigQueryTableInfoResponse(
        dataset_id=dataset.id,
        bigquery_table_id=dataset.bigquery_table_id,
        num_rows=table_info.get("num_rows"),
        num_bytes=table_info.get("num_bytes"),
        schema=table_info.get("schema", []),
    )
