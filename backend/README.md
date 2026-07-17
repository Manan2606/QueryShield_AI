# QueryShield AI Backend

FastAPI backend for QueryShield AI. It owns authentication, dataset records, CSV processing, Cloud Storage uploads, BigQuery loading, Gemini SQL generation, SQL validation, dry-run cost checks, controlled execution, AI result summaries, query history, and audit logs.

## Responsibilities

- Authenticate users with JWT access tokens.
- Enforce dataset and query ownership.
- Store dataset metadata, detected columns, query lifecycle records, bounded result rows, AI summaries, and audit logs.
- Save uploaded CSV files locally for development or to Cloud Storage in deployed GCP mode.
- Load approved CSV datasets into BigQuery.
- Generate BigQuery SQL with Gemini for loaded datasets.
- Validate generated SQL with SQLGlot and table allowlisting.
- Run BigQuery dry runs and apply bytes guardrails.
- Execute only stored, validated, dry-run-approved SQL.
- Generate optional AI summaries only after controlled execution succeeds.
- Return bounded result rows and sanitized error messages.

## Folder Structure

```text
backend/
|-- app/
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
|-- .env.gcp.example
`-- README.md
```

## Environment Setup

Windows:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```

macOS/Linux:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```

API: http://127.0.0.1:8000

Swagger UI: http://127.0.0.1:8000/docs

ReDoc: http://127.0.0.1:8000/redoc

## Database

For disposable local development, `.env.example` defaults to SQLite:

```env
DATABASE_URL=sqlite:///./queryshield.db
```

For production-like local development, use PostgreSQL:

```env
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/queryshield_ai
```

Local database files are ignored by Git. MVP-1 Cloud Run deployment uses `sqlite:////tmp/queryshield.db` for metadata only; that data is ephemeral.

## Cloud Storage, BigQuery, and Gemini

Required for cloud-backed upload, load, generation, dry-run, execution, and summary flows:

```env
GCP_PROJECT_ID=your-gcp-project-id
GCP_REGION=us-central1
BIGQUERY_DATASET_ID=queryshield_demo
STORAGE_BACKEND=gcs
GCS_UPLOAD_BUCKET=your-upload-bucket
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.5-flash
MAX_BYTES_BILLED=100000000
QUERY_RESULT_ROW_LIMIT=100
QUERY_TIMEOUT_SECONDS=30
AI_SUMMARY_ENABLED=true
SUMMARY_MAX_ROWS=25
SUMMARY_MAX_CHARS=6000
```

Use `GOOGLE_APPLICATION_CREDENTIALS` only for local development when Application Default Credentials are not available. On Cloud Run, use the runtime service account and do not mount or bake service-account JSON files into the image.

## Migrations

Run from `backend/`:

```powershell
python -m alembic upgrade head
python -m alembic current
```

Create a future migration after model changes:

```powershell
python -m alembic revision --autogenerate -m "describe change"
```

## Tests

Run from `backend/`:

```powershell
python -m pytest
```

The test suite uses FastAPI `TestClient`, HTTPX, local database setup, and mocked BigQuery/Gemini behavior where external cloud calls are not required.

## Endpoint Groups

- `GET /` and `GET /health`: service health.
- `GET /health/db`: database health.
- `POST /auth/signup` and `POST /auth/login`: authentication.
- `GET /users/me`: current authenticated user.
- `/datasets`: dataset CRUD.
- `/datasets/{dataset_id}/upload-csv`: CSV upload, storage, and schema detection.
- `/datasets/{dataset_id}/preview`: CSV preview.
- `/datasets/{dataset_id}/load-bigquery`: BigQuery load.
- `/datasets/{dataset_id}/bigquery-info`: BigQuery table metadata.
- `/queries/generate`: Gemini SQL generation.
- `/queries/{query_request_id}/validate`: SQL safety validation.
- `/queries/{query_request_id}/dry-run`: BigQuery dry run.
- `/queries/{query_request_id}/execute`: controlled query execution, bounded result storage, and optional summary generation.
- `/queries`: query history.
- `/queries/{query_request_id}`: query lifecycle detail.
- `/queries/{query_request_id}/audit-logs`: query audit timeline.
- `/audit-logs`: audit log list.

## Environment Variables

Backend variables are defined in `app/core/config.py` and documented in `.env.example`:

- `APP_ENV`
- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `FRONTEND_ORIGINS`
- `GCP_PROJECT_ID`
- `GCP_REGION`
- `BIGQUERY_DATASET_ID`
- `GOOGLE_APPLICATION_CREDENTIALS`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `MAX_BYTES_BILLED`
- `QUERY_RESULT_ROW_LIMIT`
- `QUERY_TIMEOUT_SECONDS`
- `BIGQUERY_ON_DEMAND_PRICE_PER_TIB`
- `BIGQUERY_CURRENCY`
- `STORAGE_BACKEND`
- `GCS_UPLOAD_BUCKET`
- `UPLOAD_DIR`
- `MAX_UPLOAD_SIZE_MB`
- `CSV_PREVIEW_ROWS`
- `AI_SUMMARY_ENABLED`
- `SUMMARY_MAX_ROWS`
- `SUMMARY_MAX_CHARS`

## Docker

The backend image is built from `backend/Dockerfile` and starts FastAPI with:

```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

The image uses Python 3.11 slim, installs `requirements.txt`, runs as a non-root `queryshield` user, and starts on the Cloud Run `PORT` environment variable with a default of `8000`. Local mode can keep `/app/storage/uploads` writable; deployed GCP mode should use `STORAGE_BACKEND=gcs` and `GCS_UPLOAD_BUCKET`.

In Docker Compose, migrations run through a one-shot `migrate` service:

```bash
docker compose run --rm migrate
```

The default Compose backend connects to PostgreSQL with the internal hostname `postgres`; do not use `localhost` from inside containers.

## Security Notes

- The browser is not trusted to provide SQL, table IDs, bytes limits, or safety approvals.
- Execution uses stored generated SQL only.
- SQL validation and dry-run checks are repeated before execution.
- BigQuery jobs use Standard SQL and `maximum_bytes_billed`.
- Result rows are bounded before storage and response.
- AI summaries use only bounded returned rows and are non-authoritative.
- Audit metadata is sanitized to avoid passwords, tokens, API keys, database URLs, and service account content.
- Runtime secrets belong in Secret Manager on GCP, not in repository files or frontend environment variables.

## GCP Deployment Notes

For the MVP-1 GCP demo, use SQLite in Cloud Run `/tmp` for metadata and Cloud Storage instead of container-local upload storage:

```env
APP_ENV=production
DATABASE_URL=sqlite:////tmp/queryshield.db
STORAGE_BACKEND=gcs
GCS_UPLOAD_BUCKET=your-upload-bucket
FRONTEND_ORIGINS=https://your-frontend-service-url
```

Cloud Run should provide `JWT_SECRET_KEY` and `GEMINI_API_KEY` from Secret Manager. `DATABASE_URL` is a non-secret MVP-1 value set to `sqlite:////tmp/queryshield.db`. Prefer the Cloud Run runtime service account for BigQuery and Cloud Storage access instead of `GOOGLE_APPLICATION_CREDENTIALS` in production.

See `../docs/gcp-mvp1-deployment.md` for the deployment checklist and `../docs/gcp-architecture.md` for diagrams.