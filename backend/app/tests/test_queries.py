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
        return db.query(QueryRequest).filter(QueryRequest.id == query_request_id).first()
    finally:
        db.close()


def _validate_sql(client, headers, user_id, sql, *, table_id="test-project.queryshield_demo.dataset_1_sales"):
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

    response = client.post(f"/queries/{query_request_id}/validate", headers=other_headers)

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
    _other_headers, other_id = _auth_headers(client, "validate-dataset-other@example.com")
    other_dataset_id = _create_dataset_record(other_id)
    query_request_id = _create_query_request_record(user_id, other_dataset_id)

    response = client.post(f"/queries/{query_request_id}/validate", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Dataset not found"


@pytest.mark.parametrize(
    ("sql", "expected_statement"),
    [
        ("SELECT region FROM `test-project.queryshield_demo.dataset_1_sales` LIMIT 10", "SELECT"),
        ("WITH regional_sales AS (SELECT region, SUM(total_amount) AS total_sales FROM `test-project.queryshield_demo.dataset_1_sales` GROUP BY region) SELECT region, total_sales FROM regional_sales", "SELECT"),
        ("WITH regional_sales AS (SELECT region FROM `test-project.queryshield_demo.dataset_1_sales`) SELECT * FROM regional_sales", "SELECT"),
        ("SELECT region FROM (SELECT region FROM `test-project.queryshield_demo.dataset_1_sales`) nested_sales LIMIT 5", "SELECT"),
    ],
)
def test_safe_select_cte_and_nested_queries_pass(client, sql, expected_statement):
    headers, user_id = _auth_headers(client, f"safe-{abs(hash(sql))}@example.com")

    response, query_request_id, dataset_id = _validate_sql(client, headers, user_id, sql)

    assert response.status_code == 200
    payload = response.json()
    assert payload["query_request_id"] == query_request_id
    assert payload["dataset_id"] == dataset_id
    assert payload["validation_status"] == "passed"
    assert payload["is_safe"] is True
    assert payload["statement_type"] == expected_statement
    assert payload["referenced_tables"] == ["test-project.queryshield_demo.dataset_1_sales"]
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

    response, _query_request_id, _dataset_id = _validate_sql(client, headers, user_id, sql)

    assert response.status_code == 200
    payload = response.json()
    assert payload["validation_status"] == "failed"
    assert payload["is_safe"] is False
    assert "Only read-only SELECT queries are allowed" in payload["errors"]


def test_multiple_statements_fail_validation(client):
    headers, user_id = _auth_headers(client, "validate-multistmt@example.com")
    sql = "SELECT * FROM `test-project.queryshield_demo.dataset_1_sales`; DROP TABLE `test-project.queryshield_demo.dataset_1_sales`"

    response, _query_request_id, _dataset_id = _validate_sql(client, headers, user_id, sql)

    assert response.status_code == 200
    assert response.json()["is_safe"] is False
    assert "Exactly one SQL statement is allowed" in response.json()["errors"]


def test_querying_another_table_fails_validation(client):
    headers, user_id = _auth_headers(client, "validate-wrong-table@example.com")
    sql = "SELECT * FROM `another-project.other_dataset.customers`"

    response, _query_request_id, _dataset_id = _validate_sql(client, headers, user_id, sql)

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_safe"] is False
    assert any("unauthorized table" in error for error in payload["errors"])


def test_information_schema_fails_validation(client):
    headers, user_id = _auth_headers(client, "validate-information-schema@example.com")
    sql = "SELECT * FROM `test-project.queryshield_demo.INFORMATION_SCHEMA.TABLES`"

    response, _query_request_id, _dataset_id = _validate_sql(client, headers, user_id, sql)

    assert response.status_code == 200
    assert "INFORMATION_SCHEMA access is not allowed" in response.json()["errors"]


def test_wildcard_table_reference_fails_validation(client):
    headers, user_id = _auth_headers(client, "validate-wildcard@example.com")
    sql = "SELECT * FROM `test-project.queryshield_demo.events_*`"

    response, _query_request_id, _dataset_id = _validate_sql(client, headers, user_id, sql)

    assert response.status_code == 200
    assert "Wildcard table access is not allowed" in response.json()["errors"]


def test_select_without_selected_table_fails_validation(client):
    headers, user_id = _auth_headers(client, "validate-select-one@example.com")
    sql = "SELECT 1"

    response, _query_request_id, _dataset_id = _validate_sql(client, headers, user_id, sql)

    assert response.status_code == 200
    assert "SQL must reference the selected BigQuery table" in response.json()["errors"]


def test_select_star_returns_warning(client):
    headers, user_id = _auth_headers(client, "validate-star@example.com")
    sql = "SELECT * FROM `test-project.queryshield_demo.dataset_1_sales` LIMIT 10"

    response, _query_request_id, _dataset_id = _validate_sql(client, headers, user_id, sql)

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_safe"] is True
    assert "SELECT * may scan unnecessary columns" in payload["warnings"]


def test_raw_query_without_limit_returns_warning(client):
    headers, user_id = _auth_headers(client, "validate-no-limit@example.com")
    sql = "SELECT region FROM `test-project.queryshield_demo.dataset_1_sales`"

    response, _query_request_id, _dataset_id = _validate_sql(client, headers, user_id, sql)

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_safe"] is True
    assert "Query may return many rows because no LIMIT is present" in payload["warnings"]


def test_explicit_cross_join_fails_validation(client):
    headers, user_id = _auth_headers(client, "validate-cross-join@example.com")
    sql = "SELECT a.region FROM `test-project.queryshield_demo.dataset_1_sales` a CROSS JOIN `test-project.queryshield_demo.dataset_1_sales` b"

    response, _query_request_id, _dataset_id = _validate_sql(client, headers, user_id, sql)

    assert response.status_code == 200
    assert "Explicit CROSS JOIN is not allowed" in response.json()["errors"]


def test_parse_failure_returns_unsafe_validation_result(client):
    headers, user_id = _auth_headers(client, "validate-parse-failure@example.com")
    sql = "SELECT FROM"

    response, _query_request_id, _dataset_id = _validate_sql(client, headers, user_id, sql)

    assert response.status_code == 200
    payload = response.json()
    assert payload["validation_status"] == "failed"
    assert payload["is_safe"] is False
    assert payload["errors"] == ["SQL could not be parsed"]


def test_validation_result_is_stored_and_retrievable(client):
    headers, user_id = _auth_headers(client, "validate-stored@example.com")
    sql = "SELECT region FROM `test-project.queryshield_demo.dataset_1_sales` LIMIT 10"
    response, query_request_id, _dataset_id = _validate_sql(client, headers, user_id, sql)
    assert response.status_code == 200

    stored_response = client.get(f"/queries/{query_request_id}/validation", headers=headers)

    assert stored_response.status_code == 200
    payload = stored_response.json()
    assert payload["validation_status"] == "passed"
    assert payload["is_safe"] is True
    assert payload["referenced_tables"] == ["test-project.queryshield_demo.dataset_1_sales"]
    stored = _stored_query_request(query_request_id)
    assert stored.validation_status == "passed"
    assert stored.is_safe is True
    assert stored.validated_at is not None


def test_failed_validation_status_is_stored(client):
    headers, user_id = _auth_headers(client, "validate-failed-stored@example.com")
    sql = "DELETE FROM `test-project.queryshield_demo.dataset_1_sales` WHERE TRUE"

    response, query_request_id, _dataset_id = _validate_sql(client, headers, user_id, sql)

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


def test_existing_step7_generation_response_includes_validation_summary(monkeypatch, client):
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

    monkeypatch.setattr("app.services.bigquery_service.get_bigquery_client", fail_if_bigquery_client_is_requested)
    response, _query_request_id, _dataset_id = _validate_sql(client, headers, user_id, sql)

    assert response.status_code == 200
    response_text = response.text.lower()
    assert "total_bytes" not in response_text
    assert "num_rows" not in response_text
    assert "dry" not in response_text
