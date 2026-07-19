# QueryShield AI

QueryShield AI is a governed natural-language-to-SQL analytics platform that lets users upload CSV datasets, ask questions in plain English, and receive safe, cost-controlled analytical results using Gemini and BigQuery.

AI-generated SQL can be unsafe, expensive, or hard to audit. QueryShield AI adds a governance layer before execution: SQL generation, SQL validation, BigQuery dry run, cost guardrail, controlled execution, bounded results, AI summary, charting, query history, and audit logs.

## Demo

Demo video recorded. Public or unlisted link will be added here.

- [Demo walkthrough notes](docs/demo-walkthrough.md)
- [Project presentation deck](docs/QueryShield_AI_Presentation.pptx)

## Screenshots

### Dashboard

![Dashboard](docs/screenshots/02_dashboard.png)

### Dataset Upload

![Dataset Upload](docs/screenshots/03_csv_upload.png)

### Governed Query Result

![AI Summary and Chart](docs/screenshots/06_ai_summary_chart.png)

### Query History and Audit Logs

![Query History](docs/screenshots/07_query_history.png)

![Audit Logs](docs/screenshots/08_audit_logs.png)

## Key Features

- JWT authentication and protected user workflows
- Dataset creation, CSV upload, schema detection, and preview
- Cloud Storage upload support for deployed mode
- BigQuery table loading, dry runs, and controlled execution
- Gemini-powered natural-language-to-SQL generation
- SQLGlot parser-based validation before execution
- Table allowlisting and single-statement read-only enforcement
- Configurable BigQuery bytes, timeout, and row-limit guardrails
- AI-generated summaries and automatic charts from bounded result rows
- Query history and audit logs for traceability
- Dockerized FastAPI backend and Next.js frontend
- GitHub Actions CI/CD with Cloud Run deployment

## Architecture

The frontend is built with Next.js and communicates with a FastAPI backend. The backend owns authentication, dataset metadata, CSV processing, Gemini SQL generation, SQL validation, BigQuery dry-run estimation, controlled execution, summaries, history, and audit logs.

```text
User
-> Next.js frontend
-> FastAPI backend
-> Gemini for SQL generation and result summaries
-> Cloud Storage for uploaded CSV files
-> BigQuery for analytical tables and governed SQL execution
-> SQLite for MVP metadata
-> Cloud Run for deployed frontend/backend services
```

Related docs:

- [Application architecture](docs/architecture.md)
- [GCP architecture](docs/gcp-architecture.md)
- [GCP deployment guide](docs/gcp-mvp1-deployment.md)

## Query Governance Pipeline

QueryShield AI does not blindly execute AI-generated SQL.

1. User asks a natural-language question
2. Gemini generates BigQuery SQL
3. SQLGlot validates syntax and statement type
4. Backend enforces read-only, single-statement SQL
5. Backend restricts access to the selected dataset table
6. BigQuery dry run estimates bytes scanned
7. Maximum bytes billed guardrail is enforced
8. Approved query is executed with row and timeout limits
9. Results are saved with chart, summary, history, and audit events

The result table remains the source of truth. AI summaries and charts are generated only from returned rows.

## GCP Services Used

| Service | Purpose |
|---|---|
| Cloud Run | Runs containerized frontend and backend |
| Artifact Registry | Stores Docker images |
| Cloud Storage | Stores uploaded CSV files |
| BigQuery | Stores analytical tables and executes governed SQL |
| Secret Manager | Stores JWT and Gemini secrets |
| IAM | Controls least-privilege service access |
| Cloud Logging | Captures runtime logs |
| GitHub Actions | Automates CI/CD deployment |

## Tech Stack

| Area | Technologies |
|---|---|
| Frontend | Next.js, React, TypeScript, Tailwind CSS, Recharts |
| Backend | FastAPI, Python 3.11, SQLAlchemy, Alembic, Pydantic, pytest |
| AI / Data | Gemini, SQLGlot, BigQuery |
| Cloud / DevOps | Cloud Run, Cloud Storage, Secret Manager, Artifact Registry, IAM, Docker, GitHub Actions, Workload Identity Federation |
| MVP Metadata | SQLite |

## Local Development

### Backend

```powershell
cd backend
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```

Backend API: http://127.0.0.1:8000

### Frontend

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

Frontend app: http://localhost:3000

## Environment Variables

Use placeholders only. Do not commit real `.env` files, API keys, service-account JSON files, local databases, or uploaded CSVs.

```env
APP_ENV=local
DATABASE_URL=sqlite:///./queryshield.db
JWT_SECRET_KEY=replace-with-strong-secret
GCP_PROJECT_ID=your-gcp-project-id
BIGQUERY_DATASET_ID=queryshield_demo
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.5-flash
MAX_BYTES_BILLED=100000000
QUERY_RESULT_ROW_LIMIT=100
QUERY_TIMEOUT_SECONDS=30
STORAGE_BACKEND=local
GCS_UPLOAD_BUCKET=
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

For Cloud Run, secrets are injected from Secret Manager. Local service-account JSON files must not be committed.

## Docker

```bash
docker compose up --build
```

Direct image builds:

```bash
docker build -t queryshield-backend ./backend
docker build -t queryshield-frontend ./frontend
```

## CI/CD and Deployment

GitHub Actions verifies backend tests, migrations, frontend type checks, chart tests, frontend build, Docker builds, and Compose configuration.

The deployment workflow builds Docker images, pushes them to Artifact Registry, and deploys the frontend and backend to Cloud Run using Workload Identity Federation. Runtime secrets are provided by Secret Manager, so no long-lived service-account JSON is stored in GitHub.

## MVP Design Decisions and Limitations

MVP-1 uses SQLite for lightweight metadata storage, including users, datasets, query history, and audit logs. Uploaded CSV files are stored in Cloud Storage for deployed mode, and analytical tables are loaded into BigQuery.

Current limitations:

- SQLite metadata can reset in Cloud Run because `/tmp` is ephemeral
- Multi-table joins are not included in MVP-1
- Role-based access control is planned but not implemented
- Query summaries and charts are based only on bounded returned rows
- Uploaded demo datasets are intentionally small

Future production work would replace SQLite with Cloud SQL PostgreSQL, add role-based access control, support multi-table joins, add high-cost query approval workflows, and introduce retention policies for uploaded files and audit logs.

## Resume Highlights

- Built QueryShield AI, a governed Text-to-SQL analytics platform using FastAPI, Next.js, Gemini, BigQuery, Cloud Run, Cloud Storage, and Secret Manager.
- Implemented a query governance pipeline with AI SQL generation, parser-based validation, BigQuery dry runs, and controlled execution.
- Automated containerized deployment to Google Cloud Run using Docker, GitHub Actions, Artifact Registry, Workload Identity Federation, IAM, and Secret Manager.

## License

This project is licensed under the [MIT License](LICENSE).
