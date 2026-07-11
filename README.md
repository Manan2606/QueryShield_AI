# QueryShield AI

QueryShield AI is a governed Text-to-SQL analytics platform for BigQuery. The current MVP supports authenticated dataset onboarding, CSV schema detection and preview, BigQuery loading, natural-language SQL generation, validation, cost dry run, bounded query execution, persisted query history, and audit logs.

## Current MVP Scope

This repository currently contains:

- FastAPI backend with health checks, database migrations, JWT auth, and `/users/me`
- Dataset CRUD with ownership enforcement
- CSV upload, local storage, schema detection, and preview
- BigQuery CSV load and table metadata endpoints
- Gemini-backed SQL generation for loaded datasets
- Server-side SQL validation, dry-run cost checks, execution eligibility, and bounded execution results
- Query lifecycle history and audit log endpoints
- Routed Next.js frontend in `frontend/` for Phase-1 MVP workflows

## Run Backend

From the repository root:

```powershell
cd backend
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```

Backend: http://127.0.0.1:8000

Backend docs: http://127.0.0.1:8000/docs

For quick local SQLite verification without PostgreSQL:

```powershell
cd backend
$env:DATABASE_URL="sqlite:///./queryshield_local.db"
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```

## Run Frontend

Open another terminal:

```powershell
cd frontend
Copy-Item .env.example .env.local
npm install
npm run dev
```

On macOS/Linux, use `cp .env.example .env.local` instead of `Copy-Item`.

Frontend: http://localhost:3000

## Frontend Routes

- `/login` and `/signup` are public auth screens.
- `/dashboard` summarizes datasets and recent query activity.
- `/datasets` creates, filters, opens, and deletes datasets.
- `/datasets/[id]` manages CSV upload, detected schema, preview, and BigQuery load.
- `/queries/new` runs the governed query pipeline: generate, validate, dry run, execute.
- `/history` lists query lifecycle records with filters.
- `/queries/[id]` shows a single query lifecycle, bounded results, and audit timeline.
- `/audit-logs` lists audit events with filters.

Protected routes read the MVP access token from `localStorage`, validate it through `/users/me`, and redirect to `/login` if the session is missing or invalid.

## Environment

Backend CORS allows the local frontend origins configured by `FRONTEND_ORIGINS`:

```env
FRONTEND_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Frontend configuration belongs in `frontend/.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

Only the public API base URL should use a `NEXT_PUBLIC_*` variable. Do not put backend secrets, service account keys, Google credentials, or raw secrets in frontend environment variables.

## Manual Testing Flow

1. Start the backend and frontend.
2. Sign up or log in.
3. Create a dataset.
4. Upload a CSV and confirm schema plus preview.
5. Load the dataset into BigQuery.
6. Ask a natural-language question from `/queries/new`.
7. Generate SQL, validate it, run the dry run, and execute only if the backend marks it eligible.
8. Review bounded results, query history, and audit logs.

Google credentials must be configured in the backend before testing BigQuery loading, SQL generation, dry run, or execution against BigQuery.

## Security Note

The MVP frontend stores the JWT access token in `localStorage` under `queryshield_access_token`. This is acceptable for the current local MVP but should be revisited before production, likely with secure HTTP-only cookies or another hardened session strategy.