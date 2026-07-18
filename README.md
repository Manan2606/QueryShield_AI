# QueryShield AI

QueryShield AI is a governed natural-language-to-SQL analytics platform. It lets users upload CSV datasets, load them into BigQuery, ask natural-language questions, and receive controlled analytical results with validation, dry-run cost checks, bounded rows, AI summaries, charts, history, and audit logs.

## Phase-1 Scope

The Phase-1 MVP supports the complete governed analytics workflow:

1. Sign up and log in.
2. Create a dataset.
3. Upload a CSV file.
4. Store uploads locally in development or in Cloud Storage on GCP.
5. Detect and review schema.
6. Load the dataset into BigQuery.
7. Ask a natural-language question.
8. Generate BigQuery SQL using Gemini.
9. Validate SQL safety and table ownership.
10. Run a BigQuery dry run.
11. Enforce bytes and cost guardrails.
12. Execute only approved queries.
13. Display bounded results, charts, and AI summaries.
14. Save query history and audit logs.

## Why This Project Exists

Text-to-SQL systems can generate unsafe, unauthorized, or expensive queries. QueryShield AI adds parser-based validation, table ownership checks, BigQuery dry runs, cost guardrails, controlled execution, and auditability before generated SQL can run.

The project demonstrates full-stack engineering across AI, backend APIs, data workflows, cloud services, database migrations, CI/CD, and a production-oriented frontend.

## Core Features

- JWT authentication and protected routes
- Dataset ownership and lifecycle management
- CSV upload with schema detection and preview
- Cloud Storage upload support for deployed GCP mode
- BigQuery loading, dry runs, and controlled execution
- Gemini SQL generation
- SQLGlot parser-based validation
- Table allowlisting and single-statement read-only enforcement
- Configurable bytes, timeout, and row-limit guardrails
- AI result summaries from bounded execution rows
- Deterministic bar, line, and pie charts from bounded execution rows
- Query history and audit log timelines
- Docker Compose local stack
- GitHub Actions CI and GCP Cloud Run deployment workflow

## Governance Pipeline

```text
Natural-language question
-> Gemini SQL generation
-> SQL safety validation
-> BigQuery dry run
-> Cost guardrail
-> Controlled execution
-> Results, chart, AI summary, history, and audit log
```

## Architecture

Main components:

- Next.js frontend
- FastAPI backend
- PostgreSQL for production-like local development or SQLite for disposable MVP/demo metadata
- Gemini API
- BigQuery
- Cloud Storage for deployed CSV uploads
- SQLAlchemy models and Alembic migrations
- Cloud Run, Artifact Registry, Secret Manager, Cloud Logging, and Workload Identity Federation for GCP deployment

See [docs/architecture.md](docs/architecture.md) for application architecture and trust boundaries. See [docs/gcp-architecture.md](docs/gcp-architecture.md) for the GCP service map, deployment architecture, and CI/CD diagrams.

## Demo Evidence

The final demo recording and screenshots are stored in `docs/`:

- [Demo walkthrough video](docs/QueryShield_AI_Recording_Video.mp4)
- [Demo screenshots and flow notes](docs/demo-walkthrough.md)

The screenshots cover authentication, dashboard, CSV upload, schema preview, SQL validation, AI summary/chart output, query history, and audit logs.

## Tech Stack

Frontend:

- Next.js App Router
- TypeScript
- Tailwind CSS
- Recharts

Backend:

- FastAPI
- Python 3.11
- SQLAlchemy
- Alembic
- Pydantic

AI and data:

- Gemini via `google-genai`
- BigQuery via `google-cloud-bigquery`
- Cloud Storage via `google-cloud-storage`
- SQLGlot

Testing and delivery:

- Pytest
- Frontend chart inference smoke tests
- Docker and Docker Compose
- GitHub Actions
- Google Cloud Run

## Repository Structure

```text
queryshield-ai/
|-- .github/workflows/
|-- backend/
|   |-- app/
|   |-- alembic/
|   |-- storage/uploads/
|   |-- requirements.txt
|   |-- alembic.ini
|   |-- .env.example
|   |-- .env.gcp.example
|   `-- README.md
|-- frontend/
|   |-- app/
|   |-- components/
|   |-- lib/
|   |-- tests/
|   |-- package.json
|   |-- package-lock.json
|   |-- .env.example
|   `-- README.md
|-- docs/
|   |-- screenshots/
|   |-- demo-walkthrough.md
|   `-- QueryShield_AI_Recording_Video.mp4
|-- compose.yaml
|-- CONTRIBUTING.md
|-- README.md
`-- .gitignore
```

## Local Setup

Prerequisites:

