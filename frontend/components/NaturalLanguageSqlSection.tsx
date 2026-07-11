import { FormEvent, useEffect, useState } from "react";
import * as api from "@/lib/api";
import type { Dataset, QueryDryRunResponse, QueryExecutionResponse, QueryGenerateResponse, SQLValidationResponse } from "@/lib/types";
import SectionCard from "./SectionCard";

type NaturalLanguageSqlSectionProps = {
  token: string | null;
  dataset: Dataset | null;
  generatedQuery: QueryGenerateResponse | null;
  loading: boolean;
  onGenerate: (question: string) => Promise<void>;
  onValidationResult: (operation: string, data: SQLValidationResponse) => void;
  onValidationError: (operation: string, error: unknown) => void;
  onDryRunResult: (operation: string, data: QueryDryRunResponse) => void;
  onDryRunError: (operation: string, error: unknown) => void;
  onExecutionResult: (operation: string, data: QueryExecutionResponse) => void;
  onExecutionError: (operation: string, error: unknown) => void;
};

function statusBadgeClass(status: string): string {
  if (status === "passed" || status === "succeeded") {
    return "status-badge bg-emerald-100 text-emerald-800";
  }
  if (status === "blocked") {
    return "status-badge bg-amber-100 text-amber-800";
  }
  if (status === "failed" || status === "error" || status === "timed_out") {
    return "status-badge bg-red-100 text-red-800";
  }
  if (status === "validating" || status === "running") {
    return "status-badge bg-sky-100 text-sky-800";
  }
  return "status-badge bg-slate-200 text-slate-700";
}

function formatNumber(value: number | null): string {
  return value === null ? "Not available" : value.toLocaleString(undefined, { maximumFractionDigits: 6 });
}

function formatDateTime(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "Not available";
}

