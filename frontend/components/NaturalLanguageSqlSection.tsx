import { FormEvent, useEffect, useState } from "react";
import * as api from "@/lib/api";
import type { Dataset, QueryDryRunResponse, QueryGenerateResponse, SQLValidationResponse } from "@/lib/types";
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
};

function validationBadgeClass(status: string): string {
  if (status === "passed") {
    return "status-badge bg-emerald-100 text-emerald-800";
  }
  if (status === "failed" || status === "error") {
    return "status-badge bg-red-100 text-red-800";
  }
  if (status === "validating") {
    return "status-badge bg-sky-100 text-sky-800";
  }
  return "status-badge bg-slate-200 text-slate-700";
}

function dryRunBadgeClass(status: string): string {
  if (status === "passed") {
    return "status-badge bg-emerald-100 text-emerald-800";
  }
  if (status === "blocked") {
    return "status-badge bg-amber-100 text-amber-800";
  }
  if (status === "failed" || status === "error") {
    return "status-badge bg-red-100 text-red-800";
  }
  if (status === "running") {
    return "status-badge bg-sky-100 text-sky-800";
  }
  return "status-badge bg-slate-200 text-slate-700";
}

function formatNumber(value: number | null): string {
  return value === null ? "Not available" : value.toLocaleString(undefined, { maximumFractionDigits: 6 });
}

function ValidationResultPanel({ result }: { result: SQLValidationResponse | null }) {
  if (!result) {
    return <span className="status-badge bg-slate-200 text-slate-700">Not validated</span>;
  }

  return (
    <div className="space-y-3 rounded-md border border-slate-200 bg-white p-3">
      <div className="flex flex-wrap items-center gap-3">
        <span className={validationBadgeClass(result.validation_status)}>{result.validation_status}</span>
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
        <span className={dryRunBadgeClass(result.dry_run_status)}>{result.dry_run_status}</span>
        <span className={result.dry_run_valid ? "status-badge bg-emerald-100 text-emerald-800" : "status-badge bg-red-100 text-red-800"}>
          {result.dry_run_valid ? "BigQuery valid" : "BigQuery invalid"}
        </span>
        <span className={result.execution_eligible ? "status-badge bg-emerald-100 text-emerald-800" : "status-badge bg-slate-200 text-slate-700"}>
          {result.execution_eligible ? "Future execution eligible" : "Not execution eligible"}
        </span>
      </div>
      <p className="text-sm font-medium text-slate-900">Dry run only - the query was not executed and no result rows were returned.</p>
      {result.bytes_limit_exceeded ? <p className="text-sm font-semibold text-amber-800">Blocked: estimated bytes exceed the configured query limit.</p> : null}
      {result.execution_eligible ? <p className="text-sm font-semibold text-emerald-800">All current pre-execution gates passed. The query has still not been executed.</p> : null}

      <dl className="grid gap-2 text-sm text-slate-700 sm:grid-cols-2">
        <div><dt className="font-semibold text-slate-900">Estimated bytes</dt><dd>{formatNumber(result.estimated_bytes_processed)}</dd></div>
        <div><dt className="font-semibold text-slate-900">Estimated MiB</dt><dd>{formatNumber(result.estimated_mib_processed)}</dd></div>
        <div><dt className="font-semibold text-slate-900">Estimated GiB</dt><dd>{formatNumber(result.estimated_gib_processed)}</dd></div>
        <div><dt className="font-semibold text-slate-900">Maximum bytes</dt><dd>{formatNumber(result.maximum_bytes_billed)}</dd></div>
        <div><dt className="font-semibold text-slate-900">Maximum MiB</dt><dd>{formatNumber(result.maximum_mib_billed)}</dd></div>
        <div><dt className="font-semibold text-slate-900">Dry-run time</dt><dd>{result.dry_run_at ? new Date(result.dry_run_at).toLocaleString() : "Not available"}</dd></div>
      </dl>

      {result.dry_run_job_id ? <p className="break-all text-sm text-slate-600">Job ID: {result.dry_run_job_id}</p> : null}
      {result.dry_run_error ? <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">{result.dry_run_error}</p> : null}

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
}: NaturalLanguageSqlSectionProps) {
  const [question, setQuestion] = useState("");
  const [copied, setCopied] = useState(false);
  const [validationResult, setValidationResult] = useState<SQLValidationResponse | null>(null);
  const [dryRunResult, setDryRunResult] = useState<QueryDryRunResponse | null>(null);
  const [validationLoading, setValidationLoading] = useState<"validate" | "stored" | null>(null);
  const [dryRunLoading, setDryRunLoading] = useState<"run" | "stored" | null>(null);

  useEffect(() => {
    setQuestion("");
    setCopied(false);
    setValidationResult(null);
    setDryRunResult(null);
  }, [dataset?.id]);

  useEffect(() => {
    setCopied(false);
    setValidationResult(null);
    setDryRunResult(null);
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

  const canGenerate = Boolean(token && dataset && question.trim() && !loading);
  const canValidate = Boolean(token && generatedQuery?.generated_sql && !validationLoading);
  const validationPassed = validationResult?.validation_status === "passed" && validationResult.is_safe === true;
  const canDryRun = Boolean(token && generatedQuery?.generated_sql && validationPassed && !dryRunLoading);

  return (
    <SectionCard title="Natural Language to SQL" description="Generate BigQuery SQL for the selected loaded dataset. Generated only - not executed.">
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
              <span className="status-badge bg-sky-100 text-sky-800">Generated only - not executed</span>
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
              </div>
              <pre className="max-h-96 overflow-auto rounded-md bg-slate-950 p-4 text-sm text-slate-100"><code>{generatedQuery.generated_sql}</code></pre>
              <ValidationResultPanel result={validationResult} />
              {validationResult?.is_safe !== true ? (
                <p className="text-sm text-slate-600">Execution-related actions remain unavailable until validation passes.</p>
              ) : null}
              <DryRunResultPanel result={dryRunResult} />
            </div>
          ) : null}
        </div>
      ) : null}
    </SectionCard>
  );
}
