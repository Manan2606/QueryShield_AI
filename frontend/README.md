# QueryShield AI Frontend

Next.js App Router frontend for the QueryShield AI Phase-1 MVP.

## Stack

- Next.js App Router
- TypeScript
- Tailwind CSS
- Native browser `fetch`
- React hooks
- `localStorage` token storage for the MVP auth guard

## Run

Start the backend first, then run:

```powershell
cd frontend
Copy-Item .env.example .env.local
npm install
npm run dev
```

Frontend: http://localhost:3000

`frontend/.env.local` should contain:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

## Routes

- `/login` and `/signup`: public authentication screens.
- `/dashboard`: protected summary of datasets and recent query lifecycle activity.
- `/datasets`: protected dataset creation, filtering, navigation, and deletion.
- `/datasets/[id]`: protected CSV upload, schema, preview, and BigQuery load workflow.
- `/queries/new`: protected governed query workspace for generate, validate, dry run, and bounded execute.
- `/history`: protected query lifecycle list with filters.
- `/queries/[id]`: protected query lifecycle detail, stored results, and audit timeline.
- `/audit-logs`: protected audit event list with filters.

Protected routes validate the stored token by calling `/users/me`. Invalid or missing tokens are cleared and redirected to `/login`.

## Security Note

Only expose `NEXT_PUBLIC_API_BASE_URL` to the browser. Do not place backend secrets, Google service account files, passwords, or raw credentials in frontend environment variables.