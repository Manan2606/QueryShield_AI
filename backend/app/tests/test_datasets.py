import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")

from app.db import database
from app.main import app


@pytest.fixture()
def client():
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


def test_create_and_list_dataset_for_authenticated_user(client):
    signup_response = client.post(
        "/auth/signup",
        json={"email": "dataset@example.com", "password": "password123", "full_name": "Dataset User"},
    )
    assert signup_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        data={"username": "dataset@example.com", "password": "password123"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

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
    signup_response = client.post(
        "/auth/signup",
        json={"email": "upload@example.com", "password": "password123", "full_name": "Upload User"},
    )
    assert signup_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        data={"username": "upload@example.com", "password": "password123"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/datasets",
        json={"name": "Uploadable Dataset", "description": "CSV upload test"},
        headers=headers,
    )
    assert create_response.status_code == 201
    dataset_id = create_response.json()["id"]

    upload_response = client.post(
        f"/datasets/{dataset_id}/upload-csv",
        headers=headers,
        files={"file": ("people.csv", b"id,name\n1,Alice\n2,Bob\n", "text/csv")},
    )
    assert upload_response.status_code == 200
    payload = upload_response.json()
    assert payload["row_count"] == 2
    assert payload["column_count"] == 2
    assert payload["columns"][0]["name"] == "id"

    preview_response = client.get(f"/datasets/{dataset_id}/preview", headers=headers)
    assert preview_response.status_code == 200
    preview_payload = preview_response.json()
    assert preview_payload["columns"] == ["id", "name"]
    assert len(preview_payload["rows"]) == 2


def test_unauthenticated_dataset_request_is_rejected(client):
    response = client.get("/datasets")
    assert response.status_code == 401
