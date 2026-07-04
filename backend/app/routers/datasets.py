from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.database import get_db
from app.models.dataset_column import DatasetColumn
from app.models.user import User
from app.schemas.dataset import DatasetCreate, DatasetDetailResponse, DatasetResponse, DatasetUpdate
from app.schemas.upload import CSVPreviewResponse, CSVUploadResponse
from app.services.csv_service import analyze_csv, preview_csv, save_upload_file, validate_csv_file
from app.services.dataset_service import (
    create_dataset,
    delete_user_dataset,
    get_user_dataset_by_id,
    list_user_datasets,
    update_user_dataset,
)


router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
def create_dataset_endpoint(
    dataset_in: DatasetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DatasetResponse:
    dataset = create_dataset(db, current_user.id, dataset_in)
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
    return DatasetResponse.model_validate(dataset)


@router.delete("/{dataset_id}")
def delete_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    dataset = delete_user_dataset(db, current_user.id, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
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
        original_filename, storage_path = save_upload_file(file, dataset_id)
        analysis = analyze_csv(storage_path)
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

    preview = preview_csv(dataset.storage_path, limit=settings.CSV_PREVIEW_ROWS)
    return CSVPreviewResponse(dataset_id=dataset.id, columns=preview["columns"], rows=preview["rows"])
