import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("STORAGE_BACKEND", "local")
os.environ.setdefault("GCS_UPLOAD_BUCKET", "")

from app.core.config import settings
from app.db import database
from app.main import app
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn


@pytest.fixture()
def client():
    settings.STORAGE_BACKEND = "local"
    settings.GCS_UPLOAD_BUCKET = ""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    database.engine = engine
    database.SessionLocal = TestingSessionLocal
    database.Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[database.get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def _auth_headers(client, email="dataset@example.com"):
    signup_response = client.post(
        "/auth/signup",
        json={"email": email, "password": "password123", "full_name": "Dataset User"},
    )
    assert signup_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        data={"username": email, "password": "password123"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_dataset(client, headers, name="Sales Data"):
    create_response = client.post(
        "/datasets",
        json={"name": name, "description": "Monthly sales dataset"},
        headers=headers,
    )
    assert create_response.status_code == 201
    return create_response.json()


def _upload_csv(client, headers, dataset_id):
    upload_response = client.post(
        f"/datasets/{dataset_id}/upload-csv",
        headers=headers,
        files={"file": ("people.csv", b"id,name\n1,Alice\n2,Bob\n", "text/csv")},
    )
    assert upload_response.status_code == 200
    return upload_response.json()


def test_create_and_list_dataset_for_authenticated_user(client):
    headers = _auth_headers(client)

    create_response = client.post(
        "/datasets",
        json={"name": "Sales Data", "description": "Monthly sales dataset"},
        headers=headers,
    )
    assert create_response.status_code == 201
    dataset = create_response.json()
    assert dataset["name"] == "Sales Data"
    assert dataset["owner_id"] == 1

    list_response = client.get("/datasets", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    read_response = client.get(f"/datasets/{dataset['id']}", headers=headers)
    assert read_response.status_code == 200
    assert read_response.json()["name"] == "Sales Data"


def test_upload_csv_and_preview_for_dataset(client):
    headers = _auth_headers(client, "upload@example.com")
    dataset = _create_dataset(client, headers, "Uploadable Dataset")

    payload = _upload_csv(client, headers, dataset["id"])
    assert payload["row_count"] == 2
    assert payload["column_count"] == 2
    assert payload["columns"][0]["name"] == "id"

    preview_response = client.get(f"/datasets/{dataset['id']}/preview", headers=headers)
    assert preview_response.status_code == 200
    preview_payload = preview_response.json()
    assert preview_payload["columns"] == ["id", "name"]
    assert len(preview_payload["rows"]) == 2


def test_unauthenticated_dataset_request_is_rejected(client):
    response = client.get("/datasets")
    assert response.status_code == 401


def test_unauthenticated_user_cannot_load_dataset_to_bigquery(client):
    response = client.post("/datasets/1/load-bigquery")
    assert response.status_code == 401


def test_user_cannot_load_another_users_dataset_to_bigquery(client):
    owner_headers = _auth_headers(client, "owner@example.com")
    other_headers = _auth_headers(client, "other@example.com")
    dataset = _create_dataset(client, owner_headers)

    response = client.post(f"/datasets/{dataset['id']}/load-bigquery", headers=other_headers)

    assert response.status_code == 404


def test_dataset_without_uploaded_csv_cannot_be_loaded_to_bigquery(client):
    headers = _auth_headers(client, "nocsv@example.com")
    dataset = _create_dataset(client, headers)

    response = client.post(f"/datasets/{dataset['id']}/load-bigquery", headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "No CSV file uploaded for this dataset"


def test_dataset_without_detected_schema_cannot_be_loaded_to_bigquery(client):
    headers = _auth_headers(client, "noschema@example.com")
    dataset = _create_dataset(client, headers)
    csv_path = __file__

    db = database.SessionLocal()
    try:
        db_dataset = db.get(Dataset, dataset["id"])
        db_dataset.storage_path = str(csv_path)
        db.commit()
    finally:
        db.close()

    response = client.post(f"/datasets/{dataset['id']}/load-bigquery", headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "No detected schema found for this dataset"


def test_successful_bigquery_load_updates_dataset(monkeypatch, client):
    headers = _auth_headers(client, "load@example.com")
    dataset = _create_dataset(client, headers, "Sales Data 2026")
    _upload_csv(client, headers, dataset["id"])
    observed_statuses = []

    def fake_load_csv_to_bigquery(dataset, dataset_columns):
        observed_statuses.append(dataset.status)
        assert len(dataset_columns) == 2
        return {
            "bigquery_table_id": "test-project.queryshield_demo.dataset_1_sales_data_2026",
            "job_id": "job-123",
            "row_count": 2,
            "column_count": 2,
        }

    monkeypatch.setattr("app.routers.datasets.load_csv_to_bigquery", fake_load_csv_to_bigquery)

    response = client.post(f"/datasets/{dataset['id']}/load-bigquery", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "message": "Dataset loaded into BigQuery successfully",
        "dataset_id": dataset["id"],
        "status": "loaded",
        "bigquery_table_id": "test-project.queryshield_demo.dataset_1_sales_data_2026",
        "row_count": 2,
        "column_count": 2,
    }
    assert observed_statuses == ["loading"]

    read_response = client.get(f"/datasets/{dataset['id']}", headers=headers)
    assert read_response.status_code == 200
    stored_dataset = read_response.json()
    assert stored_dataset["status"] == "loaded"
    assert stored_dataset["bigquery_table_id"] == "test-project.queryshield_demo.dataset_1_sales_data_2026"
    assert stored_dataset["load_error"] is None
    assert stored_dataset["loaded_at"] is not None


def test_failed_bigquery_load_sets_failed_status(monkeypatch, client):
    headers = _auth_headers(client, "failedload@example.com")
    dataset = _create_dataset(client, headers)
    _upload_csv(client, headers, dataset["id"])

    def fake_load_csv_to_bigquery(dataset, dataset_columns):
        raise RuntimeError("BigQuery credentials are invalid")

    monkeypatch.setattr("app.routers.datasets.load_csv_to_bigquery", fake_load_csv_to_bigquery)

    response = client.post(f"/datasets/{dataset['id']}/load-bigquery", headers=headers)

    assert response.status_code == 500
    assert "Failed to load dataset into BigQuery" in response.json()["detail"]

    read_response = client.get(f"/datasets/{dataset['id']}", headers=headers)
    assert read_response.status_code == 200
    stored_dataset = read_response.json()
    assert stored_dataset["status"] == "failed"
    assert stored_dataset["load_error"] == "BigQuery credentials are invalid"


def test_bigquery_info_endpoint_requires_ownership(client):
    owner_headers = _auth_headers(client, "infoowner@example.com")
    other_headers = _auth_headers(client, "infoother@example.com")
    dataset = _create_dataset(client, owner_headers)

    response = client.get(f"/datasets/{dataset['id']}/bigquery-info", headers=other_headers)

    assert response.status_code == 404


def test_bigquery_info_endpoint_rejects_unloaded_datasets(client):
    headers = _auth_headers(client, "unloaded@example.com")
    dataset = _create_dataset(client, headers)

    response = client.get(f"/datasets/{dataset['id']}/bigquery-info", headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "Dataset has not been loaded into BigQuery"


def test_bigquery_info_endpoint_returns_table_metadata(monkeypatch, client):
    headers = _auth_headers(client, "info@example.com")
    dataset = _create_dataset(client, headers)

    db = database.SessionLocal()
    try:
        db_dataset = db.get(Dataset, dataset["id"])
        db_dataset.bigquery_table_id = "test-project.queryshield_demo.dataset_1_sales_data"
        db_dataset.status = "loaded"
        db.add(
            DatasetColumn(
                dataset_id=dataset["id"],
                name="order_id",
                data_type="INTEGER",
                nullable=True,
                ordinal_position=1,
            )
        )
        db.commit()
    finally:
        db.close()

    def fake_fetch_bigquery_table_info(bigquery_table_id):
        assert bigquery_table_id == "test-project.queryshield_demo.dataset_1_sales_data"
        return {
            "table_id": bigquery_table_id,
            "num_rows": 100,
            "num_bytes": 2048,
            "schema": [{"name": "order_id", "type": "INT64", "mode": "NULLABLE"}],
        }

    monkeypatch.setattr("app.routers.datasets.fetch_bigquery_table_info", fake_fetch_bigquery_table_info)

    response = client.get(f"/datasets/{dataset['id']}/bigquery-info", headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "dataset_id": dataset["id"],
        "bigquery_table_id": "test-project.queryshield_demo.dataset_1_sales_data",
        "num_rows": 100,
        "num_bytes": 2048,
        "schema": [{"name": "order_id", "type": "INT64", "mode": "NULLABLE"}],
    }
