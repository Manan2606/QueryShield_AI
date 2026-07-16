# QueryShield AI

QueryShield AI is a governed natural-language-to-SQL analytics platform that uses Gemini and BigQuery to generate, validate, estimate, and safely execute analytical queries over uploaded CSV datasets.

## Project Overview

The Phase-1 MVP supports the full governed analytics workflow:

1. Sign up and log in.
2. Create a dataset.
3. Upload a CSV file.
4. Detect and review schema.
5. Load the dataset into BigQuery.
6. Ask a natural-language question.
7. Generate BigQuery SQL using Gemini.
8. Validate SQL safety.
9. Run a BigQuery dry run.
10. Estimate bytes and cost.
11. Execute only approved queries.
12. Display bounded results.
13. Save query history and audit logs.

## Why This Project Exists

Text-to-SQL systems can generate unsafe, unauthorized, or expensive queries. QueryShield AI adds parser-based validation, table ownership checks, BigQuery dry runs, cost guardrails, controlled execution, and auditability before generated SQL can run.

The project demonstrates full-stack engineering across AI, backend APIs, data workflows, cloud services, database migrations, and a production-oriented frontend.

## Core Features

- JWT authentication
- Dataset ownership
- CSV upload
- Schema detection and preview
- BigQuery loading
- Gemini SQL generation
- SQL parser-based validation
- Table allowlisting
- BigQuery dry runs
- Cost guardrails
- Controlled query execution
- Bounded result rows
- Query history
- Audit logging
- Next.js frontend

## Governance Pipeline

Natural-language question
-> Gemini SQL generation
-> SQL safety validation
-> BigQuery dry run
-> Cost guardrail
-> Controlled execution
-> Results and audit history

## Architecture

Main components:

- Next.js frontend
- FastAPI backend
- PostgreSQL or local SQLite for development
- Gemini API
- BigQuery
- SQLAlchemy models
- Alembic migrations
- Deploy MVP-1 to GCP using Cloud Run, Artifact Registry, SQLite demo mode, Cloud Storage, Secret Manager, BigQuery, Cloud Logging, and Workload Identity Federation

See [docs/architecture.md](docs/architecture.md) for the system diagram, trust boundaries, and execution controls. See [docs/gcp-architecture.md](docs/gcp-architecture.md) for the GCP deployment architecture and CI/CD diagrams.

## Tech Stack

### Frontend

- Next.js
- TypeScript
- Tailwind CSS

### Backend

- FastAPI
- Python
- SQLAlchemy
- Alembic
- Pydantic

### Database

- PostgreSQL
- SQLite for local disposable development

### AI and Data

- Gemini via `google-genai`
- BigQuery via `google-cloud-bigquery`
- SQLGlot

### Testing and Tooling

- Pytest
- HTTPX
- Git
- GitHub

## Repository Structure

```text
queryshield-ai/
|-- backend/
|   |-- app/
|   |-- alembic/
|   |-- storage/
|   |-- requirements.txt
|   |-- alembic.ini
|   |-- .env.example
|   `-- README.md
|-- frontend/
|   |-- app/
|   |-- components/
|   |-- lib/
|   |-- package.json
|   |-- .env.example
|   `-- README.md
|-- docs/
|-- screenshots/
|-- README.md
|-- LICENSE
|-- CONTRIBUTING.md
`-- .gitignore
```

## Local Setup

### Prerequisites

- Python 3.11 recommended
- Node.js 20 LTS or newer
- PostgreSQL for a production-like local setup
- Google Cloud project with BigQuery API enabled
- Gemini API key
- Service account or Application Default Credentials for BigQuery

### Backend Setup

Windows:

```powershell
cd backend
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```

macOS/Linux:

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```

Backend API: http://127.0.0.1:8000

### Frontend Setup

Windows:

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

macOS/Linux:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Frontend app: http://localhost:3000


## Docker Compose

Prerequisites:

- Docker Desktop or Docker Engine
- Docker Compose plugin

Start the local production-style stack from the repository root:

```bash
docker compose up --build
```

Application URLs:

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

Useful commands:

```bash
docker compose config
docker compose build
docker compose up --build
docker compose ps
docker compose logs -f backend
docker compose logs -f frontend
docker compose down
```

To remove containers and local named volumes:

```bash
docker compose down -v
```

