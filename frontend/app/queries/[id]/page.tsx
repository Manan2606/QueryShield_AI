"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import AppShell from "@/components/mvp/AppShell";
import ErrorAlert from "@/components/mvp/ErrorAlert";
import QueryPipeline from "@/components/mvp/QueryPipeline";
import ResultTable from "@/components/mvp/ResultTable";
import StatusBadge from "@/components/mvp/StatusBadge";
import { displayCell, formatDate, formatNumber } from "@/components/mvp/format";
import * as api from "@/lib/api";
import type { AuditLog, QueryLifecycleResponse } from "@/lib/types";

export default function QueryDetailPage() {
  const params = useParams<{ id: string }>();
  const queryId = Number(params.id);
  return <AppShell title="Query Detail">{({ token }) => <QueryDetailContent queryId={queryId} token={token} />}</AppShell>;
}

function QueryDetailContent({ token, queryId }: { token: string; queryId: number }) {
  const [lifecycle, setLifecycle] = useState<QueryLifecycleResponse | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [nextLifecycle, nextAudit] = await Promise.all([
        api.getQueryLifecycle(token, queryId),
        api.getQueryAuditLogs(token, queryId),
      ]);
      setLifecycle(nextLifecycle);
      setAuditLogs(nextAudit.items);
    } catch (err) {
      setError(err instanceof api.ApiError ? err.message : "Query detail failed to load.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [token, queryId]);

  const statuses = useMemo(() => lifecycle ? [lifecycle.generation.status, lifecycle.validation.status, lifecycle.dry_run.status, lifecycle.execution.status] : ["waiting", "waiting", "waiting", "waiting"], [lifecycle]);

  if (loading) {
    return <div className="app-surface p-4 text-sm text-slate-600">Loading query...</div>;
  }

  if (!lifecycle) {
    return <ErrorAlert message={error || "Query not found."} />;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <Link className="text-sm font-semibold text-indigo-700" href="/history">Back to history</Link>
          <h2 className="mt-2 text-xl font-bold text-slate-950">Query {lifecycle.query.id}</h2>
          <p className="mt-1 max-w-3xl text-sm text-slate-700">{lifecycle.query.question}</p>
          <p className="mt-1 text-xs text-slate-500">{lifecycle.query.dataset_name || "Dataset unavailable"} - {formatDate(lifecycle.query.created_at)}</p>
        </div>
        <button className="btn-secondary" onClick={() => void load()} type="button">Refresh</button>
      </div>
      <ErrorAlert message={error} />
      <QueryPipeline statuses={statuses} />

      <section className="grid gap-6 xl:grid-cols-2">
        <div className="app-surface p-4">
          <div className="flex flex-wrap items-center gap-2"><h3 className="text-base font-bold text-slate-950">Generation</h3><StatusBadge status={lifecycle.generation.status} /></div>
          <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2"><div><dt className="font-semibold text-slate-900">Model</dt><dd>{lifecycle.generation.model_name || "Not available"}</dd></div><div><dt className="font-semibold text-slate-900">Table</dt><dd className="break-all">{lifecycle.generation.generated_for_table_id || lifecycle.query.bigquery_table_id || "Not available"}</dd></div></dl>
          {lifecycle.generation.error_message ? <p className="mt-3 text-sm text-red-700">{lifecycle.generation.error_message}</p> : null}
          <pre className="mt-4 max-h-80 overflow-auto rounded-md bg-slate-950 p-4 text-sm text-slate-100"><code>{lifecycle.generation.generated_sql || "No SQL generated"}</code></pre>
        </div>

        <div className="app-surface p-4">
          <div className="flex flex-wrap items-center gap-2"><h3 className="text-base font-bold text-slate-950">Validation</h3><StatusBadge status={lifecycle.validation.status} /><StatusBadge status={lifecycle.validation.is_safe ? "safe" : "blocked"} /></div>
          <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2"><div><dt className="font-semibold text-slate-900">Statement</dt><dd>{lifecycle.validation.statement_type || "Not available"}</dd></div><div><dt className="font-semibold text-slate-900">Validated</dt><dd>{formatDate(lifecycle.validation.validated_at)}</dd></div><div className="sm:col-span-2"><dt className="font-semibold text-slate-900">Referenced tables</dt><dd>{lifecycle.validation.referenced_tables.join(", ") || "None"}</dd></div></dl>
          {lifecycle.validation.errors.length ? <p className="mt-3 text-sm text-red-700">{lifecycle.validation.errors.join(", ")}</p> : null}
          {lifecycle.validation.warnings.length ? <p className="mt-3 text-sm text-amber-700">{lifecycle.validation.warnings.join(", ")}</p> : null}
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <div className="app-surface p-4">
          <div className="flex flex-wrap items-center gap-2"><h3 className="text-base font-bold text-slate-950">Dry run</h3><StatusBadge status={lifecycle.dry_run.status} /><StatusBadge status={lifecycle.dry_run.execution_eligible ? "eligible" : "blocked"} /></div>
          <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2"><div><dt className="font-semibold text-slate-900">Estimated bytes</dt><dd>{formatNumber(lifecycle.dry_run.estimated_bytes_processed)}</dd></div><div><dt className="font-semibold text-slate-900">Maximum bytes</dt><dd>{formatNumber(lifecycle.dry_run.maximum_bytes_billed)}</dd></div><div><dt className="font-semibold text-slate-900">Checked</dt><dd>{formatDate(lifecycle.dry_run.dry_run_at)}</dd></div><div><dt className="font-semibold text-slate-900">Job</dt><dd className="break-all">{lifecycle.dry_run.dry_run_job_id || "Not available"}</dd></div></dl>
          {lifecycle.dry_run.dry_run_error ? <p className="mt-3 text-sm text-red-700">{lifecycle.dry_run.dry_run_error}</p> : null}
        </div>

        <div className="app-surface p-4">
          <div className="flex flex-wrap items-center gap-2"><h3 className="text-base font-bold text-slate-950">Execution</h3><StatusBadge status={lifecycle.execution.status} />{lifecycle.execution.result_truncated ? <StatusBadge status="truncated" /> : null}</div>
          <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2"><div><dt className="font-semibold text-slate-900">Rows</dt><dd>{formatNumber(lifecycle.execution.result_row_count)}</dd></div><div><dt className="font-semibold text-slate-900">Bytes processed</dt><dd>{formatNumber(lifecycle.execution.execution_bytes_processed)}</dd></div><div><dt className="font-semibold text-slate-900">Executed</dt><dd>{formatDate(lifecycle.execution.executed_at)}</dd></div><div><dt className="font-semibold text-slate-900">Job</dt><dd className="break-all">{lifecycle.execution.execution_job_id || "Not available"}</dd></div></dl>
          {lifecycle.execution.execution_error ? <p className="mt-3 text-sm text-red-700">{lifecycle.execution.execution_error}</p> : null}
        </div>
      </section>

      <section className="app-surface p-4">
        <h3 className="text-base font-bold text-slate-950">Bounded results</h3>
        <div className="mt-4"><ResultTable columns={lifecycle.execution.result_columns} rows={lifecycle.execution.result_rows} /></div>
      </section>

      <section className="app-surface p-4">
        <h3 className="text-base font-bold text-slate-950">Audit timeline</h3>
        <ol className="mt-4 space-y-3 border-l border-slate-200 pl-4 text-sm">
          {auditLogs.map((log) => <li key={log.id}><div className="font-semibold text-slate-900">{formatDate(log.created_at)} - {log.action}</div>{log.details ? <pre className="mt-1 overflow-auto rounded-md bg-slate-50 p-2 text-xs text-slate-700">{displayCell(log.details)}</pre> : null}</li>)}
        </ol>
        {!auditLogs.length ? <p className="mt-4 text-sm text-slate-600">No audit events recorded.</p> : null}
      </section>
    </div>
  );
}