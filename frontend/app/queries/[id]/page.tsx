"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import AiSummaryCard from "@/components/analysis/AiSummaryCard";
import AnalysisResultHeader from "@/components/analysis/AnalysisResultHeader";
import GovernanceDetails from "@/components/analysis/GovernanceDetails";
import ResultChart from "@/components/analysis/ResultChart";
import AppShell from "@/components/mvp/AppShell";
import ErrorAlert from "@/components/mvp/ErrorAlert";
import ResultTable from "@/components/mvp/ResultTable";
import StatusBadge from "@/components/mvp/StatusBadge";
import { formatDate, formatNumber } from "@/components/mvp/format";
import * as api from "@/lib/api";
import type { AuditLog, QueryExecutionResponse, QueryLifecycleResponse } from "@/lib/types";

export default function QueryDetailPage() {
  const params = useParams<{ id: string }>();
  const queryId = Number(params.id);
  return <AppShell title="Analysis Detail">{({ token }) => <QueryDetailContent queryId={queryId} token={token} />}</AppShell>;
}

function executionFromLifecycle(lifecycle: QueryLifecycleResponse): QueryExecutionResponse | null {
  if (lifecycle.execution.status !== "succeeded" && !lifecycle.execution.result_rows.length) return null;
  return {
    query_request_id: lifecycle.query.id,
    dataset_id: lifecycle.query.dataset_id,
    execution_status: lifecycle.execution.status,
    execution_job_id: lifecycle.execution.execution_job_id,
    execution_location: lifecycle.execution.execution_location,
    execution_bytes_processed: lifecycle.execution.execution_bytes_processed,
    execution_bytes_billed: lifecycle.execution.execution_bytes_billed,
    execution_cache_hit: lifecycle.execution.execution_cache_hit,
    result_row_count: lifecycle.execution.result_row_count || lifecycle.execution.result_rows.length,
    result_columns: lifecycle.execution.result_columns,
    result_rows: lifecycle.execution.result_rows,
    result_truncated: lifecycle.execution.result_truncated || false,
    row_limit: lifecycle.execution.result_row_count || lifecycle.execution.result_rows.length,
    execution_error: lifecycle.execution.execution_error,
    execution_started_at: lifecycle.execution.execution_started_at,
    execution_completed_at: lifecycle.execution.execution_completed_at,
    executed_at: lifecycle.execution.executed_at,
    generated_sql: lifecycle.generation.generated_sql || "",
    ai_summary: lifecycle.execution.ai_summary,
    ai_summary_status: lifecycle.execution.ai_summary_status,
    ai_summary_error: lifecycle.execution.ai_summary_error,
    ai_summary_generated_at: lifecycle.execution.ai_summary_generated_at,
  };
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
      setError(err instanceof api.ApiError ? err.message : "Analysis detail failed to load.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [token, queryId]);

  if (loading) {
    return <div className="app-surface p-4 text-sm text-slate-600">Loading analysis...</div>;
  }

  if (!lifecycle) {
    return <ErrorAlert message={error || "Analysis not found."} />;
  }

  const execution = executionFromLifecycle(lifecycle);
  const generated = lifecycle.generation.generated_sql ? {
    id: lifecycle.query.id,
    dataset_id: lifecycle.query.dataset_id,
    question: lifecycle.query.question,
    generated_sql: lifecycle.generation.generated_sql,
    model_name: lifecycle.generation.model_name,
    status: lifecycle.generation.status,
    created_at: lifecycle.query.created_at,
    validation_status: lifecycle.validation.status,
    is_safe: lifecycle.validation.is_safe,
    validation_errors: lifecycle.validation.errors,
    validation_warnings: lifecycle.validation.warnings,
    validated_at: lifecycle.validation.validated_at,
    dry_run_status: lifecycle.dry_run.status,
    estimated_bytes_processed: lifecycle.dry_run.estimated_bytes_processed,
    estimated_cost: lifecycle.dry_run.estimated_cost,
    bytes_limit_exceeded: lifecycle.dry_run.bytes_limit_exceeded,
    execution_eligible: lifecycle.dry_run.execution_eligible,
    dry_run_at: lifecycle.dry_run.dry_run_at,
  } : null;
  const validation = lifecycle.generation.generated_sql ? {
    query_request_id: lifecycle.query.id,
    dataset_id: lifecycle.query.dataset_id,
    validation_status: lifecycle.validation.status,
    is_safe: lifecycle.validation.is_safe || false,
    statement_type: lifecycle.validation.statement_type,
    referenced_tables: lifecycle.validation.referenced_tables,
    errors: lifecycle.validation.errors,
    warnings: lifecycle.validation.warnings,
    validated_at: lifecycle.validation.validated_at,
    generated_sql: lifecycle.generation.generated_sql,
    normalized_sql: null,
  } : null;
  const dryRun = lifecycle.generation.generated_sql && lifecycle.dry_run.maximum_bytes_billed !== null ? {
    query_request_id: lifecycle.query.id,
    dataset_id: lifecycle.query.dataset_id,
    dry_run_status: lifecycle.dry_run.status,
    dry_run_valid: lifecycle.dry_run.dry_run_valid || false,
    estimated_bytes_processed: lifecycle.dry_run.estimated_bytes_processed,
    estimated_mib_processed: lifecycle.dry_run.estimated_mib_processed,
    estimated_gib_processed: lifecycle.dry_run.estimated_gib_processed,
    estimated_tib_processed: lifecycle.dry_run.estimated_tib_processed,
    maximum_bytes_billed: lifecycle.dry_run.maximum_bytes_billed,
    maximum_mib_billed: 0,
    bytes_limit_exceeded: lifecycle.dry_run.bytes_limit_exceeded || false,
    estimated_cost: lifecycle.dry_run.estimated_cost,
    estimated_cost_currency: lifecycle.dry_run.estimated_cost_currency || "USD",
    execution_eligible: lifecycle.dry_run.execution_eligible,
    dry_run_error: lifecycle.dry_run.dry_run_error,
    dry_run_at: lifecycle.dry_run.dry_run_at,
    dry_run_job_id: lifecycle.dry_run.dry_run_job_id,
    dry_run_location: lifecycle.dry_run.dry_run_location,
    generated_sql: lifecycle.generation.generated_sql,
    warnings: [],
  } : null;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <Link className="text-sm font-semibold text-indigo-700" href="/history">Back to history</Link>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <h2 className="text-xl font-bold text-slate-950">Saved analysis</h2>
            <StatusBadge status={lifecycle.execution.status} />
          </div>
          <p className="mt-1 text-xs text-slate-500">{lifecycle.query.dataset_name || "Dataset unavailable"} - {formatDate(lifecycle.query.created_at)}</p>
        </div>
        <button className="btn-secondary" onClick={() => void load()} type="button">Refresh</button>
      </div>
      <ErrorAlert message={error} />

      {execution ? (
        <>
          <AnalysisResultHeader execution={execution} question={lifecycle.query.question} />
          <AiSummaryCard error={execution.ai_summary_error} status={execution.ai_summary_status} summary={execution.ai_summary} />
          <ResultChart execution={execution} question={lifecycle.query.question} />
          <section className="app-surface p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h3 className="text-base font-bold text-slate-950">Result table</h3>
              <span className="text-sm font-semibold text-slate-600">{formatNumber(execution.result_row_count)} rows returned</span>
            </div>
            <div className="mt-4"><ResultTable columns={execution.result_columns} rows={execution.result_rows} /></div>
          </section>
        </>
      ) : (
        <section className="app-surface p-4">
          <h3 className="text-base font-bold text-slate-950">No stored result rows</h3>
          <p className="mt-2 text-sm text-slate-600">This analysis has not completed successfully, or no bounded result rows were stored.</p>
        </section>
      )}

      <GovernanceDetails auditLogs={auditLogs} dryRun={dryRun} execution={execution} generated={generated} queryId={lifecycle.query.id} validation={validation} />
    </div>
  );
}
