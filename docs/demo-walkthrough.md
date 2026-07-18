# Demo Walkthrough

This folder contains the final demo recording and screenshots for the QueryShield AI Phase-1 MVP.

## Recording

- [QueryShield AI demo video](QueryShield_AI_Recording_Video.mp4)

## Screenshot Sequence

1. [Login and signup](screenshots/01_login_signup.png)
2. [Dashboard](screenshots/02_dashboard.png)
3. [CSV upload](screenshots/03_csv_upload.png)
4. [Natural-language query input](screenshots/04_query_input.png)
5. [Schema preview](screenshots/05_schema_preview.png)
6. [AI summary and chart](screenshots/06_ai_summary_chart.png)
7. [Query history](screenshots/07_query_history.png)
8. [Audit logs](screenshots/08_audit_logs.png)
9. [SQL validation](screenshots/09_sql_validation.png)

## Demo Flow

The recorded flow shows the core governed analytics path:

1. Create or access a QueryShield workspace account.
2. Open the dashboard and dataset workflow.
3. Upload a CSV file and review detected schema.
4. Load the dataset to BigQuery.
5. Ask a natural-language analytical question.
6. Generate SQL with Gemini.
7. Validate SQL safety and dataset ownership.
8. Run a BigQuery dry run and enforce cost limits.
9. Execute the approved query with bounded result rows.
10. Review the chart, AI summary, query history, and audit log trail.

## Notes

The demo assets are evidence for the MVP walkthrough. Local runtime files such as `.env`, SQLite databases, uploaded CSV copies, caches, virtual environments, `.next`, and `node_modules` remain intentionally excluded from Git.