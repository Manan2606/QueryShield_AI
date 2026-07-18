import os
from datetime import date, datetime
from decimal import Decimal

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
from app.models.audit_log import AuditLog
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.query_request import QueryRequest
from app.services.bigquery_service import (
    BigQueryExecutionTimeout,
    QueryExecutionResult,
    QueryResultColumn,
)
from app.services.result_summary_service import EMPTY_RESULT_SUMMARY, ResultSummaryError
from app.services.sql_validation_service import SQLValidatorInternalError


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
        json={"email": email, "password": "Password123!", "full_name": "Query User"},
    )
    assert signup_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        data={"username": email, "password": "Password123!"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, signup_response.json()["id"]


def _create_dataset_record(
    user_id,
    *,
    status="loaded",
    table_id="test-project.queryshield_demo.dataset_1_sales",
):
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
                DatasetColumn(
                    dataset_id=dataset.id,
                    name="region",
                    data_type="STRING",
                    nullable=True,
                    ordinal_position=1,
                ),
                DatasetColumn(
                    dataset_id=dataset.id,
                    name="total_amount",
                    data_type="FLOAT",
                    nullable=True,
                    ordinal_position=2,
                ),
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
        db.query(DatasetColumn).filter(DatasetColumn.dataset_id == dataset_id).delete(
            synchronize_session=False
        )
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
    response = client.post(
        "/queries/generate",
        json={"dataset_id": 1, "question": "Total sales by region?"},
    )

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

    monkeypatch.setattr(
        "app.services.query_generation_service.generate_bigquery_sql",
        fake_generate_bigquery_sql,
    )

    response = client.post(
        "/queries/generate",
        json={
            "dataset_id": dataset_id,
            "question": "  What is total sales by region?  ",
        },
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

    monkeypatch.setattr(
        "app.services.query_generation_service.generate_bigquery_sql",
        fake_generate_bigquery_sql,
    )

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
        lambda table_id,
        columns,
        question: "DELETE FROM `test-project.queryshield_demo.dataset_1_sales` WHERE TRUE",
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
        lambda table_id,
        columns,
        question: "SELECT region FROM `test-project.queryshield_demo.other_table`",
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
        lambda table_id,
        columns,
        question: "SELECT region FROM `test-project.queryshield_demo.dataset_1_sales` LIMIT 10",
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
    owner_dataset_id = _create_dataset_record(
        owner_id, table_id="test-project.queryshield_demo.owner_table"
    )
    other_dataset_id = _create_dataset_record(
        other_id, table_id="test-project.queryshield_demo.other_table"
    )

    def fake_generate_bigquery_sql(table_id, columns, question):
        return f"SELECT region FROM `{table_id}` LIMIT 10"

    monkeypatch.setattr(
        "app.services.query_generation_service.generate_bigquery_sql",
        fake_generate_bigquery_sql,
    )
    assert (
        client.post(
            "/queries/generate",
            json={"dataset_id": owner_dataset_id, "question": "Owner?"},
            headers=owner_headers,
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/queries/generate",
            json={"dataset_id": other_dataset_id, "question": "Other?"},
            headers=other_headers,
        ).status_code
        == 200
    )

    response = client.get("/queries", headers=owner_headers)

    assert response.status_code == 200
    payload = response.json()
    records = payload["items"]
    assert payload["total"] == 1
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

    response = client.get(
        f"/queries/{generate_response.json()['id']}", headers=other_headers
    )

    assert response.status_code == 404


def _create_query_request_record(
    user_id,
    dataset_id,
    *,
    sql="SELECT region FROM `test-project.queryshield_demo.dataset_1_sales` LIMIT 10",
    generation_status="generated",
):
    db = database.SessionLocal()
    try:
        query_request = QueryRequest(
            user_id=user_id,
            dataset_id=dataset_id,
            natural_language_question="Test validation query",
            generated_sql=sql,
            generated_for_table_id="test-project.queryshield_demo.dataset_1_sales",
            generation_status=generation_status,
            model_name="test-model",
        )
        db.add(query_request)
        db.commit()
        db.refresh(query_request)
        return query_request.id
    finally:
        db.close()


def _stored_query_request(query_request_id):
    db = database.SessionLocal()
    try:
        return (
            db.query(QueryRequest).filter(QueryRequest.id == query_request_id).first()
        )
    finally:
        db.close()


def _validate_sql(
    client,
    headers,
    user_id,
    sql,
    *,
    table_id="test-project.queryshield_demo.dataset_1_sales",
):
    dataset_id = _create_dataset_record(user_id, table_id=table_id)
    query_request_id = _create_query_request_record(user_id, dataset_id, sql=sql)
    response = client.post(f"/queries/{query_request_id}/validate", headers=headers)
    return response, query_request_id, dataset_id


def test_unauthenticated_user_cannot_validate_sql(client):
    headers, user_id = _auth_headers(client, "validate-auth-owner@example.com")
    dataset_id = _create_dataset_record(user_id)
    query_request_id = _create_query_request_record(user_id, dataset_id)

    response = client.post(f"/queries/{query_request_id}/validate")

    assert response.status_code == 401


def test_user_cannot_validate_another_users_query(client):
    _owner_headers, owner_id = _auth_headers(client, "validate-owner@example.com")
    other_headers, _other_id = _auth_headers(client, "validate-other@example.com")
    dataset_id = _create_dataset_record(owner_id)
    query_request_id = _create_query_request_record(owner_id, dataset_id)

    response = client.post(
        f"/queries/{query_request_id}/validate", headers=other_headers
    )

    assert response.status_code == 404


def test_query_request_must_exist_for_validation(client):
    headers, _user_id = _auth_headers(client, "validate-missing@example.com")

    response = client.post("/queries/999999/validate", headers=headers)

    assert response.status_code == 404


def test_query_request_must_have_generated_sql_for_validation(client):
    headers, user_id = _auth_headers(client, "validate-nosql@example.com")
    dataset_id = _create_dataset_record(user_id)
    query_request_id = _create_query_request_record(user_id, dataset_id, sql=None)

    response = client.post(f"/queries/{query_request_id}/validate", headers=headers)

    assert response.status_code == 400
    assert "generated SQL" in response.json()["detail"]


def test_query_request_dataset_must_belong_to_user_for_validation(client):
    headers, user_id = _auth_headers(client, "validate-dataset-owner@example.com")
    _other_headers, other_id = _auth_headers(
        client, "validate-dataset-other@example.com"
    )
    other_dataset_id = _create_dataset_record(other_id)
    query_request_id = _create_query_request_record(user_id, other_dataset_id)

    response = client.post(f"/queries/{query_request_id}/validate", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Dataset not found"


@pytest.mark.parametrize(
    ("sql", "expected_statement"),
    [
        (
            "SELECT region FROM `test-project.queryshield_demo.dataset_1_sales` LIMIT 10",
            "SELECT",
        ),
        (
            "WITH regional_sales AS (SELECT region, SUM(total_amount) AS total_sales FROM `test-project.queryshield_demo.dataset_1_sales` GROUP BY region) SELECT region, total_sales FROM regional_sales",
            "SELECT",
        ),
        (
            "WITH regional_sales AS (SELECT region FROM `test-project.queryshield_demo.dataset_1_sales`) SELECT * FROM regional_sales",
            "SELECT",
        ),
        (
            "SELECT region FROM (SELECT region FROM `test-project.queryshield_demo.dataset_1_sales`) nested_sales LIMIT 5",
            "SELECT",
        ),
    ],
)
def test_safe_select_cte_and_nested_queries_pass(client, sql, expected_statement):
    headers, user_id = _auth_headers(client, f"safe-{abs(hash(sql))}@example.com")

    response, query_request_id, dataset_id = _validate_sql(
        client, headers, user_id, sql
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query_request_id"] == query_request_id
    assert payload["dataset_id"] == dataset_id
    assert payload["validation_status"] == "passed"
    assert payload["is_safe"] is True
    assert payload["statement_type"] == expected_statement
    assert payload["referenced_tables"] == [
        "test-project.queryshield_demo.dataset_1_sales"
    ]
    assert payload["errors"] == []
    assert payload["validated_at"] is not None


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM `test-project.queryshield_demo.dataset_1_sales` WHERE TRUE",
        "UPDATE `test-project.queryshield_demo.dataset_1_sales` SET region = 'West' WHERE TRUE",
        "INSERT INTO `test-project.queryshield_demo.dataset_1_sales` (region) VALUES ('West')",
        "DROP TABLE `test-project.queryshield_demo.dataset_1_sales`",
        "CREATE TABLE `test-project.queryshield_demo.new_table` AS SELECT 1",
        "MERGE `test-project.queryshield_demo.dataset_1_sales` T USING `test-project.queryshield_demo.dataset_1_sales` S ON FALSE WHEN NOT MATCHED THEN INSERT (region) VALUES ('West')",
    ],
)
def test_write_and_ddl_statements_fail_validation(client, sql):
    headers, user_id = _auth_headers(client, f"unsafe-{abs(hash(sql))}@example.com")

    response, _query_request_id, _dataset_id = _validate_sql(
        client, headers, user_id, sql
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["validation_status"] == "failed"
    assert payload["is_safe"] is False
    assert "Only read-only SELECT queries are allowed" in payload["errors"]


def test_multiple_statements_fail_validation(client):
    headers, user_id = _auth_headers(client, "validate-multistmt@example.com")
    sql = "SELECT * FROM `test-project.queryshield_demo.dataset_1_sales`; DROP TABLE `test-project.queryshield_demo.dataset_1_sales`"

    response, _query_request_id, _dataset_id = _validate_sql(
        client, headers, user_id, sql
    )

    assert response.status_code == 200
    assert response.json()["is_safe"] is False
    assert "Exactly one SQL statement is allowed" in response.json()["errors"]


def test_querying_another_table_fails_validation(client):
    headers, user_id = _auth_headers(client, "validate-wrong-table@example.com")
    sql = "SELECT * FROM `another-project.other_dataset.customers`"

    response, _query_request_id, _dataset_id = _validate_sql(
        client, headers, user_id, sql
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_safe"] is False
    assert any("unauthorized table" in error for error in payload["errors"])


def test_information_schema_fails_validation(client):
    headers, user_id = _auth_headers(client, "validate-information-schema@example.com")
    sql = "SELECT * FROM `test-project.queryshield_demo.INFORMATION_SCHEMA.TABLES`"

    response, _query_request_id, _dataset_id = _validate_sql(
        client, headers, user_id, sql
    )

    assert response.status_code == 200
    assert "INFORMATION_SCHEMA access is not allowed" in response.json()["errors"]


def test_wildcard_table_reference_fails_validation(client):
    headers, user_id = _auth_headers(client, "validate-wildcard@example.com")
    sql = "SELECT * FROM `test-project.queryshield_demo.events_*`"

    response, _query_request_id, _dataset_id = _validate_sql(
        client, headers, user_id, sql
    )

    assert response.status_code == 200
    assert "Wildcard table access is not allowed" in response.json()["errors"]


def test_select_without_selected_table_fails_validation(client):
    headers, user_id = _auth_headers(client, "validate-select-one@example.com")
    sql = "SELECT 1"

    response, _query_request_id, _dataset_id = _validate_sql(
        client, headers, user_id, sql
    )

    assert response.status_code == 200
    assert "SQL must reference the selected BigQuery table" in response.json()["errors"]


def test_select_star_returns_warning(client):
    headers, user_id = _auth_headers(client, "validate-star@example.com")
    sql = "SELECT * FROM `test-project.queryshield_demo.dataset_1_sales` LIMIT 10"

    response, _query_request_id, _dataset_id = _validate_sql(
        client, headers, user_id, sql
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_safe"] is True
    assert "SELECT * may scan unnecessary columns" in payload["warnings"]


def test_raw_query_without_limit_returns_warning(client):
    headers, user_id = _auth_headers(client, "validate-no-limit@example.com")
    sql = "SELECT region FROM `test-project.queryshield_demo.dataset_1_sales`"

    response, _query_request_id, _dataset_id = _validate_sql(
        client, headers, user_id, sql
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_safe"] is True
    assert (
        "Query may return many rows because no LIMIT is present" in payload["warnings"]
    )


def test_explicit_cross_join_fails_validation(client):
    headers, user_id = _auth_headers(client, "validate-cross-join@example.com")
    sql = "SELECT a.region FROM `test-project.queryshield_demo.dataset_1_sales` a CROSS JOIN `test-project.queryshield_demo.dataset_1_sales` b"

    response, _query_request_id, _dataset_id = _validate_sql(
        client, headers, user_id, sql
    )

    assert response.status_code == 200
    assert "Explicit CROSS JOIN is not allowed" in response.json()["errors"]


def test_parse_failure_returns_unsafe_validation_result(client):
    headers, user_id = _auth_headers(client, "validate-parse-failure@example.com")
    sql = "SELECT FROM"

    response, _query_request_id, _dataset_id = _validate_sql(
        client, headers, user_id, sql
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["validation_status"] == "failed"
    assert payload["is_safe"] is False
    assert payload["errors"] == ["SQL could not be parsed"]


def test_validation_result_is_stored_and_retrievable(client):
    headers, user_id = _auth_headers(client, "validate-stored@example.com")
    sql = "SELECT region FROM `test-project.queryshield_demo.dataset_1_sales` LIMIT 10"
    response, query_request_id, _dataset_id = _validate_sql(
        client, headers, user_id, sql
    )
    assert response.status_code == 200

    stored_response = client.get(
        f"/queries/{query_request_id}/validation", headers=headers
    )

    assert stored_response.status_code == 200
    payload = stored_response.json()
    assert payload["validation_status"] == "passed"
    assert payload["is_safe"] is True
    assert payload["referenced_tables"] == [
        "test-project.queryshield_demo.dataset_1_sales"
    ]
    stored = _stored_query_request(query_request_id)
    assert stored.validation_status == "passed"
    assert stored.is_safe is True
    assert stored.validated_at is not None


def test_failed_validation_status_is_stored(client):
    headers, user_id = _auth_headers(client, "validate-failed-stored@example.com")
    sql = "DELETE FROM `test-project.queryshield_demo.dataset_1_sales` WHERE TRUE"

    response, query_request_id, _dataset_id = _validate_sql(
        client, headers, user_id, sql
    )

    assert response.status_code == 200
    stored = _stored_query_request(query_request_id)
    assert stored.validation_status == "failed"
    assert stored.is_safe is False
    assert stored.validation_errors


def test_get_validation_before_validation_returns_400(client):
    headers, user_id = _auth_headers(client, "validate-before-get@example.com")
    dataset_id = _create_dataset_record(user_id)
    query_request_id = _create_query_request_record(user_id, dataset_id)

    response = client.get(f"/queries/{query_request_id}/validation", headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "Query request has not been validated"


def test_existing_step7_generation_response_includes_validation_summary(
    monkeypatch, client
):
    headers, user_id = _auth_headers(client, "step7-validation-summary@example.com")
    dataset_id = _create_dataset_record(user_id)
    monkeypatch.setattr(
        "app.services.query_generation_service.generate_bigquery_sql",
        lambda table_id, columns, question: f"SELECT region FROM `{table_id}` LIMIT 10",
    )

    response = client.post(
        "/queries/generate",
        json={"dataset_id": dataset_id, "question": "Show regions"},
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "generated"
    assert payload["validation_status"] == "not_validated"
    assert payload["is_safe"] is None


def test_validation_does_not_execute_sql_or_run_bigquery_dry_run(monkeypatch, client):
    headers, user_id = _auth_headers(client, "validate-no-execute@example.com")
    sql = "SELECT region FROM `test-project.queryshield_demo.dataset_1_sales` LIMIT 10"

    def fail_if_bigquery_client_is_requested(*args, **kwargs):
        raise AssertionError("BigQuery should not be called during SQL validation")

    monkeypatch.setattr(
        "app.services.bigquery_service.get_bigquery_client",
        fail_if_bigquery_client_is_requested,
    )
    response, _query_request_id, _dataset_id = _validate_sql(
        client, headers, user_id, sql
    )

    assert response.status_code == 200
    response_text = response.text.lower()
    assert "total_bytes" not in response_text
    assert "num_rows" not in response_text
    assert "dry" not in response_text


class _FakeDryRunResult:
    def __init__(self, total_bytes_processed, job_id="dry_job_1", location="US"):
        self.total_bytes_processed = total_bytes_processed
        self.job_id = job_id
        self.location = location


def _create_validated_query_request(
    user_id,
    dataset_id,
    *,
    sql="SELECT region FROM `test-project.queryshield_demo.dataset_1_sales` LIMIT 10",
    generation_status="generated",
    validation_status="passed",
    is_safe=True,
):
    query_request_id = _create_query_request_record(
        user_id, dataset_id, sql=sql, generation_status=generation_status
    )
    db = database.SessionLocal()
    try:
        query_request = (
            db.query(QueryRequest).filter(QueryRequest.id == query_request_id).first()
        )
        query_request.validation_status = validation_status
        query_request.is_safe = is_safe
        db.commit()
        return query_request_id
    finally:
        db.close()


def _dry_run_ready_query(
    client,
    email="dryrun@example.com",
    *,
    dataset_status="loaded",
    table_id="test-project.queryshield_demo.dataset_1_sales",
):
    headers, user_id = _auth_headers(client, email)
    dataset_id = _create_dataset_record(
        user_id, status=dataset_status, table_id=table_id
    )
    query_request_id = _create_validated_query_request(user_id, dataset_id)
    return headers, user_id, dataset_id, query_request_id


def test_unauthenticated_user_cannot_run_dry_run(client):
    headers, _user_id, _dataset_id, query_request_id = _dry_run_ready_query(
        client, "dryrun-auth@example.com"
    )

    response = client.post(f"/queries/{query_request_id}/dry-run")

    assert response.status_code == 401


def test_user_cannot_dry_run_another_users_query(client):
    _owner_headers, owner_id = _auth_headers(client, "dryrun-owner@example.com")
    other_headers, _other_id = _auth_headers(client, "dryrun-other@example.com")
    dataset_id = _create_dataset_record(owner_id)
    query_request_id = _create_validated_query_request(owner_id, dataset_id)

    response = client.post(
        f"/queries/{query_request_id}/dry-run", headers=other_headers
    )

    assert response.status_code == 404


def test_query_request_must_exist_for_dry_run(client):
    headers, _user_id = _auth_headers(client, "dryrun-missing@example.com")

    response = client.post("/queries/999999/dry-run", headers=headers)

    assert response.status_code == 404


def test_generated_sql_must_exist_for_dry_run(client):
    headers, user_id = _auth_headers(client, "dryrun-nosql@example.com")
    dataset_id = _create_dataset_record(user_id)
    query_request_id = _create_validated_query_request(user_id, dataset_id, sql=None)

    response = client.post(f"/queries/{query_request_id}/dry-run", headers=headers)

    assert response.status_code == 400
    assert "generated SQL" in response.json()["detail"]


def test_generation_status_must_be_generated_for_dry_run(client):
    headers, user_id = _auth_headers(client, "dryrun-generation-status@example.com")
    dataset_id = _create_dataset_record(user_id)
    query_request_id = _create_validated_query_request(
        user_id, dataset_id, generation_status="failed"
    )

    response = client.post(f"/queries/{query_request_id}/dry-run", headers=headers)

    assert response.status_code == 400
    assert "generation" in response.json()["detail"]


def test_validation_must_have_passed_for_dry_run(client):
    headers, user_id = _auth_headers(client, "dryrun-validation-status@example.com")
    dataset_id = _create_dataset_record(user_id)
    query_request_id = _create_validated_query_request(
        user_id, dataset_id, validation_status="failed", is_safe=False
    )

    response = client.post(f"/queries/{query_request_id}/dry-run", headers=headers)

    assert response.status_code == 409
    assert "SQL safety validation" in response.json()["detail"]


def test_is_safe_must_be_true_for_dry_run(client):
    headers, user_id = _auth_headers(client, "dryrun-unsafe@example.com")
    dataset_id = _create_dataset_record(user_id)
    query_request_id = _create_validated_query_request(
        user_id, dataset_id, validation_status="passed", is_safe=False
    )

    response = client.post(f"/queries/{query_request_id}/dry-run", headers=headers)

    assert response.status_code == 409


def test_dry_run_dataset_must_exist_and_be_owned(client):
    headers, user_id = _auth_headers(client, "dryrun-dataset-owner@example.com")
    _other_headers, other_id = _auth_headers(client, "dryrun-dataset-other@example.com")
    other_dataset_id = _create_dataset_record(other_id)
    query_request_id = _create_validated_query_request(user_id, other_dataset_id)

    response = client.post(f"/queries/{query_request_id}/dry-run", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Dataset not found"


def test_dataset_must_be_loaded_for_dry_run(client):
    headers, _user_id, _dataset_id, query_request_id = _dry_run_ready_query(
        client, "dryrun-unloaded@example.com", dataset_status="schema_detected"
    )

    response = client.post(f"/queries/{query_request_id}/dry-run", headers=headers)

    assert response.status_code == 400
    assert "loaded into BigQuery" in response.json()["detail"]


def test_dataset_must_have_bigquery_table_id_for_dry_run(client):
    headers, _user_id, _dataset_id, query_request_id = _dry_run_ready_query(
        client, "dryrun-notable@example.com", table_id=None
    )

    response = client.post(f"/queries/{query_request_id}/dry-run", headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "Dataset does not have a BigQuery table ID"


def test_successful_within_limit_dry_run_stores_estimate_and_execution_eligible(
    monkeypatch, client
):
    headers, _user_id, _dataset_id, query_request_id = _dry_run_ready_query(
        client, "dryrun-pass@example.com"
    )
    monkeypatch.setattr(
        "app.services.query_dry_run_service.run_query_dry_run",
        lambda sql: _FakeDryRunResult(52_428_800),
    )

    response = client.post(f"/queries/{query_request_id}/dry-run", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["dry_run_status"] == "passed"
    assert payload["dry_run_valid"] is True
    assert payload["estimated_bytes_processed"] == 52_428_800
    assert payload["estimated_mib_processed"] == 50.0
    assert payload["maximum_bytes_billed"] == 100_000_000
    assert payload["bytes_limit_exceeded"] is False
    assert payload["execution_eligible"] is True
    assert payload["dry_run_job_id"] == "dry_job_1"
    stored = _stored_query_request(query_request_id)
    assert stored.dry_run_status == "passed"
    assert stored.execution_eligible is True


def test_over_limit_dry_run_is_blocked(monkeypatch, client):
    headers, _user_id, _dataset_id, query_request_id = _dry_run_ready_query(
        client, "dryrun-blocked@example.com"
    )
    monkeypatch.setattr(
        "app.services.query_dry_run_service.run_query_dry_run",
        lambda sql: _FakeDryRunResult(500_000_000),
    )

    response = client.post(f"/queries/{query_request_id}/dry-run", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["dry_run_status"] == "blocked"
    assert payload["dry_run_valid"] is True
    assert payload["bytes_limit_exceeded"] is True
    assert payload["execution_eligible"] is False
    stored = _stored_query_request(query_request_id)
    assert stored.dry_run_status == "blocked"
    assert stored.execution_eligible is False


def test_invalid_bigquery_sql_sets_failed_status_and_sanitized_error(
    monkeypatch, client
):
    headers, _user_id, _dataset_id, query_request_id = _dry_run_ready_query(
        client, "dryrun-failed@example.com"
    )
    BadRequest = type("BadRequest", (Exception,), {})

    def raise_bad_request(sql):
        raise BadRequest(
            "Unrecognized name: secret_column at [1:8] credential=/private/key.json"
        )

    monkeypatch.setattr(
        "app.services.query_dry_run_service.run_query_dry_run", raise_bad_request
    )

    response = client.post(f"/queries/{query_request_id}/dry-run", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["dry_run_status"] == "failed"
    assert payload["dry_run_valid"] is False
    assert payload["execution_eligible"] is False
    assert (
        payload["dry_run_error"] == "The query references a field that does not exist."
    )
    assert "key.json" not in payload["dry_run_error"]


def test_credential_error_sets_error_status_and_sanitized_error(monkeypatch, client):
    headers, _user_id, _dataset_id, query_request_id = _dry_run_ready_query(
        client, "dryrun-error@example.com"
    )
    DefaultCredentialsError = type("DefaultCredentialsError", (Exception,), {})

    def raise_credentials(sql):
        raise DefaultCredentialsError(
            "Could not read credentials from C:/secret/service-account.json"
        )

    monkeypatch.setattr(
        "app.services.query_dry_run_service.run_query_dry_run", raise_credentials
    )

    response = client.post(f"/queries/{query_request_id}/dry-run", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["dry_run_status"] == "error"
    assert payload["dry_run_valid"] is False
    assert payload["execution_eligible"] is False
    assert (
        payload["dry_run_error"]
        == "Google Cloud credentials are not configured correctly."
    )


def test_estimated_cost_and_byte_conversions_are_correct(monkeypatch):
    from app.services.query_dry_run_service import (
        bytes_to_gib,
        bytes_to_mib,
        bytes_to_tib,
        calculate_estimated_cost,
    )

    assert bytes_to_mib(1024**2) == 1.0
    assert bytes_to_gib(1024**3) == 1.0
    assert bytes_to_tib(1024**4) == 1.0
    assert str(calculate_estimated_cost(1024**4)) == "6.250000"
    assert str(calculate_estimated_cost(0)) == "0.000000"


def test_rerun_replaces_latest_stored_dry_run(monkeypatch, client):
    headers, _user_id, _dataset_id, query_request_id = _dry_run_ready_query(
        client, "dryrun-rerun@example.com"
    )
    estimates = iter(
        [
            _FakeDryRunResult(500_000_000, "job_large"),
            _FakeDryRunResult(1_048_576, "job_small"),
        ]
    )
    monkeypatch.setattr(
        "app.services.query_dry_run_service.run_query_dry_run",
        lambda sql: next(estimates),
    )

    first = client.post(f"/queries/{query_request_id}/dry-run", headers=headers)
    second = client.post(f"/queries/{query_request_id}/dry-run", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    payload = second.json()
    assert payload["dry_run_status"] == "passed"
    assert payload["estimated_bytes_processed"] == 1_048_576
    assert payload["dry_run_job_id"] == "job_small"
    assert payload["execution_eligible"] is True


def test_stored_dry_run_endpoint_enforces_ownership(monkeypatch, client):
    owner_headers, owner_id, dataset_id, query_request_id = _dry_run_ready_query(
        client, "dryrun-get-owner@example.com"
    )
    other_headers, _other_id = _auth_headers(client, "dryrun-get-other@example.com")
    monkeypatch.setattr(
        "app.services.query_dry_run_service.run_query_dry_run",
        lambda sql: _FakeDryRunResult(1_048_576),
    )
    assert (
        client.post(
            f"/queries/{query_request_id}/dry-run", headers=owner_headers
        ).status_code
        == 200
    )

    response = client.get(f"/queries/{query_request_id}/dry-run", headers=other_headers)

    assert response.status_code == 404


def test_get_dry_run_before_run_returns_400(client):
    headers, _user_id, _dataset_id, query_request_id = _dry_run_ready_query(
        client, "dryrun-before-get@example.com"
    )

    response = client.get(f"/queries/{query_request_id}/dry-run", headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "Query dry run has not been run"


def test_dry_run_does_not_return_rows_or_create_execution_job(monkeypatch, client):
    headers, _user_id, _dataset_id, query_request_id = _dry_run_ready_query(
        client, "dryrun-no-execute@example.com"
    )
    observed = {}

    def fake_dry_run(sql):
        observed["sql"] = sql
        return _FakeDryRunResult(1_048_576)

    monkeypatch.setattr(
        "app.services.query_dry_run_service.run_query_dry_run", fake_dry_run
    )
    response = client.post(f"/queries/{query_request_id}/dry-run", headers=headers)

    assert response.status_code == 200
    assert observed["sql"].startswith("SELECT")
    response_text = response.text.lower()
    assert "rows" not in response_text
    assert "result" not in response_text
    assert "execute" not in response_text


def test_existing_generation_and_validation_still_work_after_dry_run_fields(
    monkeypatch, client
):
    headers, user_id = _auth_headers(client, "dryrun-existing-flow@example.com")
    dataset_id = _create_dataset_record(user_id)
    monkeypatch.setattr(
        "app.services.query_generation_service.generate_bigquery_sql",
        lambda table_id, columns, question: f"SELECT region FROM `{table_id}` LIMIT 10",
    )

    generate_response = client.post(
        "/queries/generate",
        json={"dataset_id": dataset_id, "question": "Show regions"},
        headers=headers,
    )
    assert generate_response.status_code == 200
    query_request_id = generate_response.json()["id"]
    validate_response = client.post(
        f"/queries/{query_request_id}/validate", headers=headers
    )

    assert validate_response.status_code == 200
    assert validate_response.json()["validation_status"] == "passed"
    assert generate_response.json()["dry_run_status"] == "not_run"


def _execution_ready_query(
    client,
    email="execute@example.com",
    *,
    dataset_status="loaded",
    table_id="test-project.queryshield_demo.dataset_1_sales",
    sql="SELECT region FROM `test-project.queryshield_demo.dataset_1_sales` LIMIT 10",
    generation_status="generated",
    validation_status="passed",
    is_safe=True,
    dry_run_status="passed",
    dry_run_valid=True,
    bytes_limit_exceeded=False,
    execution_eligible=True,
    estimated_bytes_processed=1_048_576,
):
    headers, user_id = _auth_headers(client, email)
    dataset_id = _create_dataset_record(
        user_id, status=dataset_status, table_id=table_id
    )
    query_request_id = _create_query_request_record(
        user_id, dataset_id, sql=sql, generation_status=generation_status
    )
    db = database.SessionLocal()
    try:
        query_request = (
            db.query(QueryRequest).filter(QueryRequest.id == query_request_id).first()
        )
        query_request.generated_for_table_id = table_id
        query_request.validation_status = validation_status
        query_request.is_safe = is_safe
        query_request.dry_run_status = dry_run_status
        query_request.dry_run_valid = dry_run_valid
        query_request.estimated_bytes_processed = estimated_bytes_processed
        query_request.maximum_bytes_billed = 100_000_000
        query_request.bytes_limit_exceeded = bytes_limit_exceeded
        query_request.execution_eligible = execution_eligible
        db.commit()
    finally:
        db.close()
    return headers, user_id, dataset_id, query_request_id


def _fake_execution_result(rows=None, *, truncated=False):
    return QueryExecutionResult(
        job_id="exec_job_1",
        location="US",
        total_bytes_processed=1_048_576,
        total_bytes_billed=1_048_576,
        cache_hit=False,
        columns=[
            QueryResultColumn(name="region", field_type="STRING", mode="NULLABLE"),
            QueryResultColumn(
                name="total_sales", field_type="NUMERIC", mode="NULLABLE"
            ),
        ],
        rows=rows
        if rows is not None
        else [{"region": "South", "total_sales": Decimal("1849.25")}],
        result_truncated=truncated,
    )


def test_unauthenticated_user_cannot_execute_query(client):
    headers, _user_id, _dataset_id, query_request_id = _execution_ready_query(
        client, "execute-auth@example.com"
    )

    response = client.post(f"/queries/{query_request_id}/execute")

    assert response.status_code == 401


def test_user_cannot_execute_another_users_query(client):
    _owner_headers, owner_id = _auth_headers(client, "execute-owner@example.com")
    other_headers, _other_id = _auth_headers(client, "execute-other@example.com")
    dataset_id = _create_dataset_record(owner_id)
    query_request_id = _create_query_request_record(owner_id, dataset_id)

    response = client.post(
        f"/queries/{query_request_id}/execute", headers=other_headers
    )

    assert response.status_code == 404


def test_execute_query_request_must_exist(client):
    headers, _user_id = _auth_headers(client, "execute-missing@example.com")

    response = client.post("/queries/999999/execute", headers=headers)

    assert response.status_code == 404


@pytest.mark.parametrize(
    ("field", "value", "expected_detail"),
    [
        ("generated_sql", None, "generated SQL"),
        ("generation_status", "failed", "generation"),
        ("validation_status", "failed", "SQL safety validation"),
        ("is_safe", False, "marked safe"),
        ("dry_run_status", "failed", "dry run"),
        ("dry_run_valid", False, "dry run"),
        ("bytes_limit_exceeded", True, "estimated bytes"),
        ("execution_eligible", False, "not eligible"),
        ("estimated_bytes_processed", None, "estimated bytes"),
    ],
)
def test_execute_requires_all_pre_execution_gates(
    client, field, value, expected_detail
):
    headers, _user_id, _dataset_id, query_request_id = _execution_ready_query(
        client, f"execute-gate-{field}@example.com"
    )
    db = database.SessionLocal()
    try:
        query_request = (
            db.query(QueryRequest).filter(QueryRequest.id == query_request_id).first()
        )
        setattr(query_request, field, value)
        db.commit()
    finally:
        db.close()

    response = client.post(f"/queries/{query_request_id}/execute", headers=headers)

    assert response.status_code == 409
    assert expected_detail in response.json()["detail"]
    stored = _stored_query_request(query_request_id)
    assert stored.execution_status == "blocked"


def test_execute_requires_dataset_to_still_belong_to_user(client):
    headers, user_id, dataset_id, query_request_id = _execution_ready_query(
        client, "execute-dataset-owner@example.com"
    )
    _other_headers, other_id = _auth_headers(
        client, "execute-dataset-other@example.com"
    )
    db = database.SessionLocal()
    try:
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        dataset.owner_id = other_id
        db.commit()
    finally:
        db.close()

    response = client.post(f"/queries/{query_request_id}/execute", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Dataset not found"


def test_execute_requires_dataset_still_loaded(client):
    headers, _user_id, _dataset_id, query_request_id = _execution_ready_query(
        client, "execute-unloaded@example.com", dataset_status="schema_detected"
    )

    response = client.post(f"/queries/{query_request_id}/execute", headers=headers)

    assert response.status_code == 409
    assert "loaded into BigQuery" in response.json()["detail"]


def test_execute_blocks_stale_table_context(client):
    headers, _user_id, dataset_id, query_request_id = _execution_ready_query(
        client, "execute-stale@example.com"
    )
    db = database.SessionLocal()
    try:
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        dataset.bigquery_table_id = "test-project.queryshield_demo.reloaded_table"
        db.commit()
    finally:
        db.close()

    response = client.post(f"/queries/{query_request_id}/execute", headers=headers)

    assert response.status_code == 409
    assert "changed after generation" in response.json()["detail"]
    assert _stored_query_request(query_request_id).execution_eligible is False


def test_execute_revalidates_stored_sql_before_bigquery(monkeypatch, client):
    headers, _user_id, _dataset_id, query_request_id = _execution_ready_query(
        client,
        "execute-revalidate@example.com",
        sql="SELECT * FROM `another-project.other_dataset.customers`",
    )
    called = {"bigquery": False}

    def fake_execute(*args, **kwargs):
        called["bigquery"] = True
        return _fake_execution_result()

    monkeypatch.setattr(
        "app.services.query_execution_service.execute_query", fake_execute
    )

    response = client.post(f"/queries/{query_request_id}/execute", headers=headers)

    assert response.status_code == 409
    assert "execution-time validation" in response.json()["detail"]
    assert called["bigquery"] is False


def test_execute_revalidation_internal_error_is_sanitized_and_audited(
    monkeypatch, client
):
    headers, user_id, _dataset_id, query_request_id = _execution_ready_query(
        client, "execute-revalidation-error@example.com"
    )
    called = {"bigquery": False}

    def fail_validation(*args, **kwargs):
        raise SQLValidatorInternalError("sqlglot path C:/secret/internal.txt")

    def fake_execute(*args, **kwargs):
        called["bigquery"] = True
        return _fake_execution_result()

    monkeypatch.setattr(
        "app.services.query_execution_service.validate_generated_sql", fail_validation
    )
    monkeypatch.setattr(
        "app.services.query_execution_service.execute_query", fake_execute
    )

    response = client.post(f"/queries/{query_request_id}/execute", headers=headers)

    assert response.status_code == 503
    assert (
        response.json()["detail"]
        == "Stored SQL could not be revalidated before execution"
    )
    assert called["bigquery"] is False

    stored = _stored_query_request(query_request_id)
    assert stored.execution_status == "blocked"
    assert (
        stored.execution_error == "Stored SQL could not be revalidated before execution"
    )
    assert stored.execution_eligible is False

    db = database.SessionLocal()
    try:
        actions = [
            log.action
            for log in db.query(AuditLog)
            .filter(
                AuditLog.user_id == user_id,
                AuditLog.resource_id == str(query_request_id),
            )
            .all()
        ]
    finally:
        db.close()
    assert "query.execution_revalidation_error" in actions


def test_execute_rejects_raw_sql_body(client):
    headers, _user_id, _dataset_id, query_request_id = _execution_ready_query(
        client, "execute-rawsql@example.com"
    )

    response = client.post(
        f"/queries/{query_request_id}/execute",
        headers=headers,
        json={"sql": "SELECT secret FROM `other.table`", "row_limit": 1},
    )

    assert response.status_code == 422


def test_successful_execution_stores_metadata_bounded_rows_and_json_safe_values(
    monkeypatch, client
):
    headers, _user_id, _dataset_id, query_request_id = _execution_ready_query(
        client, "execute-success@example.com"
    )
    observed = {}

    def fake_execute(sql, maximum_bytes_billed, row_limit, timeout_seconds):
        observed.update(
            {
                "sql": sql,
                "maximum_bytes_billed": maximum_bytes_billed,
                "row_limit": row_limit,
                "timeout_seconds": timeout_seconds,
            }
        )
        return _fake_execution_result(
            rows=[
                {
                    "region": "South",
                    "total_sales": Decimal("1849.25"),
                    "day": date(2026, 7, 10),
                    "nested": {"count": Decimal("2")},
                },
                {
                    "region": "East",
                    "total_sales": Decimal("1300.50"),
                    "day": datetime(2026, 7, 10, 12, 0, 0),
                    "nested": [Decimal("3")],
                },
            ],
            truncated=True,
        )

    monkeypatch.setattr(
        "app.services.query_execution_service.execute_query", fake_execute
    )

    response = client.post(
        f"/queries/{query_request_id}/execute", headers=headers, json={"row_limit": 2}
    )

    assert response.status_code == 200
    payload = response.json()
    assert observed["sql"].startswith("SELECT")
    assert observed["maximum_bytes_billed"] == 100_000_000
    assert observed["row_limit"] == 2
    assert observed["timeout_seconds"] == 30
    assert payload["execution_status"] == "succeeded"
    assert payload["execution_job_id"] == "exec_job_1"
    assert payload["execution_bytes_processed"] == 1_048_576
    assert payload["execution_bytes_billed"] == 1_048_576
    assert payload["execution_cache_hit"] is False
    assert payload["result_row_count"] == 2
    assert payload["result_truncated"] is True
    assert payload["result_rows"][0]["total_sales"] == "1849.25"
    assert payload["result_rows"][0]["day"] == "2026-07-10"
    assert payload["result_rows"][0]["nested"]["count"] == "2"
    stored = _stored_query_request(query_request_id)
    assert stored.execution_status == "succeeded"
    assert stored.result_row_count == 2


def test_successful_execution_generates_and_stores_ai_summary(monkeypatch, client):
    monkeypatch.setattr(
        "app.services.query_execution_service.settings.AI_SUMMARY_ENABLED", True
    )
    headers, user_id, _dataset_id, query_request_id = _execution_ready_query(
        client, "execute-summary@example.com"
    )
    observed = {}

    monkeypatch.setattr(
        "app.services.query_execution_service.execute_query",
        lambda *args, **kwargs: _fake_execution_result(),
    )

    def fake_summary(question, generated_sql, rows, columns=None, row_count=None):
        observed["question"] = question
        observed["rows"] = rows
        observed["columns"] = columns
        observed["row_count"] = row_count
        return "South has the highest returned sales total at 1849.25."

    monkeypatch.setattr(
        "app.services.query_execution_service.generate_result_summary", fake_summary
    )

    response = client.post(f"/queries/{query_request_id}/execute", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["execution_status"] == "succeeded"
    assert payload["ai_summary_status"] == "completed"
    assert (
        payload["ai_summary"]
        == "South has the highest returned sales total at 1849.25."
    )
    assert payload["ai_summary_error"] is None
    assert observed["rows"] == [{"region": "South", "total_sales": "1849.25"}]
    assert observed["columns"] == ["region", "total_sales"]
    assert observed["row_count"] == 1

    stored = _stored_query_request(query_request_id)
    assert stored.ai_summary_status == "completed"
    assert stored.ai_summary == payload["ai_summary"]
    assert stored.ai_summary_generated_at is not None

    db = database.SessionLocal()
    try:
        actions = [
            log.action
            for log in db.query(AuditLog)
            .filter(
                AuditLog.user_id == user_id,
                AuditLog.resource_id == str(query_request_id),
            )
            .all()
        ]
    finally:
        db.close()
    assert "query.ai_summary_started" in actions
    assert "query.ai_summary_completed" in actions


def test_empty_execution_rows_use_deterministic_ai_summary_without_gemini(
    monkeypatch, client
):
    monkeypatch.setattr(
        "app.services.query_execution_service.settings.AI_SUMMARY_ENABLED", True
    )
    headers, _user_id, _dataset_id, query_request_id = _execution_ready_query(
        client, "execute-empty-summary@example.com"
    )
    monkeypatch.setattr(
        "app.services.query_execution_service.execute_query",
        lambda *args, **kwargs: _fake_execution_result(rows=[]),
    )

    response = client.post(f"/queries/{query_request_id}/execute", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["execution_status"] == "succeeded"
    assert payload["result_rows"] == []
    assert payload["ai_summary_status"] == "completed"
    assert payload["ai_summary"] == EMPTY_RESULT_SUMMARY


def test_ai_summary_failure_does_not_fail_query_execution(monkeypatch, client):
    monkeypatch.setattr(
        "app.services.query_execution_service.settings.AI_SUMMARY_ENABLED", True
    )
    headers, user_id, _dataset_id, query_request_id = _execution_ready_query(
        client, "execute-summary-fail@example.com"
    )
    monkeypatch.setattr(
        "app.services.query_execution_service.execute_query",
        lambda *args, **kwargs: _fake_execution_result(),
    )

    def fail_summary(*args, **kwargs):
        raise ResultSummaryError("Gemini API key leaked path C:/secret/key.json")

    monkeypatch.setattr(
        "app.services.query_execution_service.generate_result_summary", fail_summary
    )

    response = client.post(f"/queries/{query_request_id}/execute", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["execution_status"] == "succeeded"
    assert payload["result_rows"] == [{"region": "South", "total_sales": "1849.25"}]
    assert payload["ai_summary"] is None
    assert payload["ai_summary_status"] == "failed"
    assert payload["ai_summary_error"] == "AI summary is not configured."
    assert "key.json" not in payload["ai_summary_error"]

    db = database.SessionLocal()
    try:
        actions = [
            log.action
            for log in db.query(AuditLog)
            .filter(
                AuditLog.user_id == user_id,
                AuditLog.resource_id == str(query_request_id),
            )
            .all()
        ]
    finally:
        db.close()
    assert "query.ai_summary_failed" in actions


def test_requested_row_limit_cannot_exceed_server_max(monkeypatch, client):
    headers, _user_id, _dataset_id, query_request_id = _execution_ready_query(
        client, "execute-rowlimit@example.com"
    )
    monkeypatch.setattr(
        "app.services.query_execution_service.settings.QUERY_RESULT_ROW_LIMIT", 5
    )

    response = client.post(
        f"/queries/{query_request_id}/execute", headers=headers, json={"row_limit": 6}
    )

    assert response.status_code == 400
    assert "row limit" in response.json()["detail"]


def test_bigquery_failure_sets_failed_status_and_sanitized_error(monkeypatch, client):
    headers, _user_id, _dataset_id, query_request_id = _execution_ready_query(
        client, "execute-failed@example.com"
    )
    BadRequest = type("BadRequest", (Exception,), {})

    def fail_execute(*args, **kwargs):
        raise BadRequest(
            "Exceeded maximum bytes billed with credential path C:/secret/key.json"
        )

    monkeypatch.setattr(
        "app.services.query_execution_service.execute_query", fail_execute
    )

    response = client.post(f"/queries/{query_request_id}/execute", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["execution_status"] == "failed"
    assert (
        payload["execution_error"]
        == "The query exceeded the configured maximum bytes billed."
    )
    assert "key.json" not in payload["execution_error"]


def test_timeout_sets_timed_out_status(monkeypatch, client):
    headers, _user_id, _dataset_id, query_request_id = _execution_ready_query(
        client, "execute-timeout@example.com"
    )

    def timeout_execute(*args, **kwargs):
        raise BigQueryExecutionTimeout("timeout", job_id="timeout_job")

    monkeypatch.setattr(
        "app.services.query_execution_service.execute_query", timeout_execute
    )

    response = client.post(f"/queries/{query_request_id}/execute", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["execution_status"] == "timed_out"
    assert payload["execution_job_id"] == "timeout_job"
    assert payload["execution_error"] == "The query timed out before completion."


def test_internal_credential_error_sets_error_status(monkeypatch, client):
    headers, _user_id, _dataset_id, query_request_id = _execution_ready_query(
        client, "execute-error@example.com"
    )
    DefaultCredentialsError = type("DefaultCredentialsError", (Exception,), {})

    def credential_error(*args, **kwargs):
        raise DefaultCredentialsError("service account path C:/secret/key.json")

    monkeypatch.setattr(
        "app.services.query_execution_service.execute_query", credential_error
    )

    response = client.post(f"/queries/{query_request_id}/execute", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["execution_status"] == "error"
    assert (
        payload["execution_error"]
        == "Google Cloud credentials are not configured correctly."
    )


def test_stored_execution_endpoint_enforces_ownership(monkeypatch, client):
    owner_headers, _user_id, _dataset_id, query_request_id = _execution_ready_query(
        client, "execute-get-owner@example.com"
    )
    other_headers, _other_id = _auth_headers(client, "execute-get-other@example.com")
    monkeypatch.setattr(
        "app.services.query_execution_service.execute_query",
        lambda *args, **kwargs: _fake_execution_result(),
    )
    assert (
        client.post(
            f"/queries/{query_request_id}/execute", headers=owner_headers
        ).status_code
        == 200
    )

    response = client.get(
        f"/queries/{query_request_id}/execution", headers=other_headers
    )

    assert response.status_code == 404


def test_get_execution_before_run_returns_400(client):
    headers, _user_id, _dataset_id, query_request_id = _execution_ready_query(
        client, "execute-before-get@example.com"
    )

    response = client.get(f"/queries/{query_request_id}/execution", headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "Query has not been executed"


def test_stored_execution_returns_bounded_rows(monkeypatch, client):
    headers, _user_id, _dataset_id, query_request_id = _execution_ready_query(
        client, "execute-get@example.com"
    )
    monkeypatch.setattr(
        "app.services.query_execution_service.execute_query",
        lambda *args, **kwargs: _fake_execution_result(),
    )
    assert (
        client.post(f"/queries/{query_request_id}/execute", headers=headers).status_code
        == 200
    )

    response = client.get(f"/queries/{query_request_id}/execution", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["execution_status"] == "succeeded"
    assert payload["result_rows"] == [{"region": "South", "total_sales": "1849.25"}]


def _set_query_history_state(query_request_id, **values):
    db = database.SessionLocal()
    try:
        query_request = (
            db.query(QueryRequest).filter(QueryRequest.id == query_request_id).first()
        )
        for key, value in values.items():
            setattr(query_request, key, value)
        db.commit()
    finally:
        db.close()


def _create_history_query(
    user_id,
    dataset_id,
    *,
    question="Total sales by region?",
    sql=None,
    created_at=None,
    **state,
):
    query_request_id = _create_query_request_record(
        user_id,
        dataset_id,
        sql=sql
        or "SELECT region FROM `test-project.queryshield_demo.dataset_1_sales` LIMIT 10",
    )
    defaults = {
        "validation_status": "passed",
        "is_safe": True,
        "dry_run_status": "passed",
        "dry_run_valid": True,
        "estimated_bytes_processed": 1_048_576,
        "maximum_bytes_billed": 100_000_000,
        "estimated_cost": Decimal("0.000006"),
        "estimated_cost_currency": "USD",
        "bytes_limit_exceeded": False,
        "execution_eligible": True,
        "execution_status": "succeeded",
        "result_row_count": 1,
        "result_columns": [
            {"name": "region", "field_type": "STRING", "mode": "NULLABLE"}
        ],
        "result_rows": [{"region": "South"}],
        "result_truncated": False,
    }
    defaults.update(state)
    if created_at is not None:
        defaults["created_at"] = created_at
    db = database.SessionLocal()
    try:
        query_request = (
            db.query(QueryRequest).filter(QueryRequest.id == query_request_id).first()
        )
        query_request.natural_language_question = question
        for key, value in defaults.items():
            setattr(query_request, key, value)
        db.commit()
    finally:
        db.close()
    return query_request_id


def _add_audit(
    user_id,
    action,
    *,
    resource_type="query_request",
    resource_id="1",
    details=None,
    created_at=None,
):
    db = database.SessionLocal()
    try:
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            details=details or {},
        )
        if created_at is not None:
            audit_log.created_at = created_at
        db.add(audit_log)
        db.commit()
        return audit_log.id
    finally:
        db.close()


def test_unauthenticated_user_cannot_access_query_history(client):
    response = client.get("/queries")

    assert response.status_code == 401


def test_query_history_filters_paginates_and_excludes_rows(client):
    headers, user_id = _auth_headers(client, "history-owner@example.com")
    other_headers, other_id = _auth_headers(client, "history-other@example.com")
    dataset_id = _create_dataset_record(user_id)
    other_dataset_id = _create_dataset_record(
        other_id, table_id="test-project.queryshield_demo.other_history"
    )
    older = datetime(2026, 7, 9, 12, 0, 0)
    newer = datetime(2026, 7, 10, 12, 0, 0)
    first_id = _create_history_query(
        user_id,
        dataset_id,
        question="Total sales by region",
        created_at=older,
        execution_status="failed",
    )
    second_id = _create_history_query(
        user_id,
        dataset_id,
        question="Average sales by market",
        created_at=newer,
        execution_status="succeeded",
    )
    _create_history_query(other_id, other_dataset_id, question="Other user query")

    response = client.get("/queries?limit=1", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["has_more"] is True
    assert payload["items"][0]["id"] == second_id
    assert "result_rows" not in payload["items"][0]
    assert payload["items"][0]["generated_sql_preview"].startswith("SELECT")

    response = client.get("/queries?skip=1&limit=1", headers=headers)
    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == first_id

    filters = [
        "dataset_id=" + str(dataset_id),
        "generation_status=generated",
        "validation_status=passed",
        "dry_run_status=passed",
        "execution_status=succeeded",
        "is_safe=true",
        "execution_eligible=true",
        "search=Average",
        "created_from=2026-07-10T00:00:00",
        "created_to=2026-07-10T23:59:59",
    ]
    response = client.get("/queries?" + "&".join(filters), headers=headers)
    assert response.status_code == 200
    filtered = response.json()
    assert filtered["total"] == 1
    assert filtered["items"][0]["id"] == second_id

    assert (
        client.get("/queries?execution_status=unknown", headers=headers).status_code
        == 400
    )
    capped = client.get("/queries?limit=500", headers=headers)
    assert capped.status_code == 200
    assert capped.json()["limit"] == 100


def test_query_lifecycle_returns_full_owned_read_only_record(monkeypatch, client):
    headers, user_id = _auth_headers(client, "history-detail@example.com")
    dataset_id = _create_dataset_record(user_id)
    query_request_id = _create_history_query(user_id, dataset_id)
    _add_audit(
        user_id,
        "query.execution_succeeded",
        resource_id=query_request_id,
        details={"result_row_count": 1},
    )

    def fail_if_execution_called(*args, **kwargs):
        raise AssertionError("History detail must not execute queries")

    monkeypatch.setattr(
        "app.services.query_execution_service.execute_query", fail_if_execution_called
    )
    response = client.get(f"/queries/{query_request_id}", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"]["id"] == query_request_id
    assert payload["query"]["dataset_name"] == "Sales Data"
    assert payload["generation"]["generated_sql"].startswith("SELECT")
    assert payload["validation"]["status"] == "passed"
    assert payload["dry_run"]["estimated_bytes_processed"] == 1_048_576
    assert payload["execution"]["status"] == "succeeded"
    assert payload["execution"]["result_rows"] == [{"region": "South"}]
    assert payload["audit_summary"]["total_events"] == 1


def test_query_lifecycle_enforces_ownership(client):
    _owner_headers, owner_id = _auth_headers(client, "history-detail-owner@example.com")
    other_headers, _other_id = _auth_headers(client, "history-detail-other@example.com")
    dataset_id = _create_dataset_record(owner_id)
    query_request_id = _create_history_query(owner_id, dataset_id)

    response = client.get(f"/queries/{query_request_id}", headers=other_headers)

    assert response.status_code == 404


def test_audit_list_enforces_ownership_and_filters(client):
    headers, user_id = _auth_headers(client, "audit-owner@example.com")
    _other_headers, other_id = _auth_headers(client, "audit-other@example.com")
    _add_audit(
        user_id,
        "query.execution_succeeded",
        resource_id="12",
        details={"result_row_count": 4},
        created_at=datetime(2026, 7, 10, 12, 0, 0),
    )
    _add_audit(
        user_id,
        "query.validation_failed",
        resource_id="13",
        details={"error_count": 1},
        created_at=datetime(2026, 7, 10, 11, 0, 0),
    )
    _add_audit(
        other_id,
        "query.execution_succeeded",
        resource_id="99",
        details={"result_row_count": 1},
    )

    response = client.get(
        "/audit-logs?action=query.execution_succeeded&resource_type=query_request&resource_id=12",
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["resource_id"] == "12"
    assert payload["items"][0]["details"] == {"result_row_count": 4}

    asc_response = client.get("/audit-logs?sort_order=asc", headers=headers)
    assert asc_response.status_code == 200
    actions = [item["action"] for item in asc_response.json()["items"]]
    assert "query.validation_failed" in actions
    assert "query.execution_succeeded" in actions
    assert all(item["resource_id"] != "99" for item in asc_response.json()["items"])

    assert client.get("/audit-logs?limit=500", headers=headers).json()["limit"] == 100
    assert (
        client.get("/audit-logs?sort_order=sideways", headers=headers).status_code
        == 400
    )


def test_query_audit_timeline_enforces_ownership_and_chronological_order(client):
    owner_headers, owner_id = _auth_headers(client, "audit-query-owner@example.com")
    other_headers, _other_id = _auth_headers(client, "audit-query-other@example.com")
    dataset_id = _create_dataset_record(owner_id)
    query_request_id = _create_history_query(owner_id, dataset_id)
    _add_audit(
        owner_id,
        "query.execution_succeeded",
        resource_id=query_request_id,
        created_at=datetime(2026, 7, 10, 12, 0, 2),
    )
    _add_audit(
        owner_id,
        "query.execution_started",
        resource_id=query_request_id,
        created_at=datetime(2026, 7, 10, 12, 0, 1),
    )

    response = client.get(
        f"/queries/{query_request_id}/audit-logs", headers=owner_headers
    )
    assert response.status_code == 200
    actions = [item["action"] for item in response.json()["items"]]
    assert actions == ["query.execution_started", "query.execution_succeeded"]

    forbidden = client.get(
        f"/queries/{query_request_id}/audit-logs", headers=other_headers
    )
    assert forbidden.status_code == 404


def test_audit_service_sanitizes_sensitive_details(client):
    from app.services.audit_service import create_audit_log

    headers, user_id = _auth_headers(client, "audit-sanitize@example.com")
    db = database.SessionLocal()
    try:
        create_audit_log(
            db,
            user_id,
            "query.execution_failed",
            "query_request",
            "123",
            {
                "password": "password123",
                "jwt_token": "secret-token",
                "GEMINI_API_KEY": "secret-key",
                "safe_status": "failed",
                "nested": {"credentials_path": "C:/secret/key.json", "count": 1},
            },
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/audit-logs?action=query.execution_failed", headers=headers)

    assert response.status_code == 200
    details = response.json()["items"][0]["details"]
    assert details == {"safe_status": "failed", "nested": {"count": 1}}
    assert "password123" not in response.text
    assert "secret-token" not in response.text
    assert "secret-key" not in response.text
