# GCP MVP-1 Deployment

This guide deploys QueryShield AI for the MVP-1 demo on Google Cloud. It intentionally uses Cloud Run plus SQLite demo mode instead of Cloud SQL. See [GCP Architecture](gcp-architecture.md) for the service map and runtime diagrams.

## Services Used

- Cloud Run runs the FastAPI backend and Next.js frontend as separate services.
- Artifact Registry stores backend and frontend Docker images.
- BigQuery stores uploaded analytical tables and runs dry runs plus controlled executions.
- Cloud Storage stores uploaded CSV files outside the Cloud Run filesystem.
- Secret Manager provides backend runtime secrets.
- IAM service accounts separate runtime access from deployment access.
- Cloud Logging captures Cloud Run logs.
- GitHub Actions uses Workload Identity Federation to deploy without service-account JSON keys.

## MVP-1 Database Decision

The backend Cloud Run service uses:

```env
DATABASE_URL=sqlite:////tmp/queryshield.db
```

This is acceptable only for the MVP-1 demo. Cloud Run filesystem storage is ephemeral, so signup users, query history, audit logs, and SQLite metadata can reset after restart or replacement. The backend runs Alembic migrations on production startup so a fresh `/tmp/queryshield.db` has the required schema and current migration revision before user workflows run. The backend deploy sets `--min-instances 0` to reduce cost and `--max-instances 1` to avoid multiple isolated SQLite databases.

Cloud SQL is intentionally excluded for MVP-1. Do not create Cloud SQL instances, connectors, private IP settings, or Cloud SQL deploy flags for this demo workflow.

## Repository Resource Values

The deployment workflow now requires repository variables for project-specific identifiers and identity values. It keeps generic defaults only for service names, region, sizing, and non-secret tuning values.

Set `BIGQUERY_DATASET_ID` to the existing dataset name. The app default is `queryshield_demo`, but the deployed workflow requires an explicit repository variable so accidental project drift fails before deploy.

## Required GitHub Variables

Recommended repository variables:

```text
GCP_PROJECT_ID
GCP_REGION
ARTIFACT_REGISTRY_REPO
GCP_WORKLOAD_IDENTITY_PROVIDER
GCP_DEPLOY_SERVICE_ACCOUNT
BACKEND_SERVICE
FRONTEND_SERVICE
BACKEND_SERVICE_ACCOUNT
GCS_UPLOAD_BUCKET
BIGQUERY_DATASET_ID
MAX_BYTES_BILLED
QUERY_RESULT_ROW_LIMIT
QUERY_TIMEOUT_SECONDS
GEMINI_MODEL
AI_SUMMARY_ENABLED
SUMMARY_MAX_ROWS
SUMMARY_MAX_CHARS
JWT_SECRET_NAME
GEMINI_API_KEY_SECRET_NAME
```

Do not store `JWT_SECRET_KEY`, `GEMINI_API_KEY`, service-account JSON, database passwords, or local `.env` contents in GitHub variables or repository files.

## Required Secret Manager Secrets

The backend Cloud Run service maps these Secret Manager secrets to environment variables:

```text
JWT_SECRET_KEY <- queryshield_jwt_secret:latest
GEMINI_API_KEY <- queryshield_gemini_api_key:latest
```

Secret values are not committed, printed, or baked into Docker images. The workflow supports alternate secret names through `JWT_SECRET_NAME` and `GEMINI_API_KEY_SECRET_NAME` repository variables.

## Service Accounts And IAM

The GitHub workflow authenticates as:

```text
<deploy-service-account>@<project-id>.iam.gserviceaccount.com
```

It needs scoped permissions to write Artifact Registry images, deploy Cloud Run services, and act as the backend runtime service account.

The backend runs as:

```text
<backend-service-account>@<project-id>.iam.gserviceaccount.com
```

That runtime service account needs access to the existing BigQuery dataset, BigQuery job creation, the configured upload bucket, Secret Manager secret access for the two mapped secrets, and Cloud Logging.

Minimum practical IAM for the backend runtime service account:

- BigQuery job user on the project.
- BigQuery data editor or narrower dataset-level access on the target dataset.
- Storage object admin or a narrower object role on the upload bucket.
- Secret Manager secret accessor for the mapped runtime secrets.
- Logs writer, normally granted by Cloud Run runtime defaults.

