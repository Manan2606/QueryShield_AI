from sqlalchemy.orm import Session

from app.models.dataset import Dataset
from app.models.query_request import QueryRequest
from app.schemas.dataset import DatasetCreate, DatasetUpdate


class DatasetDeletionBlocked(RuntimeError):
    pass


def create_dataset(db: Session, owner_id: int, dataset_in: DatasetCreate) -> Dataset:
    dataset = Dataset(
        owner_id=owner_id, name=dataset_in.name, description=dataset_in.description
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


def get_dataset_by_id(db: Session, dataset_id: int) -> Dataset | None:
    return db.query(Dataset).filter(Dataset.id == dataset_id).first()


def get_user_dataset_by_id(
    db: Session, owner_id: int, dataset_id: int
) -> Dataset | None:
    return (
        db.query(Dataset)
        .filter(Dataset.owner_id == owner_id, Dataset.id == dataset_id)
        .first()
    )


def list_user_datasets(
    db: Session, owner_id: int, skip: int = 0, limit: int = 100
) -> list[Dataset]:
    return (
        db.query(Dataset)
        .filter(Dataset.owner_id == owner_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_user_dataset(
    db: Session, owner_id: int, dataset_id: int, dataset_in: DatasetUpdate
) -> Dataset | None:
    dataset = get_user_dataset_by_id(db, owner_id, dataset_id)
    if dataset is None:
        return None

    if dataset_in.name is not None:
        dataset.name = dataset_in.name
    if dataset_in.description is not None:
        dataset.description = dataset_in.description
    if dataset_in.status is not None:
        dataset.status = dataset_in.status

    db.commit()
    db.refresh(dataset)
    return dataset


def delete_user_dataset(db: Session, owner_id: int, dataset_id: int) -> Dataset | None:
    dataset = get_user_dataset_by_id(db, owner_id, dataset_id)
    if dataset is None:
        return None

    has_query_history = (
        db.query(QueryRequest.id).filter(QueryRequest.dataset_id == dataset.id).first()
        is not None
    )
    if has_query_history:
        raise DatasetDeletionBlocked(
            "Dataset has query history and cannot be deleted in this MVP"
        )

    db.delete(dataset)
    db.commit()
    return dataset
