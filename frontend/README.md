# QueryShield AI Frontend

Next.js App Router frontend for the QueryShield AI Phase-1 MVP.

## Responsibilities

- Provide public login and signup screens.
- Guard authenticated application routes.
- Manage dataset creation, upload, schema preview, and BigQuery load workflows.
- Run the governed query workflow: generate, validate, dry run, execute.
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
- `/queries/new`: protected governed query workspace.
- `/queries`: protected query list route.
- `/history`: protected query lifecycle history with filters.
- `/queries/[id]`: protected query lifecycle detail, stored results, and audit timeline.
- `/audit-logs`: protected audit event list with filters.

## Authentication Behavior

The MVP stores the backend access token in `localStorage` under `queryshield_access_token`. Protected routes call `/users/me`; missing or invalid tokens are cleared and redirected to `/login`.

This is acceptable for the local MVP but should be hardened before production, likely with secure HTTP-only cookies or a stronger session strategy.

## Major User Flows

- Sign up or log in.
- Create a dataset.
- Upload a CSV.
- Review detected schema and preview rows.
- Load the dataset into BigQuery.
- Generate SQL from a natural-language question.
- Validate SQL safety.
- Run a BigQuery dry run.
- Execute eligible queries only.
- Review bounded results, history, and audit logs.
