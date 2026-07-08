# QueryShield AI

QueryShield AI is a governed Text-to-SQL analytics platform for BigQuery.

The backend is complete through Step 6. Step 6.5 adds a temporary Next.js test console for exercising the existing backend from a browser. Gemini, SQL generation, SQL validation, cost estimation, query execution, charting, and production frontend behavior are intentionally not included yet.

## Current Step 6.5 Scope

This repository currently contains:

- FastAPI backend setup with health checks
- SQLAlchemy database foundation and Alembic migrations
- User signup, login, JWT authentication, and `/users/me`
- Dataset CRUD with ownership enforcement
- CSV upload, local storage, schema detection, and preview
- BigQuery CSV load and table metadata endpoints
- Configurable CORS for the local frontend
- Next.js TypeScript test console in `frontend/`

## Run Backend

From the repository root:

```powershell
cd backend
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Backend:

http://127.0.0.1:8000

Backend docs:

http://127.0.0.1:8000/docs

Run database migrations when needed:

```powershell
cd backend
python -m alembic upgrade head
```
If a local SQLite database was created by an earlier backend startup before Alembic was applied, `python -m alembic upgrade head` may report that a table already exists. If you want to keep that local data and the schema is already current, stamp the local database once:

```powershell
cd backend
python -m alembic stamp head
python -m alembic upgrade head
```

For a disposable local SQLite database, stop the backend, delete the local `.db` file, then rerun `python -m alembic upgrade head`.

For quick local SQLite verification without PostgreSQL:

```powershell
cd backend
$env:DATABASE_URL="sqlite:///./queryshield_local.db"
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```


## Local SQLite Mode

Local development now uses SQLite by default through `backend/.env`:

```env
DATABASE_URL=sqlite:///./queryshield.db
```

Apply migrations from `backend/` with:

```powershell
python -m alembic upgrade head
```

The SQLite database file is `backend/queryshield.db`. For a clean local reset, stop the backend, delete that `.db` file, then rerun `python -m alembic upgrade head.`r`n`r`n## Run Frontend

Open another terminal:

```powershell
cd frontend
Copy-Item .env.example .env.local
npm install
npm run dev
```

On macOS/Linux, use `cp .env.example .env.local` instead of `Copy-Item`.

Frontend:

http://localhost:3000

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

## Full Manual Testing Flow

1. Check backend health.
2. Sign up.
3. Log in.
4. Verify current user.
5. Create a dataset.
6. Select the dataset.
7. Upload a CSV.
8. Preview the CSV.
9. Load the dataset into BigQuery.
10. Fetch BigQuery table information.
11. Delete the test dataset if desired.

Google credentials must be configured in the backend before testing BigQuery loading.

## Security Note

The Step 6.5 frontend is an internal local testing console. It stores the JWT access token in `localStorage` under `queryshield_access_token` for convenience. A production frontend should reconsider token storage and may use secure HTTP-only cookies.
