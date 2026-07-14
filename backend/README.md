# QueryShield AI Backend

FastAPI backend for QueryShield AI. It owns authentication, dataset records, CSV processing, BigQuery loading, Gemini SQL generation, SQL validation, dry-run cost checks, controlled execution, query history, and audit logs.

## Responsibilities

- Authenticate users with JWT access tokens.
- Enforce dataset and query ownership.
- Store dataset metadata, detected columns, query lifecycle records, and audit logs.
- Save uploaded CSV files locally for the MVP.
- Load approved CSV datasets into BigQuery.
- Generate BigQuery SQL with Gemini for loaded datasets.
- Validate generated SQL with SQLGlot and table allowlisting.
- Run BigQuery dry runs and apply bytes guardrails.
- Execute only stored, validated, dry-run-approved SQL.
- Return bounded result rows and sanitized error messages.

## Folder Structure

```text
backend/
|-- app/
|   |-- api/
|   |-- core/
|   |-- db/
|   |-- models/
|   |-- routers/
|   |-- schemas/
|   |-- services/
|   `-- tests/
|-- alembic/
|-- storage/uploads/
|-- requirements.txt
|-- alembic.ini
|-- .env.example
`-- README.md
```

## Environment Setup

Windows:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

macOS/Linux:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

## PostgreSQL Setup

Set `DATABASE_URL` in `backend/.env` to your PostgreSQL database:

```env
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/queryshield_ai
```

For disposable local development, the example file defaults to SQLite:

```env
DATABASE_URL=sqlite:///./queryshield.db
```

Local database files are ignored by Git.

## Alembic Migrations

Apply migrations from `backend/`:

```powershell
python -m alembic upgrade head
```

Check the current migration:

```powershell
python -m alembic current
```

Create a future migration after model changes:

```powershell
python -m alembic revision --autogenerate -m "describe change"
```

## Run Commands

Start the API from `backend/`:

```powershell
python -m uvicorn app.main:app --reload
```

API: http://127.0.0.1:8000

Swagger UI: http://127.0.0.1:8000/docs

ReDoc: http://127.0.0.1:8000/redoc

## Test Commands

Run backend tests from `backend/`:

```powershell
python -m pytest
```

The test suite uses FastAPI `TestClient`, HTTPX, local database setup, and mocked BigQuery/Gemini behavior where external cloud calls are not required.

## Environment Variables

Backend variables are defined in `app/core/config.py` and documented in `.env.example`:

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `FRONTEND_ORIGINS`
- `GCP_PROJECT_ID`
- `BIGQUERY_DATASET_ID`
- `GOOGLE_APPLICATION_CREDENTIALS`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `MAX_BYTES_BILLED`
- `QUERY_RESULT_ROW_LIMIT`
- `QUERY_TIMEOUT_SECONDS`
- `BIGQUERY_ON_DEMAND_PRICE_PER_TIB`
- `BIGQUERY_CURRENCY`
- `UPLOAD_DIR`
- `MAX_UPLOAD_SIZE_MB`
- `CSV_PREVIEW_ROWS`

## Endpoint Groups

- `GET /` and `GET /health`: service health.
- `GET /health/db`: database health.
- `POST /auth/signup` and `POST /auth/login`: authentication.
- `GET /users/me`: current authenticated user.
- `/datasets`: dataset CRUD.
- `/datasets/{dataset_id}/upload-csv`: CSV upload and schema detection.
- `/datasets/{dataset_id}/preview`: CSV preview.
- `/datasets/{dataset_id}/load-bigquery`: BigQuery load.
- `/datasets/{dataset_id}/bigquery-info`: BigQuery table metadata.
- `/queries/generate`: Gemini SQL generation.
- `/queries/{query_request_id}/validate`: SQL safety validation.
- `/queries/{query_request_id}/dry-run`: BigQuery dry run.
- `/queries/{query_request_id}/execute`: controlled query execution.
- `/queries`: query history.
- `/queries/{query_request_id}`: query lifecycle detail.
- `/queries/{query_request_id}/audit-logs`: query audit timeline.
- `/audit-logs`: audit log list.

## BigQuery and Gemini Configuration

Required for cloud-backed flows:

```env
GCP_PROJECT_ID=your-gcp-project-id
BIGQUERY_DATASET_ID=queryshield_demo
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account.json
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.5-flash
MAX_BYTES_BILLED=100000000
QUERY_RESULT_ROW_LIMIT=100
QUERY_TIMEOUT_SECONDS=30
```

Keep service account JSON files outside the repository or under ignored credential paths. Gemini and GCP secrets must remain backend-only.


## Docker

The backend image is built from `backend/Dockerfile` and starts FastAPI with:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The image uses Python 3.11 slim, installs `requirements.txt`, runs as a non-root `queryshield` user, exposes port `8000`, and keeps `/app/storage/uploads` writable for uploaded CSV files.

In Docker Compose, migrations run through a one-shot `migrate` service:

```bash
docker compose run --rm migrate
```

The default Compose backend connects to PostgreSQL with the internal hostname `postgres`; do not use `localhost` from inside containers. Backend health uses `GET /health`, and database readiness can be checked with `GET /health/db`.

## Security Notes

- The browser is not trusted to provide SQL, table IDs, bytes limits, or safety approvals.
- Execution uses stored generated SQL only.
- SQL validation and dry-run checks are repeated before execution.
- BigQuery jobs use Standard SQL and `maximum_bytes_billed`.
- Result rows are bounded before storage and response.
- Audit metadata is sanitized to avoid passwords, tokens, API keys, database URLs, and service account content.
