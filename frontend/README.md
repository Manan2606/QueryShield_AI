# QueryShield AI Test Console

Temporary Next.js frontend for testing the completed QueryShield AI backend from a browser.

This is not the production frontend. It intentionally avoids Gemini, natural-language questions, SQL generation, SQL validation, query execution, charts, OAuth, NextAuth, Redux, React Query, and advanced dashboards.

## Stack

- Next.js App Router
- TypeScript
- Tailwind CSS
- Native browser `fetch`
- React hooks
- `localStorage` for the temporary JWT token

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

## Run Frontend

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

This is an internal local testing frontend. Using `localStorage` for the access token is acceptable for this temporary console, but a production frontend should reconsider token storage and may use secure HTTP-only cookies.

Never store passwords, service account keys, Google credentials, or raw secrets in this frontend. Only `NEXT_PUBLIC_API_BASE_URL` belongs in frontend environment configuration.