`docker compose down -v` deletes the local PostgreSQL data volume and uploaded CSV storage volume.

Compose uses local development defaults only. Do not reuse the included database password or JWT secret in production. Gemini and BigQuery credentials are not required for container startup, and service-account JSON files must not be baked into images.


## Continuous Integration

GitHub Actions CI is defined in `.github/workflows/ci.yml`. It runs on pull requests and pushes to `main` and `dev`.

CI verifies:

- backend dependency installation
- Alembic migration compatibility
- backend tests
- frontend dependency installation from `package-lock.json`
- frontend build
- Docker image builds
- Compose configuration validity

The CI workflow does not deploy the application, push images, or require real Gemini or GCP credentials.
## GCP MVP-1 Deployment

MVP-1 deployment is documented in [docs/gcp-mvp1-deployment.md](docs/gcp-mvp1-deployment.md). The target deployment uses:

- Cloud Run for the FastAPI backend and Next.js frontend services.
- Artifact Registry for backend and frontend images.
- BigQuery for analytical tables, dry runs, and controlled SQL execution.
- Cloud Storage for uploaded CSV files in deployed environments.
- Secret Manager for backend runtime secrets.
- Cloud Logging for runtime logs.
- Workload Identity Federation for GitHub Actions deployment authentication.
- SQLite demo mode at `sqlite:////tmp/queryshield.db` for MVP-1 metadata only.

Cloud SQL is intentionally excluded from MVP-1. Cloud Run filesystem storage is ephemeral, so signup users, query history, audit logs, and dataset metadata can reset after restart. The backend deploy uses min instances `0` and max instances `1` to reduce cost and avoid multiple isolated SQLite databases.

The combined deployment workflow is `.github/workflows/deploy-gcp.yml`. It builds and pushes backend and frontend images to Artifact Registry, deploys both services to Cloud Run, maps `JWT_SECRET_KEY` and `GEMINI_API_KEY` from Secret Manager, captures service URLs, updates backend CORS to the exact frontend URL, and verifies health endpoints.

Local development still supports SQLite or the Compose PostgreSQL service and local disk uploads. Deployed MVP-1 mode should set `STORAGE_BACKEND=gcs` and `GCS_UPLOAD_BUCKET=queryshield_ai`. The frontend should expose only `NEXT_PUBLIC_API_BASE_URL` and no backend secrets.
## Environment Variables

Do not commit real `.env` files, API keys, database passwords, or service account JSON files.

Backend variables:

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

Frontend variables:

- `NEXT_PUBLIC_API_BASE_URL`

## API Documentation

When the backend is running:

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

See [backend/README.md](backend/README.md) for endpoint groups and backend setup details.

## Screenshots

Screenshots are not committed yet. Add final demo images under `screenshots/` using these suggested names:

- `dashboard.png`
- `dataset-upload.png`
- `schema-preview.png`
- `sql-generation.png`
- `sql-validation.png`
- `dry-run-estimate.png`
- `query-results.png`
- `query-history.png`

## Security Controls

QueryShield AI is an MVP with a defense-in-depth design, not a claim of perfect security. Current controls include:

- JWT authentication
- Dataset ownership checks
- Read-only SQL enforcement
- Single-statement validation
- Table allowlisting
- BigQuery dry run before execution
- Configurable maximum bytes billed
- Row limits
- Query timeout
- Audit logging
- Backend-only GCP and Gemini secrets

## Current Status

- Phase-1 MVP complete
- Dockerization added for local Compose usage
- GitHub Actions CI added for tests, builds, Docker image builds, and Compose validation
- Provision GCP resources and run Cloud Run deployment readiness added; live deployment pending manual GCP resource provisioning
- AI result summary pending
- Charts pending

## Roadmap

- Provision GCP resources and run Cloud Run deployment
- AI result summaries
- Charts
- Demo video
- Resume update

## Cost Awareness

The MVP uses BigQuery dry runs, configurable maximum bytes billed, informational cost estimation, and limited result rows to reduce the risk of unexpectedly expensive generated queries. For GCP MVP-1 demo deployments, keep Cloud Run min instances at 0, max instances at 1, use SQLite demo mode only, keep BigQuery bytes limits low, set budget alerts, and delete demo resources after recording if they are no longer needed.

## License

This project is licensed under the [MIT License](LICENSE).