- Python 3.11
- Node.js 20 LTS or newer
- Docker Desktop or Docker Engine for Compose
- Google Cloud project with BigQuery enabled for cloud-backed query flows
- Gemini API key for SQL generation and AI summaries
- Application Default Credentials or a local service-account JSON file for local BigQuery/GCS testing only

Backend on Windows:

```powershell
cd backend
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```

Backend on macOS/Linux:

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

Frontend on Windows:

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

Frontend on macOS/Linux:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Frontend app: http://localhost:3000

## Docker Compose

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

`docker compose down -v` deletes the local PostgreSQL data volume and uploaded CSV storage volume. Compose uses local development defaults only. Do not reuse the included database password or JWT secret in production. Gemini and GCP credentials are not required for container startup, and service-account JSON files must not be baked into images.

## Continuous Integration

GitHub Actions CI is defined in `.github/workflows/ci.yml`. It runs on pull requests and pushes to `main` and `dev`.

CI verifies:

- backend dependency installation
- Alembic migration compatibility
- backend tests
- frontend dependency installation from `package-lock.json`
- frontend chart inference tests
- frontend build
- Docker image builds
- Compose configuration validity

The CI workflow does not deploy the application, push images, or require real Gemini or GCP credentials.

## GCP MVP-1 Deployment

MVP-1 deployment is documented in [docs/gcp-mvp1-deployment.md](docs/gcp-mvp1-deployment.md). The target deployment uses:

- Cloud Run for the FastAPI backend and Next.js frontend services
- Artifact Registry for backend and frontend images
- BigQuery for analytical tables, dry runs, and controlled SQL execution
- Cloud Storage for uploaded CSV files
- Secret Manager for backend runtime secrets
- Cloud Logging for runtime logs
- Workload Identity Federation for GitHub Actions deployment authentication
- SQLite demo mode at `sqlite:////tmp/queryshield.db` for MVP-1 metadata only

Cloud SQL is intentionally excluded from MVP-1. Cloud Run filesystem storage is ephemeral, so signup users, query history, audit logs, and dataset metadata can reset after restart. The backend runs Alembic migrations on production startup so a fresh SQLite file has the required tables and current migration revision before signup or query workflows run. For public demo reuse beyond a recorded MVP walkthrough, move metadata to a durable store such as Cloud SQL before inviting external users. The backend deploy uses min instances `0` and max instances `1` to reduce cost and avoid multiple isolated SQLite databases.

The deployment workflow is `.github/workflows/deploy-gcp.yml`. It builds and pushes backend and frontend images to Artifact Registry, deploys both services to Cloud Run, maps `JWT_SECRET_KEY` and `GEMINI_API_KEY` from Secret Manager, captures service URLs, updates backend CORS to the exact frontend URL, and verifies service health, readiness, and database schema endpoints, then smoke-tests deployed signup and login.

## Environment Variables

Do not commit real `.env` files, API keys, database passwords, service-account JSON files, local databases, uploaded CSVs, logs, build outputs, or virtual environments.

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
- `GOOGLE_APPLICATION_CREDENTIALS` for local development only
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
- `MAX_CSV_COLUMNS`
- `AI_SUMMARY_ENABLED`
- `SUMMARY_MAX_ROWS`
- `SUMMARY_MAX_CHARS`

Frontend variables:

- `NEXT_PUBLIC_API_BASE_URL`

## API Documentation

When the backend is running:

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

See [backend/README.md](backend/README.md) for endpoint groups and backend setup details.

## Security Controls

QueryShield AI is an MVP with a defense-in-depth design, not a claim of perfect security. Current controls include:

- JWT authentication
- Dataset ownership checks
- Backend-only Gemini and GCP secrets
- Read-only SQL enforcement
- Single-statement validation
- Table allowlisting
- BigQuery dry run before execution
- Configurable maximum bytes billed
- Row limits and query timeout
- Sanitized error handling
- Audit logging

## Current Status

- Phase-1 MVP complete
- GCP Cloud Run deployment workflow added
- Cloud Storage uploads enabled for deployed mode
- BigQuery loading, dry run, and controlled execution working
- AI result summaries implemented after controlled execution
- Charts implemented from bounded query result rows
- Demo recording and screenshots added under `docs/`
- Local generated files, uploaded CSV copies, DB files, caches, and build outputs are ignored and cleaned before push

## Roadmap

- Resume update
- Harden browser session handling with secure HTTP-only cookies

## Cost Awareness

The MVP uses BigQuery dry runs, configurable maximum bytes billed, informational cost estimation, and limited result rows to reduce the risk of unexpectedly expensive generated queries. For GCP MVP-1 demo deployments, keep Cloud Run min instances at 0, max instances at 1, use SQLite demo mode only, keep BigQuery bytes limits low, set budget alerts, and delete demo resources after recording if they are no longer needed.

## License

This project is licensed under the [MIT License](LICENSE).