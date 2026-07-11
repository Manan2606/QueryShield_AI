"use client";

import Link from "next/link";
import { FormEvent, Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import AppShell from "@/components/mvp/AppShell";
import EmptyState from "@/components/mvp/EmptyState";
import ErrorAlert from "@/components/mvp/ErrorAlert";
import QueryPipeline from "@/components/mvp/QueryPipeline";
import ResultTable from "@/components/mvp/ResultTable";
import StatusBadge from "@/components/mvp/StatusBadge";
import { formatDate, formatNumber } from "@/components/mvp/format";
import * as api from "@/lib/api";
import type { Dataset, QueryDryRunResponse, QueryExecutionResponse, QueryGenerateResponse, SQLValidationResponse } from "@/lib/types";

export default function NewQueryPage() {
  return (
    <AppShell title="Ask Query">
      {({ token }) => (
        <Suspense fallback={<div className="app-surface p-4 text-sm text-slate-600">Loading query workspace...</div>}>
          <NewQueryContent token={token} />
        </Suspense>
      )}
    </AppShell>
  );
}

function NewQueryContent({ token }: { token: string }) {
  const searchParams = useSearchParams();
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [datasetId, setDatasetId] = useState(searchParams.get("dataset_id") || "");
  const [question, setQuestion] = useState("");
  const [generated, setGenerated] = useState<QueryGenerateResponse | null>(null);
  const [validation, setValidation] = useState<SQLValidationResponse | null>(null);
  const [dryRun, setDryRun] = useState<QueryDryRunResponse | null>(null);
  const [execution, setExecution] = useState<QueryExecutionResponse | null>(null);
  const [loading, setLoading] = useState<string | null>("datasets");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    async function load() {
      setLoading("datasets");
      setError(null);
      try {
        const data = await api.listDatasets(token);
        if (!mounted) return;
        setDatasets(data);
      } catch (err) {
        if (mounted) setError(err instanceof api.ApiError ? err.message : "Datasets failed to load.");
      } finally {
        if (mounted) setLoading(null);
      }
    }
    void load();
    return () => { mounted = false; };
  }, [token]);

  const loadedDatasets = useMemo(() => datasets.filter((dataset) => dataset.status === "loaded"), [datasets]);
  const selectedDataset = datasets.find((dataset) => String(dataset.id) === datasetId) || null;
  const queryId = generated?.id || validation?.query_request_id || dryRun?.query_request_id || execution?.query_request_id || null;
  const canValidate = Boolean(queryId && generated?.generated_sql && !validation);
  const canDryRun = Boolean(queryId && validation?.is_safe && validation.validation_status === "passed" && !dryRun);
  const canExecute = Boolean(queryId && dryRun?.execution_eligible && dryRun.dry_run_status === "passed" && !execution);

  function resetPipeline() {
    setGenerated(null);
    setValidation(null);
    setDryRun(null);
    setExecution(null);
  }

  async function generate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading("generate");
    setError(null);
    resetPipeline();
    try {
      setGenerated(await api.generateSql(token, { dataset_id: Number(datasetId), question }));
    } catch (err) {
      setError(err instanceof api.ApiError ? err.message : "SQL generation failed.");
    } finally {
      setLoading(null);
    }
  }

  async function validate() {
    if (!queryId) return;
    setLoading("validate");
    setError(null);
    try {
      setValidation(await api.validateSql(token, queryId));
    } catch (err) {
      setError(err instanceof api.ApiError ? err.message : "SQL validation failed.");
    } finally {
      setLoading(null);
    }
  }

  async function dryRunQuery() {
    if (!queryId) return;
    setLoading("dry-run");
    setError(null);
    try {
      setDryRun(await api.runCostDryRun(token, queryId));
    } catch (err) {
      setError(err instanceof api.ApiError ? err.message : "Dry run failed.");
    } finally {
      setLoading(null);
    }
  }

  async function execute() {
    if (!queryId || !window.confirm("Execute this validated, dry-run-approved query with bounded results?")) return;
    setLoading("execute");
    setError(null);
    try {
      setExecution(await api.executeQuery(token, queryId, { row_limit: 100 }));
    } catch (err) {
      setError(err instanceof api.ApiError ? err.message : "Query execution failed.");
    } finally {
      setLoading(null);
    }
  }

  const statuses = [generated?.status, validation?.validation_status, dryRun?.dry_run_status, execution?.execution_status].map((status) => status || "waiting");

  return (
    <div className="space-y-6">
      <ErrorAlert message={error} />
      <QueryPipeline statuses={statuses} />

      <section className="app-surface p-4">
        <h2 className="text-base font-bold text-slate-950">Question</h2>
        <form className="mt-4 space-y-4" onSubmit={generate}>
          <label className="field-label">Loaded dataset
            <select className="input-field" required value={datasetId} onChange={(event) => { setDatasetId(event.target.value); resetPipeline(); }}>
              <option value="">Select a loaded dataset</option>
              {loadedDatasets.map((dataset) => <option key={dataset.id} value={dataset.id}>{dataset.name}</option>)}
            </select>
          </label>
          {selectedDataset ? <p className="text-sm text-slate-600">{selectedDataset.bigquery_table_id || "No BigQuery table recorded"} - {formatNumber(selectedDataset.row_count)} rows</p> : null}
          {!loadedDatasets.length && loading !== "datasets" ? <EmptyState title="Load a CSV dataset to BigQuery before asking questions" action={<Link className="btn-primary" href="/datasets">Open datasets</Link>} /> : null}
          <label className="field-label">Natural language question
            <textarea className="input-field min-h-28" required value={question} onChange={(event) => { setQuestion(event.target.value); resetPipeline(); }} placeholder="Example: Show the top 10 customers by revenue" />
          </label>
          <button className="btn-primary" disabled={!datasetId || !question.trim() || loading === "generate"} type="submit">{loading === "generate" ? "Generating..." : "Generate SQL"}</button>
        </form>
      </section>

      {generated ? <section className="app-surface p-4"><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-base font-bold text-slate-950">Generated SQL</h2><StatusBadge status={generated.status} /></div><pre className="mt-4 max-h-80 overflow-auto rounded-md bg-slate-950 p-4 text-sm text-slate-100"><code>{generated.generated_sql}</code></pre><div className="mt-4 flex flex-wrap gap-3"><button className="btn-primary" disabled={!canValidate || loading === "validate"} onClick={validate} type="button">{loading === "validate" ? "Validating..." : "Validate"}</button>{queryId ? <Link className="btn-secondary" href={`/queries/${queryId}`}>Open detail</Link> : null}</div></section> : null}

      {validation ? <section className="app-surface p-4"><div className="flex flex-wrap items-center gap-2"><h2 className="text-base font-bold text-slate-950">Validation</h2><StatusBadge status={validation.validation_status} /><StatusBadge status={validation.is_safe ? "safe" : "blocked"} /></div><dl className="mt-4 grid gap-3 text-sm sm:grid-cols-3"><div><dt className="font-semibold text-slate-900">Statement</dt><dd>{validation.statement_type || "Not available"}</dd></div><div><dt className="font-semibold text-slate-900">Validated</dt><dd>{formatDate(validation.validated_at)}</dd></div><div><dt className="font-semibold text-slate-900">Referenced tables</dt><dd>{validation.referenced_tables.join(", ") || "None"}</dd></div></dl>{validation.errors.length ? <p className="mt-3 text-sm text-red-700">{validation.errors.join(", ")}</p> : null}{validation.warnings.length ? <p className="mt-3 text-sm text-amber-700">{validation.warnings.join(", ")}</p> : null}<button className="btn-primary mt-4" disabled={!canDryRun || loading === "dry-run"} onClick={dryRunQuery} type="button">{loading === "dry-run" ? "Checking cost..." : "Run dry run"}</button></section> : null}

      {dryRun ? <section className="app-surface p-4"><div className="flex flex-wrap items-center gap-2"><h2 className="text-base font-bold text-slate-950">Dry run</h2><StatusBadge status={dryRun.dry_run_status} /><StatusBadge status={dryRun.execution_eligible ? "eligible" : "blocked"} /></div><dl className="mt-4 grid gap-3 text-sm sm:grid-cols-4"><div><dt className="font-semibold text-slate-900">Estimated bytes</dt><dd>{formatNumber(dryRun.estimated_bytes_processed)}</dd></div><div><dt className="font-semibold text-slate-900">Maximum bytes</dt><dd>{formatNumber(dryRun.maximum_bytes_billed)}</dd></div><div><dt className="font-semibold text-slate-900">Checked</dt><dd>{formatDate(dryRun.dry_run_at)}</dd></div><div><dt className="font-semibold text-slate-900">Job</dt><dd className="break-all">{dryRun.dry_run_job_id || "Not available"}</dd></div></dl>{dryRun.dry_run_error ? <p className="mt-3 text-sm text-red-700">{dryRun.dry_run_error}</p> : null}<button className="btn-warning mt-4" disabled={!canExecute || loading === "execute"} onClick={execute} type="button">{loading === "execute" ? "Executing..." : "Execute bounded query"}</button></section> : null}

      {execution ? <section className="app-surface p-4"><div className="flex flex-wrap items-center gap-2"><h2 className="text-base font-bold text-slate-950">Results</h2><StatusBadge status={execution.execution_status} />{execution.result_truncated ? <StatusBadge status="truncated" /> : null}</div><dl className="mt-4 grid gap-3 text-sm sm:grid-cols-4"><div><dt className="font-semibold text-slate-900">Rows</dt><dd>{formatNumber(execution.result_row_count)}</dd></div><div><dt className="font-semibold text-slate-900">Bytes processed</dt><dd>{formatNumber(execution.execution_bytes_processed)}</dd></div><div><dt className="font-semibold text-slate-900">Executed</dt><dd>{formatDate(execution.executed_at)}</dd></div><div><dt className="font-semibold text-slate-900">Job</dt><dd className="break-all">{execution.execution_job_id || "Not available"}</dd></div></dl>{execution.execution_error ? <p className="mt-3 text-sm text-red-700">{execution.execution_error}</p> : null}<div className="mt-4"><ResultTable columns={execution.result_columns} rows={execution.result_rows} /></div></section> : null}
    </div>
  );
}