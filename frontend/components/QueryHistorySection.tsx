import { FormEvent, useEffect, useState } from "react";
import * as api from "@/lib/api";
import type { AuditLog, AuditLogListResponse, Dataset, QueryHistoryListResponse, QueryLifecycleResponse } from "@/lib/types";
import SectionCard from "./SectionCard";

type QueryHistorySectionProps = {
  token: string | null;
  datasets: Dataset[];
  onResult: (operation: string, data: unknown) => void;
  onError: (operation: string, error: unknown) => void;
};

const STATUS_OPTIONS = ["", "pending", "generated", "failed", "not_validated", "validating", "passed", "error", "not_run", "running", "blocked", "not_executed", "succeeded", "timed_out"];

function badgeClass(status: string | null | undefined): string {
  if (!status) {
    return "status-badge bg-slate-200 text-slate-700";
  }
  if (["generated", "passed", "succeeded"].includes(status)) {
    return "status-badge bg-emerald-100 text-emerald-800";
  }
  if (["blocked", "timed_out"].includes(status)) {
    return "status-badge bg-amber-100 text-amber-800";
  }
  if (["failed", "error"].includes(status)) {
    return "status-badge bg-red-100 text-red-800";
  }
  if (["pending", "validating", "running"].includes(status)) {
    return "status-badge bg-sky-100 text-sky-800";
  }
  return "status-badge bg-slate-200 text-slate-700";
}

function formatNumber(value: number | null | undefined): string {
  return value === null || value === undefined ? "Not available" : value.toLocaleString();
}

function formatDate(value: string | null | undefined): string {
  return value ? new Date(value).toLocaleString() : "Not available";
}

function displayValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "null";
  }
  if (["string", "number", "boolean"].includes(typeof value)) {
    return String(value);
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function ResultTable({ lifecycle }: { lifecycle: QueryLifecycleResponse }) {
  const rows = lifecycle.execution.result_rows;
  const headers = lifecycle.execution.result_columns.length ? lifecycle.execution.result_columns.map((column) => column.name) : Object.keys(rows[0] || {});
  if (!headers.length) {
    return <p className="text-sm text-slate-600">No result rows stored.</p>;
  }

  return (
    <div className="table-shell">
      <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
        <thead className="bg-slate-50 text-xs uppercase text-slate-500">
          <tr>{headers.map((header) => <th className="px-3 py-2 font-semibold" key={header}>{header}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white text-slate-700">
          {rows.map((row, index) => (
            <tr key={`${lifecycle.query.id}-${index}`}>
              {headers.map((header) => <td className="max-w-xs whitespace-pre-wrap px-3 py-2 align-top" key={header}>{displayValue(row[header])}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AuditTimeline({ auditLogs }: { auditLogs: AuditLog[] }) {
  if (!auditLogs.length) {
    return <p className="text-sm text-slate-600">No audit events found.</p>;
  }
  return (
    <ol className="space-y-2 border-l border-slate-200 pl-4 text-sm">
      {auditLogs.map((event) => (
        <li key={event.id}>
          <div className="font-medium text-slate-900">{formatDate(event.created_at)} - {event.action}</div>
          {event.details ? <pre className="mt-1 overflow-auto rounded-md bg-slate-50 p-2 text-xs text-slate-700">{JSON.stringify(event.details, null, 2)}</pre> : null}
        </li>
      ))}
    </ol>
  );
}

function LifecycleDetails({ lifecycle, auditLogs }: { lifecycle: QueryLifecycleResponse | null; auditLogs: AuditLog[] }) {
  if (!lifecycle) {
    return <p className="text-sm text-slate-600">Select a query to view its full lifecycle.</p>;
  }

  return (
    <div className="space-y-4 app-surface p-4">
      <div>
        <h3 className="text-base font-bold text-slate-950">Query {lifecycle.query.id}</h3>
        <p className="mt-1 text-sm text-slate-700">{lifecycle.query.question}</p>
        <p className="mt-1 text-xs text-slate-500">{lifecycle.query.dataset_name || "Dataset no longer available"} - {lifecycle.query.bigquery_table_id || "No table ID"}</p>
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <section className="space-y-2 rounded-md border border-slate-200 p-3">
          <h4 className="text-sm font-semibold text-slate-900">Generation</h4>
          <span className={badgeClass(lifecycle.generation.status)}>{lifecycle.generation.status}</span>
          <p className="text-sm text-slate-600">Model: {lifecycle.generation.model_name || "Not available"}</p>
          {lifecycle.generation.error_message ? <p className="text-sm text-red-700">{lifecycle.generation.error_message}</p> : null}
          <pre className="max-h-64 overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-100"><code>{lifecycle.generation.generated_sql || "No SQL generated"}</code></pre>
        </section>

        <section className="space-y-2 rounded-md border border-slate-200 p-3">
          <h4 className="text-sm font-semibold text-slate-900">Validation</h4>
          <div className="flex flex-wrap gap-2">
            <span className={badgeClass(lifecycle.validation.status)}>{lifecycle.validation.status}</span>
            <span className={lifecycle.validation.is_safe ? "status-badge bg-emerald-100 text-emerald-800" : "status-badge bg-slate-200 text-slate-700"}>{lifecycle.validation.is_safe ? "Safe" : "Not safe"}</span>
          </div>
          <p className="text-sm text-slate-600">Statement: {lifecycle.validation.statement_type || "Not available"}</p>
          {lifecycle.validation.errors.length ? <p className="text-sm text-red-700">Errors: {lifecycle.validation.errors.join(", ")}</p> : null}
          {lifecycle.validation.warnings.length ? <p className="text-sm text-amber-700">Warnings: {lifecycle.validation.warnings.join(", ")}</p> : null}
        </section>

        <section className="space-y-2 rounded-md border border-slate-200 p-3">
          <h4 className="text-sm font-semibold text-slate-900">Dry Run</h4>
          <span className={badgeClass(lifecycle.dry_run.status)}>{lifecycle.dry_run.status}</span>
          <dl className="grid gap-2 text-sm text-slate-700 sm:grid-cols-2">
            <div><dt className="font-medium text-slate-900">Estimated bytes</dt><dd>{formatNumber(lifecycle.dry_run.estimated_bytes_processed)}</dd></div>
            <div><dt className="font-medium text-slate-900">Estimated cost</dt><dd>{lifecycle.dry_run.estimated_cost || "Not available"} {lifecycle.dry_run.estimated_cost_currency || ""}</dd></div>
            <div><dt className="font-medium text-slate-900">Max bytes</dt><dd>{formatNumber(lifecycle.dry_run.maximum_bytes_billed)}</dd></div>
            <div><dt className="font-medium text-slate-900">Eligible</dt><dd>{String(lifecycle.dry_run.execution_eligible)}</dd></div>
          </dl>
          {lifecycle.dry_run.dry_run_error ? <p className="text-sm text-red-700">{lifecycle.dry_run.dry_run_error}</p> : null}
        </section>

        <section className="space-y-2 rounded-md border border-slate-200 p-3">
          <h4 className="text-sm font-semibold text-slate-900">Execution</h4>
          <div className="flex flex-wrap gap-2">
            <span className={badgeClass(lifecycle.execution.status)}>{lifecycle.execution.status}</span>
            <span className={lifecycle.execution.result_truncated ? "status-badge bg-amber-100 text-amber-800" : "status-badge bg-slate-200 text-slate-700"}>{lifecycle.execution.result_truncated ? "Truncated" : "Not truncated"}</span>
          </div>
          <dl className="grid gap-2 text-sm text-slate-700 sm:grid-cols-2">
            <div><dt className="font-medium text-slate-900">Job ID</dt><dd className="break-all">{lifecycle.execution.execution_job_id || "Not available"}</dd></div>
            <div><dt className="font-medium text-slate-900">Rows</dt><dd>{formatNumber(lifecycle.execution.result_row_count)}</dd></div>
            <div><dt className="font-medium text-slate-900">Bytes processed</dt><dd>{formatNumber(lifecycle.execution.execution_bytes_processed)}</dd></div>
            <div><dt className="font-medium text-slate-900">Executed</dt><dd>{formatDate(lifecycle.execution.executed_at)}</dd></div>
          </dl>
          {lifecycle.execution.execution_error ? <p className="text-sm text-red-700">{lifecycle.execution.execution_error}</p> : null}
        </section>
      </div>

      <section className="space-y-2">
        <h4 className="text-sm font-semibold text-slate-900">Bounded Results</h4>
        {lifecycle.execution.result_truncated ? <p className="text-sm font-semibold text-amber-800">Stored rows are truncated.</p> : null}
        <ResultTable lifecycle={lifecycle} />
      </section>

      <section className="space-y-2">
        <h4 className="text-sm font-semibold text-slate-900">Audit Timeline</h4>
        <AuditTimeline auditLogs={auditLogs} />
      </section>
    </div>
  );
}

export default function QueryHistorySection({ token, datasets, onResult, onError }: QueryHistorySectionProps) {
  const [history, setHistory] = useState<QueryHistoryListResponse | null>(null);
  const [selected, setSelected] = useState<QueryLifecycleResponse | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    dataset_id: "",
    generation_status: "",
    validation_status: "",
    dry_run_status: "",
    execution_status: "",
    search: "",
  });
  const [skip, setSkip] = useState(0);
  const limit = 25;

  async function loadHistory(nextSkip = skip) {
    if (!token) {
      return;
    }
    const operation = "GET /queries";
    setLoading("history");
    try {
      const data = await api.listQueryHistory(token, {
        skip: nextSkip,
        limit,
        dataset_id: filters.dataset_id ? Number(filters.dataset_id) : null,
        generation_status: filters.generation_status,
        validation_status: filters.validation_status,
        dry_run_status: filters.dry_run_status,
        execution_status: filters.execution_status,
        search: filters.search.trim(),
      });
      setHistory(data);
      setSkip(nextSkip);
      onResult(operation, data);
    } catch (error) {
      onError(operation, error);
    } finally {
      setLoading(null);
    }
  }

  async function loadDetails(queryRequestId: number) {
    if (!token) {
      return;
    }
    setLoading(`details:${queryRequestId}`);
    try {
      const lifecycle = await api.getQueryLifecycle(token, queryRequestId);
      const audit = await api.getQueryAuditLogs(token, queryRequestId);
      setSelected(lifecycle);
      setAuditLogs(audit.items);
      onResult(`GET /queries/${queryRequestId}`, { lifecycle, audit });
    } catch (error) {
      onError(`GET /queries/${queryRequestId}`, error);
    } finally {
      setLoading(null);
    }
  }

  function submitFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void loadHistory(0);
  }

  function clearFilters() {
    setFilters({ dataset_id: "", generation_status: "", validation_status: "", dry_run_status: "", execution_status: "", search: "" });
    setSkip(0);
  }

  useEffect(() => {
    if (!token) {
      setHistory(null);
      setSelected(null);
      setAuditLogs([]);
    }
  }, [token]);

  return (
    <SectionCard title="Query History" description="Review generated SQL, validation, dry run, execution, bounded results, and audit timeline without running queries.">
      {!token ? <p className="text-sm text-amber-700">Log in before viewing query history.</p> : null}
      {token ? (
        <div className="space-y-4">
          <form className="grid gap-3 lg:grid-cols-6" onSubmit={submitFilters}>
            <label className="field-label lg:col-span-2">Search
              <input className="input-field" value={filters.search} onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))} placeholder="Question or SQL" />
            </label>
            <label className="field-label">Dataset
              <select className="input-field" value={filters.dataset_id} onChange={(event) => setFilters((current) => ({ ...current, dataset_id: event.target.value }))}>
                <option value="">All</option>
                {datasets.map((dataset) => <option key={dataset.id} value={dataset.id}>{dataset.name}</option>)}
              </select>
            </label>
            {(["generation_status", "validation_status", "dry_run_status", "execution_status"] as const).map((field) => (
              <label className="field-label" key={field}>{field.replace("_", " ")}
                <select className="input-field" value={filters[field]} onChange={(event) => setFilters((current) => ({ ...current, [field]: event.target.value }))}>
                  {STATUS_OPTIONS.map((status) => <option key={`${field}-${status || "all"}`} value={status}>{status || "All"}</option>)}
                </select>
              </label>
            ))}
            <div className="flex items-end gap-2 lg:col-span-6">
              <button className="btn-primary" disabled={loading === "history"} type="submit">{loading === "history" ? "Loading..." : "Refresh"}</button>
              <button className="btn-secondary" onClick={clearFilters} type="button">Clear filters</button>
            </div>
          </form>

          <div className="table-shell">
            <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-3 py-2 font-semibold">Question</th>
                  <th className="px-3 py-2 font-semibold">Dataset</th>
                  <th className="px-3 py-2 font-semibold">Generation</th>
                  <th className="px-3 py-2 font-semibold">Validation</th>
                  <th className="px-3 py-2 font-semibold">Dry run</th>
                  <th className="px-3 py-2 font-semibold">Execution</th>
                  <th className="px-3 py-2 font-semibold">Rows</th>
                  <th className="px-3 py-2 font-semibold">Created</th>
                  <th className="px-3 py-2 font-semibold">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {history?.items.map((item) => (
                  <tr key={item.id}>
                    <td className="max-w-sm px-3 py-2 align-top"><div className="font-medium text-slate-900">{item.question}</div><div className="mt-1 text-xs text-slate-500">{item.generated_sql_preview || "No SQL"}</div></td>
                    <td className="px-3 py-2 align-top">{item.dataset_name || "Dataset unavailable"}</td>
                    <td className="px-3 py-2 align-top"><span className={badgeClass(item.generation_status)}>{item.generation_status}</span></td>
                    <td className="px-3 py-2 align-top"><span className={badgeClass(item.validation_status)}>{item.validation_status}</span></td>
                    <td className="px-3 py-2 align-top"><span className={badgeClass(item.dry_run_status)}>{item.dry_run_status}</span><div className="mt-1 text-xs">{formatNumber(item.estimated_bytes_processed)} bytes</div></td>
                    <td className="px-3 py-2 align-top"><span className={badgeClass(item.execution_status)}>{item.execution_status}</span></td>
                    <td className="px-3 py-2 align-top">{formatNumber(item.result_row_count)}</td>
                    <td className="px-3 py-2 align-top">{formatDate(item.created_at)}</td>
                    <td className="px-3 py-2 align-top"><button className="btn-secondary" onClick={() => void loadDetails(item.id)} type="button">{loading === `details:${item.id}` ? "Loading..." : "View details"}</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
            {history && history.items.length === 0 ? <p className="p-4 text-sm text-slate-600">No query history yet.</p> : null}
            {!history ? <p className="p-4 text-sm text-slate-600">Refresh to load query history.</p> : null}
          </div>

          <div className="flex items-center justify-between text-sm text-slate-600">
            <span>{history ? `${history.total.toLocaleString()} total records` : "No page loaded"}</span>
            <div className="flex gap-2">
              <button className="btn-secondary" disabled={!history || skip === 0 || loading === "history"} onClick={() => void loadHistory(Math.max(0, skip - limit))} type="button">Previous</button>
              <button className="btn-secondary" disabled={!history?.has_more || loading === "history"} onClick={() => void loadHistory(skip + limit)} type="button">Next</button>
            </div>
          </div>

          <LifecycleDetails lifecycle={selected} auditLogs={auditLogs} />
        </div>
      ) : null}
    </SectionCard>
  );
}
