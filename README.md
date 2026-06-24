# QueryShield AI

QueryShield AI is a governed Text-to-SQL analytics platform for BigQuery.

The goal is to let users upload CSV datasets, ask natural-language questions, generate SQL using Gemini, validate generated SQL for safety, estimate BigQuery cost using dry run, execute only approved queries, show results, and save query history and audit logs.

## Phase-1 Goal

Phase 1 will eventually include user authentication, CSV upload, BigQuery loading, dataset schema storage, natural-language questions, Gemini SQL generation, SQL safety validation, cost estimation, approved query execution, result display, and query history.

## Current Step 1 Scope

This repository currently contains only the project foundation and FastAPI backend skeleton:

- Monorepo structure
- FastAPI app setup
- Environment configuration setup
- SQLAlchemy database connection scaffolding
- Health endpoint
- Backend dependency list
- Environment example file
- Frontend placeholder folder

Authentication, BigQuery, Gemini, CSV upload, SQL validation, and frontend implementation are intentionally not included yet.

## Tech Stack

- Python
- FastAPI
- Uvicorn
- SQLAlchemy
- Pydantic
- pydantic-settings
- python-dotenv
- PostgreSQL
- PyTest and HTTPX for future testing
- Next.js frontend later

## Local Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

On Windows:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Create a local `.env` file from `.env.example` before running the backend:

```bash
cp .env.example .env
```

API docs should be available at:

[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Current API Endpoints

- `GET /` returns project status and API version.
- `GET /health` returns backend health status.