function displayCell(value: unknown): string {
  if (value === null || value === undefined) {
    return "null";
  }
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function ValidationResultPanel({ result }: { result: SQLValidationResponse | null }) {
  if (!result) {
    return <span className="status-badge bg-slate-200 text-slate-700">Not validated</span>;
  }

  return (
    <div className="space-y-3 rounded-md border border-slate-200 bg-white p-3">
      <div className="flex flex-wrap items-center gap-3">
        <span className={statusBadgeClass(result.validation_status)}>{result.validation_status}</span>
        <span className={result.is_safe ? "status-badge bg-emerald-100 text-emerald-800" : "status-badge bg-red-100 text-red-800"}>
          {result.is_safe ? "Safe" : "Unsafe"}
        </span>
        {result.statement_type ? <span className="status-badge bg-slate-200 text-slate-700">{result.statement_type}</span> : null}
      </div>
      <p className="text-sm font-medium text-slate-900">Validation does not execute the query.</p>
      {result.validated_at ? <p className="text-xs text-slate-500">Validated at {new Date(result.validated_at).toLocaleString()}</p> : null}

      <div>
        <h4 className="text-xs font-semibold uppercase text-slate-500">Referenced tables</h4>
        {result.referenced_tables.length ? (
          <ul className="mt-1 space-y-1 text-sm text-slate-700">
            {result.referenced_tables.map((table) => <li className="break-all" key={table}>{table}</li>)}
          </ul>
        ) : <p className="mt-1 text-sm text-slate-600">None detected.</p>}
      </div>

      {result.errors.length ? (
        <div className="rounded-md border border-red-200 bg-red-50 p-3">
          <h4 className="text-sm font-semibold text-red-900">Validation errors</h4>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-red-800">
            {result.errors.map((error) => <li key={error}>{error}</li>)}
          </ul>
        </div>
      ) : null}

      {result.warnings.length ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-3">
          <h4 className="text-sm font-semibold text-amber-900">Validation warnings</h4>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-800">
            {result.warnings.map((warning) => <li key={warning}>{warning}</li>)}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

function DryRunResultPanel({ result }: { result: QueryDryRunResponse | null }) {
  if (!result) {
    return <span className="status-badge bg-slate-200 text-slate-700">Dry run not run</span>;
  }

  return (
    <div className="space-y-3 rounded-md border border-slate-200 bg-white p-3">
      <div className="flex flex-wrap items-center gap-3">
        <span className={statusBadgeClass(result.dry_run_status)}>{result.dry_run_status}</span>
        <span className={result.dry_run_valid ? "status-badge bg-emerald-100 text-emerald-800" : "status-badge bg-red-100 text-red-800"}>
          {result.dry_run_valid ? "BigQuery valid" : "BigQuery invalid"}
        </span>
        <span className={result.execution_eligible ? "status-badge bg-emerald-100 text-emerald-800" : "status-badge bg-slate-200 text-slate-700"}>
          {result.execution_eligible ? "Execution eligible" : "Not execution eligible"}
        </span>
      </div>
      <p className="text-sm font-medium text-slate-900">Dry run only - the query was not executed and no result rows were returned.</p>
      {result.bytes_limit_exceeded ? <p className="text-sm font-semibold text-amber-800">Blocked: estimated bytes exceed the configured query limit.</p> : null}

      <dl className="grid gap-2 text-sm text-slate-700 sm:grid-cols-2">
        <div><dt className="font-semibold text-slate-900">Estimated bytes</dt><dd>{formatNumber(result.estimated_bytes_processed)}</dd></div>
        <div><dt className="font-semibold text-slate-900">Estimated MiB</dt><dd>{formatNumber(result.estimated_mib_processed)}</dd></div>
        <div><dt className="font-semibold text-slate-900">Estimated GiB</dt><dd>{formatNumber(result.estimated_gib_processed)}</dd></div>
        <div><dt className="font-semibold text-slate-900">Maximum bytes</dt><dd>{formatNumber(result.maximum_bytes_billed)}</dd></div>
        <div><dt className="font-semibold text-slate-900">Maximum MiB</dt><dd>{formatNumber(result.maximum_mib_billed)}</dd></div>
        <div><dt className="font-semibold text-slate-900">Dry-run time</dt><dd>{formatDateTime(result.dry_run_at)}</dd></div>
      </dl>

      {result.dry_run_job_id ? <p className="break-all text-sm text-slate-600">Job ID: {result.dry_run_job_id}</p> : null}
      {result.dry_run_error ? <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">{result.dry_run_error}</p> : null}
    </div>
  );
}

function ExecutionResultPanel({ result }: { result: QueryExecutionResponse | null }) {
  if (!result) {
    return <span className="status-badge bg-slate-200 text-slate-700">Not executed</span>;
  }

  const headers = result.result_columns.length ? result.result_columns.map((column) => column.name) : Object.keys(result.result_rows[0] || {});

  return (
    <div className="space-y-3 rounded-md border border-slate-200 bg-white p-3">
      <div className="flex flex-wrap items-center gap-3">
        <span className={statusBadgeClass(result.execution_status)}>{result.execution_status}</span>
        <span className={result.result_truncated ? "status-badge bg-amber-100 text-amber-800" : "status-badge bg-slate-200 text-slate-700"}>
          {result.result_truncated ? "Truncated" : "Not truncated"}
        </span>
      </div>

      <dl className="grid gap-2 text-sm text-slate-700 sm:grid-cols-2 lg:grid-cols-3">
        <div><dt className="font-semibold text-slate-900">Job ID</dt><dd className="break-all">{result.execution_job_id || "Not available"}</dd></div>
        <div><dt className="font-semibold text-slate-900">Location</dt><dd>{result.execution_location || "Not available"}</dd></div>
        <div><dt className="font-semibold text-slate-900">Bytes processed</dt><dd>{formatNumber(result.execution_bytes_processed)}</dd></div>
        <div><dt className="font-semibold text-slate-900">Bytes billed</dt><dd>{formatNumber(result.execution_bytes_billed)}</dd></div>
        <div><dt className="font-semibold text-slate-900">Cache hit</dt><dd>{result.execution_cache_hit === null ? "Not available" : String(result.execution_cache_hit)}</dd></div>
        <div><dt className="font-semibold text-slate-900">Returned rows</dt><dd>{result.result_row_count.toLocaleString()}</dd></div>
        <div><dt className="font-semibold text-slate-900">Started</dt><dd>{formatDateTime(result.execution_started_at)}</dd></div>
        <div><dt className="font-semibold text-slate-900">Completed</dt><dd>{formatDateTime(result.execution_completed_at)}</dd></div>
        <div><dt className="font-semibold text-slate-900">Row limit</dt><dd>{result.row_limit.toLocaleString()}</dd></div>
      </dl>

      {result.execution_error ? <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">{result.execution_error}</p> : null}
      {result.result_truncated ? <p className="text-sm font-semibold text-amber-800">Only the first {result.row_limit.toLocaleString()} rows are displayed.</p> : null}

      {headers.length ? (
        <div className="overflow-x-auto rounded-md border border-slate-200">
          <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
            <thead className="bg-slate-100 text-xs uppercase text-slate-600">
              <tr>{headers.map((header) => <th className="px-3 py-2 font-semibold" key={header}>{header}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white text-slate-700">
              {result.result_rows.map((row, index) => (
                <tr key={`${result.query_request_id}-${index}`}>
                  {headers.map((header) => <td className="max-w-xs whitespace-pre-wrap px-3 py-2 align-top" key={header}>{displayCell(row[header])}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <p className="text-sm text-slate-600">No rows returned.</p>}
    </div>
  );
}

export default function NaturalLanguageSqlSection({
  token,
  dataset,
  generatedQuery,
  loading,
  onGenerate,
  onValidationResult,
  onValidationError,
  onDryRunResult,
  onDryRunError,
  onExecutionResult,
  onExecutionError,
}: NaturalLanguageSqlSectionProps) {
  const [question, setQuestion] = useState("");
  const [copied, setCopied] = useState(false);
  const [validationResult, setValidationResult] = useState<SQLValidationResponse | null>(null);
  const [dryRunResult, setDryRunResult] = useState<QueryDryRunResponse | null>(null);
  const [executionResult, setExecutionResult] = useState<QueryExecutionResponse | null>(null);
  const [validationLoading, setValidationLoading] = useState<"validate" | "stored" | null>(null);
  const [dryRunLoading, setDryRunLoading] = useState<"run" | "stored" | null>(null);
  const [executionLoading, setExecutionLoading] = useState<"execute" | "stored" | null>(null);

  useEffect(() => {
    setQuestion("");
    setCopied(false);
    setValidationResult(null);
    setDryRunResult(null);
    setExecutionResult(null);
  }, [dataset?.id]);

  useEffect(() => {
    setCopied(false);
    setValidationResult(null);
    setDryRunResult(null);
    setExecutionResult(null);
  }, [generatedQuery?.id]);

  async function submitGenerate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onGenerate(question);
  }

  async function copySql() {
    if (!generatedQuery?.generated_sql) {
      return;
    }
    await navigator.clipboard.writeText(generatedQuery.generated_sql);
    setCopied(true);
  }

  async function validateSql() {
    if (!token || !generatedQuery) {
      return;
    }
    const operation = `POST /queries/${generatedQuery.id}/validate`;
    setValidationLoading("validate");
    try {
      const data = await api.validateSql(token, generatedQuery.id);
      setValidationResult(data);
      setDryRunResult(null);
      setExecutionResult(null);
      onValidationResult(operation, data);
    } catch (error) {
      onValidationError(operation, error);
    } finally {
      setValidationLoading(null);
    }
  }

  async function viewStoredValidation() {
    if (!token || !generatedQuery) {
      return;
    }
    const operation = `GET /queries/${generatedQuery.id}/validation`;
    setValidationLoading("stored");
    try {
      const data = await api.getSqlValidation(token, generatedQuery.id);
      setValidationResult(data);
      onValidationResult(operation, data);
    } catch (error) {
      onValidationError(operation, error);
    } finally {
      setValidationLoading(null);
    }
  }

  async function runCostDryRun() {
    if (!token || !generatedQuery) {
      return;
    }
    const operation = `POST /queries/${generatedQuery.id}/dry-run`;
    setDryRunLoading("run");
    try {
      const data = await api.runCostDryRun(token, generatedQuery.id);
      setDryRunResult(data);
      setExecutionResult(null);
      onDryRunResult(operation, data);
    } catch (error) {
      onDryRunError(operation, error);
    } finally {
      setDryRunLoading(null);
    }
  }

  async function viewStoredDryRun() {
    if (!token || !generatedQuery) {
      return;
    }
    const operation = `GET /queries/${generatedQuery.id}/dry-run`;
    setDryRunLoading("stored");
    try {
      const data = await api.getCostDryRun(token, generatedQuery.id);
      setDryRunResult(data);
      onDryRunResult(operation, data);
    } catch (error) {
      onDryRunError(operation, error);
    } finally {
      setDryRunLoading(null);
    }
  }

  async function executeStoredQuery() {
    if (!token || !generatedQuery || !dryRunResult?.execution_eligible) {
      return;
    }
    const confirmed = window.confirm("This will execute the validated query in BigQuery. The configured maximum bytes billed and row limit will be enforced.");
    if (!confirmed) {
      return;
    }
    const operation = `POST /queries/${generatedQuery.id}/execute`;
    setExecutionLoading("execute");
    try {
      const data = await api.executeQuery(token, generatedQuery.id);
      setExecutionResult(data);
      onExecutionResult(operation, data);
    } catch (error) {
      onExecutionError(operation, error);
    } finally {
      setExecutionLoading(null);
    }
  }

  async function viewStoredExecution() {
    if (!token || !generatedQuery) {
      return;
    }
    const operation = `GET /queries/${generatedQuery.id}/execution`;
    setExecutionLoading("stored");
    try {
      const data = await api.getQueryExecution(token, generatedQuery.id);
      setExecutionResult(data);
      onExecutionResult(operation, data);
    } catch (error) {
      onExecutionError(operation, error);
    } finally {
      setExecutionLoading(null);
    }
  }

  const canGenerate = Boolean(token && dataset && question.trim() && !loading);
  const canValidate = Boolean(token && generatedQuery?.generated_sql && !validationLoading);
  const validationPassed = validationResult?.validation_status === "passed" && validationResult.is_safe === true;
  const canDryRun = Boolean(token && generatedQuery?.generated_sql && validationPassed && !dryRunLoading);
  const executionEligible = dryRunResult?.dry_run_status === "passed" && dryRunResult.dry_run_valid && dryRunResult.execution_eligible;
  const canExecute = Boolean(token && generatedQuery?.generated_sql && executionEligible && !executionLoading);

  return (
    <SectionCard title="Natural Language to SQL" description="Generate, validate, dry run, and execute eligible stored BigQuery SQL for the selected loaded dataset.">
      {!token ? <p className="text-sm text-amber-700">Log in before generating SQL.</p> : null}
      {!dataset ? <p className="text-sm text-slate-600">Select a dataset before generating SQL.</p> : null}
      {dataset ? (
        <div className="space-y-4">
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-sm font-semibold text-slate-900">{dataset.name}</span>
              <span className="status-badge bg-slate-200 text-slate-700">{dataset.status}</span>
            </div>
            <p className="mt-2 break-all text-sm text-slate-600">{dataset.bigquery_table_id || "No BigQuery table ID"}</p>
          </div>

          <form className="space-y-3" onSubmit={submitGenerate}>
            <label className="field-label">Analytics question
              <textarea
                className="input-field min-h-28 resize-y"
                disabled={!token || !dataset}
                maxLength={2000}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="What is the total sales amount by region?"
                value={question}
              />
            </label>
            <div className="flex flex-wrap items-center gap-3">
              <button className="btn-primary" disabled={!canGenerate} type="submit">
                {loading ? "Generating SQL..." : "Generate SQL"}
              </button>
              <span className="status-badge bg-sky-100 text-sky-800">Stored SQL workflow</span>
            </div>
          </form>

          {generatedQuery ? (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-3">
                <h3 className="text-sm font-semibold text-slate-900">Generated SQL</h3>
                <button className="btn-secondary" onClick={copySql} type="button">{copied ? "Copied" : "Copy SQL"}</button>
                <button className="btn-primary" disabled={!canValidate} onClick={validateSql} type="button">
                  {validationLoading === "validate" ? "Validating..." : "Validate SQL"}
                </button>
                <button className="btn-secondary" disabled={!canValidate} onClick={viewStoredValidation} type="button">
                  {validationLoading === "stored" ? "Loading..." : "View Stored Validation"}
                </button>
                <button className="btn-primary" disabled={!canDryRun} onClick={runCostDryRun} type="button">
                  {dryRunLoading === "run" ? "Running dry run..." : "Run Cost Dry Run"}
                </button>
                <button className="btn-secondary" disabled={!token || !generatedQuery || Boolean(dryRunLoading)} onClick={viewStoredDryRun} type="button">
                  {dryRunLoading === "stored" ? "Loading..." : "View Stored Dry Run"}
                </button>
                <button className="btn-primary" disabled={!canExecute} onClick={executeStoredQuery} type="button">
                  {executionLoading === "execute" ? "Executing..." : "Execute Query"}
                </button>
                <button className="btn-secondary" disabled={!token || !generatedQuery || Boolean(executionLoading)} onClick={viewStoredExecution} type="button">
                  {executionLoading === "stored" ? "Loading..." : "View Stored Execution"}
                </button>
              </div>
              <pre className="max-h-96 overflow-auto rounded-md bg-slate-950 p-4 text-sm text-slate-100"><code>{generatedQuery.generated_sql}</code></pre>
              <ValidationResultPanel result={validationResult} />
              {validationResult?.is_safe !== true ? <p className="text-sm text-slate-600">Dry run and execution remain unavailable until validation passes.</p> : null}
              <DryRunResultPanel result={dryRunResult} />
              <ExecutionResultPanel result={executionResult} />
            </div>
          ) : null}
        </div>
      ) : null}
    </SectionCard>
  );
}
