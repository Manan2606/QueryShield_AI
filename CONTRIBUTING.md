# Contributing

## Workflow

Create a branch from `dev`, keep changes focused, and open a pull request with a clear summary of what changed and how it was tested.

## Local Setup

Follow the setup instructions in the root `README.md`, `backend/README.md`, and `frontend/README.md`.

## Coding Expectations

- Keep backend validation and authorization server-side.
- Keep frontend secrets out of `NEXT_PUBLIC_*` variables.
- Add or update tests when behavior changes.
- Include Alembic migrations when models change.
- Avoid unrelated refactors in feature or cleanup pull requests.

## Before Pull Request

- Run backend tests with `python -m pytest` from `backend/`.
- Run frontend build with `npm run build` from `frontend/`.
- Check that no secrets, local databases, uploaded CSVs, logs, or build output are staged.
- Use clear commit messages.

## Pull Request Description

Include:

- Summary of changes.
- Testing performed.
- Any migrations or environment changes.
- Known limitations or follow-up work.
