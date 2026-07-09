import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("GEMINI_MODEL", "gemini-2.5-flash")

from app.db import database
from app.main import app
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.query_request import QueryRequest


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


def _auth_headers(client, email="query@example.com"):
    signup_response = client.post(
        "/auth/signup",
        json={"email": email, "password": "password123", "full_name": "Query User"},
    )
    assert signup_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        data={"username": email, "password": "password123"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, signup_response.json()["id"]


def _create_dataset_record(user_id, *, status="loaded", table_id="test-project.queryshield_demo.dataset_1_sales"):
    db = database.SessionLocal()
    try:
        dataset = Dataset(
            owner_id=user_id,
            name="Sales Data",
            status=status,
            bigquery_table_id=table_id,
        )
        db.add(dataset)
        db.flush()
        db.add_all(
            [
                DatasetColumn(dataset_id=dataset.id, name="region", data_type="STRING", nullable=True, ordinal_position=1),
                DatasetColumn(dataset_id=dataset.id, name="total_amount", data_type="FLOAT", nullable=True, ordinal_position=2),
            ]
        )
        db.commit()
        db.refresh(dataset)
        return dataset.id
    finally:
        db.close()


def _clear_columns(dataset_id):
    db = database.SessionLocal()
    try:
        db.query(DatasetColumn).filter(DatasetColumn.dataset_id == dataset_id).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def _query_records():
    db = database.SessionLocal()
    try:
        return db.query(QueryRequest).order_by(QueryRequest.id).all()
    finally:
        db.close()


def test_unauthenticated_user_cannot_generate_sql(client):
    response = client.post("/queries/generate", json={"dataset_id": 1, "question": "Total sales by region?"})

    assert response.status_code == 401


def test_user_cannot_generate_sql_for_another_users_dataset(client):
    _owner_headers, owner_id = _auth_headers(client, "owner-query@example.com")
    other_headers, _other_id = _auth_headers(client, "other-query@example.com")
    dataset_id = _create_dataset_record(owner_id)

    response = client.post(
        "/queries/generate",
        json={"dataset_id": dataset_id, "question": "Total sales by region?"},
        headers=other_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Dataset not found"


def test_dataset_must_be_loaded(client):
    headers, user_id = _auth_headers(client, "unloaded-query@example.com")
    dataset_id = _create_dataset_record(user_id, status="schema_detected")

    response = client.post(
        "/queries/generate",
        json={"dataset_id": dataset_id, "question": "Total sales by region?"},
        headers=headers,
    )

    assert response.status_code == 400
    assert "loaded into BigQuery" in response.json()["detail"]


def test_dataset_must_have_bigquery_table_id(client):
    headers, user_id = _auth_headers(client, "notable-query@example.com")
    dataset_id = _create_dataset_record(user_id, table_id=None)

    response = client.post(
        "/queries/generate",
        json={"dataset_id": dataset_id, "question": "Total sales by region?"},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Dataset does not have a BigQuery table ID"


def test_dataset_must_have_stored_columns(client):
    headers, user_id = _auth_headers(client, "nocolumn-query@example.com")
    dataset_id = _create_dataset_record(user_id)
    _clear_columns(dataset_id)

    response = client.post(
        "/queries/generate",
        json={"dataset_id": dataset_id, "question": "Total sales by region?"},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Dataset does not have stored schema columns"


def test_empty_question_is_rejected(client):
    headers, user_id = _auth_headers(client, "empty-query@example.com")
    dataset_id = _create_dataset_record(user_id)

    response = client.post(
        "/queries/generate",
        json={"dataset_id": dataset_id, "question": "   "},
        headers=headers,
    )

    assert response.status_code == 422


def test_successful_generation_stores_generated_sql(monkeypatch, client):
    headers, user_id = _auth_headers(client, "success-query@example.com")
    dataset_id = _create_dataset_record(user_id)
    observed = {}

    def fake_generate_bigquery_sql(table_id, columns, question):
        observed["table_id"] = table_id
        observed["columns"] = [(column.name, column.data_type) for column in columns]
        observed["question"] = question
        return "```sql\nSELECT region, SUM(total_amount) AS total_sales FROM `test-project.queryshield_demo.dataset_1_sales` GROUP BY region\n```"

    monkeypatch.setattr("app.services.query_generation_service.generate_bigquery_sql", fake_generate_bigquery_sql)

    response = client.post(
        "/queries/generate",
        json={"dataset_id": dataset_id, "question": "  What is total sales by region?  "},
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["dataset_id"] == dataset_id
    assert payload["question"] == "What is total sales by region?"
    assert payload["generated_sql"].startswith("SELECT region")
    assert payload["model_name"] == "gemini-2.5-flash"
    assert payload["status"] == "generated"
    assert observed == {
        "table_id": "test-project.queryshield_demo.dataset_1_sales",
        "columns": [("region", "STRING"), ("total_amount", "FLOAT")],
        "question": "What is total sales by region?",
    }

    records = _query_records()
    assert len(records) == 1
    assert records[0].generation_status == "generated"
    assert records[0].generated_sql == payload["generated_sql"]


def test_gemini_failure_sets_status_failed(monkeypatch, client):
    headers, user_id = _auth_headers(client, "failure-query@example.com")
    dataset_id = _create_dataset_record(user_id)

    def fake_generate_bigquery_sql(table_id, columns, question):
        raise RuntimeError("Gemini unavailable")

    monkeypatch.setattr("app.services.query_generation_service.generate_bigquery_sql", fake_generate_bigquery_sql)

    response = client.post(
        "/queries/generate",
        json={"dataset_id": dataset_id, "question": "Total sales?"},
        headers=headers,
    )

    assert response.status_code == 502
    records = _query_records()
    assert len(records) == 1
    assert records[0].generation_status == "failed"
    assert records[0].error_message == "Gemini unavailable"


def test_forbidden_statement_output_is_rejected(monkeypatch, client):
    headers, user_id = _auth_headers(client, "forbidden-query@example.com")
    dataset_id = _create_dataset_record(user_id)

    monkeypatch.setattr(
        "app.services.query_generation_service.generate_bigquery_sql",
        lambda table_id, columns, question: "DELETE FROM `test-project.queryshield_demo.dataset_1_sales` WHERE TRUE",
    )

    response = client.post(
        "/queries/generate",
        json={"dataset_id": dataset_id, "question": "Delete rows?"},
        headers=headers,
    )

    assert response.status_code == 502
    assert "SELECT or WITH" in response.json()["detail"]


def test_sql_not_referencing_selected_table_is_rejected(monkeypatch, client):
    headers, user_id = _auth_headers(client, "wrongtable-query@example.com")
    dataset_id = _create_dataset_record(user_id)

    monkeypatch.setattr(
        "app.services.query_generation_service.generate_bigquery_sql",
        lambda table_id, columns, question: "SELECT region FROM `test-project.queryshield_demo.other_table`",
    )

    response = client.post(
        "/queries/generate",
        json={"dataset_id": dataset_id, "question": "Show regions"},
        headers=headers,
    )

    assert response.status_code == 502
    assert "selected BigQuery table" in response.json()["detail"]


def test_sql_generation_does_not_execute_bigquery(monkeypatch, client):
    headers, user_id = _auth_headers(client, "noexecute-query@example.com")
    dataset_id = _create_dataset_record(user_id)

    monkeypatch.setattr(
        "app.services.query_generation_service.generate_bigquery_sql",
        lambda table_id, columns, question: "SELECT region FROM `test-project.queryshield_demo.dataset_1_sales` LIMIT 10",
    )

    response = client.post(
        "/queries/generate",
        json={"dataset_id": dataset_id, "question": "Show regions"},
        headers=headers,
    )

    assert response.status_code == 200
    assert "num_rows" not in response.text
    assert "total_bytes" not in response.text


def test_user_can_list_only_their_own_query_records(monkeypatch, client):
    owner_headers, owner_id = _auth_headers(client, "list-owner-query@example.com")
    other_headers, other_id = _auth_headers(client, "list-other-query@example.com")
    owner_dataset_id = _create_dataset_record(owner_id, table_id="test-project.queryshield_demo.owner_table")
    other_dataset_id = _create_dataset_record(other_id, table_id="test-project.queryshield_demo.other_table")

    def fake_generate_bigquery_sql(table_id, columns, question):
        return f"SELECT region FROM `{table_id}` LIMIT 10"

    monkeypatch.setattr("app.services.query_generation_service.generate_bigquery_sql", fake_generate_bigquery_sql)
    assert client.post("/queries/generate", json={"dataset_id": owner_dataset_id, "question": "Owner?"}, headers=owner_headers).status_code == 200
    assert client.post("/queries/generate", json={"dataset_id": other_dataset_id, "question": "Other?"}, headers=other_headers).status_code == 200

    response = client.get("/queries", headers=owner_headers)

    assert response.status_code == 200
    records = response.json()
    assert len(records) == 1
    assert records[0]["dataset_id"] == owner_dataset_id


def test_user_cannot_read_another_users_query_record(monkeypatch, client):
    owner_headers, owner_id = _auth_headers(client, "read-owner-query@example.com")
    other_headers, _other_id = _auth_headers(client, "read-other-query@example.com")
    dataset_id = _create_dataset_record(owner_id)

    monkeypatch.setattr(
        "app.services.query_generation_service.generate_bigquery_sql",
        lambda table_id, columns, question: f"SELECT region FROM `{table_id}` LIMIT 10",
    )
    generate_response = client.post(
        "/queries/generate",
        json={"dataset_id": dataset_id, "question": "Show regions"},
        headers=owner_headers,
    )
    assert generate_response.status_code == 200

    response = client.get(f"/queries/{generate_response.json()['id']}", headers=other_headers)

    assert response.status_code == 404
