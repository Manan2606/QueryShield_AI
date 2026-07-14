# QueryShield AI Frontend

Next.js App Router frontend for the QueryShield AI Phase-1 MVP.

## Responsibilities

- Provide public login and signup screens.
- Guard authenticated application routes.
- Manage dataset creation, upload, schema preview, and BigQuery load workflows.
- Run the governed query workflow behind one Analyze action: generate, validate, dry run, then execute only when eligible.
- Show bounded query results, query history, query detail, and audit logs.
- Call the FastAPI backend through a single public API base URL.

## Stack

- Next.js App Router
- TypeScript
- Tailwind CSS
- React hooks
- Native browser `fetch`

## Environment Setup

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

Frontend: http://localhost:3000

## Environment Variables

`frontend/.env.local` should contain:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

Only expose `NEXT_PUBLIC_API_BASE_URL` to the browser. Do not place backend secrets, Google service account files, database credentials, Gemini API keys, or raw tokens in frontend environment variables.

## Commands

```powershell
npm run dev
npm run build
npm run start
```

This project currently does not define an `npm run lint` script.

## Routes

- `/`: redirects users into the app flow.
- `/login`: public login screen.
- `/signup`: public signup screen.
- `/dashboard`: protected summary of datasets and recent query activity.
- `/datasets`: protected dataset creation, filtering, navigation, and deletion.
- `/datasets/[id]`: protected CSV upload, schema preview, and BigQuery load workflow.
- `/queries/new`: protected analysis workspace with dataset selection, one Analyze action, results, chart boundary, AI summary boundary, and collapsed governance details.
- `/queries`: protected query list route.
- `/history`: protected query lifecycle history with filters.
- `/queries/[id]`: protected saved analysis detail with stored results and collapsed governance details.
- `/audit-logs`: protected audit event list with filters.


## Analysis Experience

The primary analysis page is outcome-focused. Users select a prepared dataset, ask a question, and click `Analyze`. The frontend then calls the existing backend endpoints in order: SQL generation, validation, dry run, and controlled execution. Governance details remain available in a collapsed section titled `How this result was generated`.

AI summaries are shown only when backend-generated summary data exists. The current MVP has no summary endpoint, so the frontend displays a clear unavailable state while keeping the result table usable.

Charts are built only from returned bounded result rows when the shape is compatible with a simple bar or line chart. Unsupported result shapes fall back to the table.

## Docker

The frontend image is built from `frontend/Dockerfile` using npm and `package-lock.json`. It builds the Next.js App Router application with standalone output and runs the production server as a non-root `nextjs` user on port `3000`.

For local Docker Compose, `NEXT_PUBLIC_API_BASE_URL` is set at build time to:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

This URL is browser-facing. Do not set it to `http://backend:8000` unless the architecture changes to proxy browser requests server-side.
## Authentication Behavior

The MVP stores the backend access token in `localStorage` under `queryshield_access_token`. Protected routes call `/users/me`; missing or invalid tokens are cleared and redirected to `/login`.

This is acceptable for the local MVP but should be hardened before production, likely with secure HTTP-only cookies or a stronger session strategy.

## Major User Flows

- Sign up or log in.
- Create a dataset.
- Upload a CSV.
- Review detected schema and preview rows.
- Load the dataset into BigQuery.
- Ask a natural-language question.
- Click Analyze to generate SQL, validate safety, run a BigQuery dry run, and execute only when eligible.
- Review bounded results, history, and audit logs.