Do not grant broad Owner or Editor roles for the demo.

## Deployment Workflow

The deploy workflow is:

```text
.github/workflows/deploy-gcp.yml
```

It runs on manual dispatch and pushes to `dev`. It performs this order:

1. Validate required deployment configuration.
2. Authenticate to GCP with Workload Identity Federation.
3. Configure Docker auth for Artifact Registry.
4. Build and push the backend image.
5. Deploy the backend to Cloud Run with SQLite demo mode, Secret Manager mappings, GCS uploads, BigQuery settings, min instances 0, and max instances 1.
6. Capture the backend URL.
7. Build and push the frontend image with `NEXT_PUBLIC_API_BASE_URL` set to the backend URL.
8. Deploy the frontend to Cloud Run with min instances 0 and max instances 1.
9. Capture the frontend URL.
10. Update backend `FRONTEND_ORIGINS` to the exact frontend URL.
11. Smoke-test backend signup/login, then verify `GET /health`, `GET /health/db`, and `GET /ready` on the backend and `GET /` on the frontend.

Image names use Artifact Registry paths like:

```text
<region>-docker.pkg.dev/<project-id>/<artifact-registry-repo>/queryshield-backend:<github-sha>
<region>-docker.pkg.dev/<project-id>/<artifact-registry-repo>/queryshield-frontend:<github-sha>
```

The workflow also pushes `latest` tags for convenience.

## Runtime Environment

Backend Cloud Run environment:

```env
APP_ENV=production
DATABASE_URL=sqlite:////tmp/queryshield.db
GCP_PROJECT_ID=<project-id>
GCP_REGION=us-central1
BIGQUERY_DATASET_ID=<existing_dataset_name>
STORAGE_BACKEND=gcs
GCS_UPLOAD_BUCKET=<upload-bucket>
FRONTEND_ORIGINS=<frontend_cloud_run_url_after_deploy>
GEMINI_MODEL=gemini-2.5-flash
MAX_BYTES_BILLED=100000000
QUERY_RESULT_ROW_LIMIT=100
QUERY_TIMEOUT_SECONDS=30
AI_SUMMARY_ENABLED=true
SUMMARY_MAX_ROWS=25
SUMMARY_MAX_CHARS=6000
```

Frontend Cloud Run environment and build arg:

```env
NEXT_PUBLIC_API_BASE_URL=<backend_cloud_run_url>
```

## Verification

After deployment, verify:

```powershell
curl https://BACKEND_URL/health
curl https://BACKEND_URL/health/db
curl https://BACKEND_URL/ready
curl https://FRONTEND_URL/
```

Manual MVP checks:

1. Frontend URL opens.
2. Backend health endpoint works.
3. Signup works.
4. Login works.
5. Dataset creation works.
6. CSV upload stores the file in Cloud Storage.
7. Dataset loads into the existing BigQuery dataset.
8. Natural-language question generates SQL.
9. SQL validation runs.
10. Dry run returns an estimate.
11. Query execution works when eligible.
12. Results display.
13. AI summary displays when enabled and Gemini succeeds, or a safe fallback appears.
14. Compatible results display a chart without issuing another query.
15. Query history appears during the same Cloud Run instance lifetime.
16. Audit logs appear during the same Cloud Run instance lifetime.
17. Restarting or replacing the backend may reset SQLite metadata.

## Cost Controls

The MVP-1 workflow uses these controls:

```text
Cloud Run min instances = 0
Cloud Run max instances = 1
BigQuery MAX_BYTES_BILLED = 100000000

No GKE
No load balancer
```

Budget alerts should be configured in the GCP project. After the demo, delete Cloud Run services if not needed, remove old Artifact Registry images, delete Cloud Storage test files, and remove BigQuery test tables created for the recording.

## Cleanup

Demo cleanup commands should be reviewed before use:

```powershell
gcloud run services delete queryshield-backend --region us-central1
gcloud run services delete queryshield-frontend --region us-central1
gcloud artifacts docker images list <region>-docker.pkg.dev/<project-id>/<artifact-registry-repo>
```

Do not delete the existing BigQuery dataset or upload bucket unless that is explicitly intended.