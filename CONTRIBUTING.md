# Contributing

## Workflow

Create a branch from `dev`, keep changes focused, and open a pull request with a clear summary of what changed and how it was tested.

## Local Setup

Follow the setup instructions in the root `README.md`, `backend/README.md`, and `frontend/README.md`.

## Coding Expectations

- Keep backend validation, authorization, query governance, and cost controls server-side.
- Keep frontend secrets out of `NEXT_PUBLIC_*` variables.
- Do not commit real `.env` files, API keys, service-account JSON files, local databases, uploaded CSVs, virtual environments, caches, logs, or build outputs.
- Add or update tests when behavior changes.
- Include Alembic migrations when models change.
- Keep validation, dry run, and execution as distinct backend steps unless a product decision explicitly changes that contract.
- Do not fabricate AI summaries or charts; render them only from backend data or bounded returned rows.
- Avoid unrelated refactors in feature or cleanup pull requests.

## Before Pull Request

Run these checks from the repository root unless noted:

```powershell
cd backend
python -m pytest
cd ..\frontend
npm run test:charts
npm run build
cd ..
git diff --check
git status --short --ignored
```

Before pushing, confirm that only intended source, docs, migration, config template, and workflow changes are staged.

## Pull Request Description

Include:

- Summary of changes.
- Testing performed.
- Any migrations or environment changes.
- Any GCP resource or IAM assumptions.
- Known limitations or follow-up work.