import { useState } from "react";
import Link from "next/link";
import StatusBadge from "@/components/mvp/StatusBadge";
import { displayCell, formatDate, formatNumber } from "@/components/mvp/format";
import type { AuditLog, QueryDryRunResponse, QueryExecutionResponse, QueryGenerateResponse, SQLValidationResponse } from "@/lib/types";

type GovernanceDetailsProps = {
  generated: QueryGenerateResponse | null;
  validation: SQLValidationResponse | null;
  dryRun: QueryDryRunResponse | null;
  execution: QueryExecutionResponse | null;
  auditLogs: AuditLog[];
  queryId: number | null;
};

type Tab = "sql" | "validation" | "cost" | "audit";

function TabButton({ active, children, onClick }: { active: boolean; children: string; onClick: () => void }) {
  return <button className={active ? "tab-button tab-button-active" : "tab-button"} onClick={onClick} type="button">{children}</button>;
}

function SqlPanel({ generated, execution }: Pick<GovernanceDetailsProps, "generated" | "execution">) {
  const sql = execution?.generated_sql || generated?.generated_sql || "No SQL generated yet.";
  async function copySql() {
    if (sql && sql !== "No SQL generated yet.") await navigator.clipboard.writeText(sql);
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-slate-700">This SQL was generated from your question and passed through QueryShield's safety pipeline before execution.</p>
      <div className="flex flex-wrap gap-3 text-sm">
        <button className="btn-secondary" disabled={!generated?.generated_sql && !execution?.generated_sql} onClick={copySql} type="button">Copy SQL</button>
        {generated?.created_at ? <span className="self-center text-slate-600">Generated {formatDate(generated.created_at)}</span> : null}
        {generated?.model_name ? <span className="self-center text-slate-600">Model: {generated.model_name}</span> : null}
      </div>
      <pre className="max-h-96 overflow-auto rounded-xl bg-slate-950 p-4 text-sm text-slate-100"><code>{sql}</code></pre>
    </div>
  );
}

function ValidationPanel({ validation }: Pick<GovernanceDetailsProps, "validation">) {
  if (!validation) return <p className="text-sm text-slate-600">Validation is not available yet.</p>;
  return (
    <div className="space-y-4 text-sm">
      <div className="flex flex-wrap items-center gap-2"><StatusBadge status={validation.validation_status} /><StatusBadge status={validation.is_safe ? "safe" : "blocked"} /></div>
      <p className="text-slate-700">{validation.is_safe ? "QueryShield allowed this read-only query for the selected dataset." : "This query was blocked by QueryShield's safety rules."}</p>
      <dl className="grid gap-3 sm:grid-cols-3">
        <div><dt className="font-semibold text-slate-900">Statement</dt><dd>{validation.statement_type || "Not available"}</dd></div>
        <div><dt className="font-semibold text-slate-900">Validated</dt><dd>{formatDate(validation.validated_at)}</dd></div>
        <div><dt className="font-semibold text-slate-900">Referenced tables</dt><dd className="break-all">{validation.referenced_tables.join(", ") || "None"}</dd></div>
      </dl>
      {validation.errors.length ? <div className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-rose-800"><p className="font-semibold">Blocked reasons</p><ul className="mt-2 list-disc space-y-1 pl-5">{validation.errors.map((error) => <li key={error}>{error}</li>)}</ul></div> : null}
      {validation.warnings.length ? <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-amber-900"><p className="font-semibold">Warnings</p><ul className="mt-2 list-disc space-y-1 pl-5">{validation.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></div> : null}
    </div>
  );
}

function CostPanel({ dryRun, execution }: Pick<GovernanceDetailsProps, "dryRun" | "execution">) {
  if (!dryRun) return <p className="text-sm text-slate-600">Cost estimate is not available yet.</p>;
  return (
    <div className="space-y-4 text-sm">
      <div className="flex flex-wrap items-center gap-2"><StatusBadge status={dryRun.dry_run_status} /><StatusBadge status={dryRun.execution_eligible ? "eligible" : "blocked"} /></div>
      <p className="text-slate-700">
        BigQuery estimated that this query would process approximately {formatNumber(dryRun.estimated_mib_processed)} MiB. This estimate is {dryRun.bytes_limit_exceeded ? "above" : "within"} the configured limit of {formatNumber(dryRun.maximum_mib_billed)} MiB.
      </p>
      <dl className="grid gap-3 sm:grid-cols-3">
        <div><dt className="font-semibold text-slate-900">Estimated bytes</dt><dd>{formatNumber(dryRun.estimated_bytes_processed)}</dd></div>
        <div><dt className="font-semibold text-slate-900">Maximum bytes</dt><dd>{formatNumber(dryRun.maximum_bytes_billed)}</dd></div>
        <div><dt className="font-semibold text-slate-900">Estimated cost</dt><dd>{dryRun.estimated_cost ? `${dryRun.estimated_cost} ${dryRun.estimated_cost_currency}` : "Not available"}</dd></div>
        <div><dt className="font-semibold text-slate-900">Dry-run time</dt><dd>{formatDate(dryRun.dry_run_at)}</dd></div>
        <div><dt className="font-semibold text-slate-900">Bytes billed</dt><dd>{formatNumber(execution?.execution_bytes_billed)}</dd></div>
        <div><dt className="font-semibold text-slate-900">Cache hit</dt><dd>{execution?.execution_cache_hit === null || execution?.execution_cache_hit === undefined ? "Not available" : String(execution.execution_cache_hit)}</dd></div>
      </dl>
      <p className="text-xs leading-5 text-slate-500">Cost and bytes are estimates until BigQuery executes the approved query. Billing can vary by Google Cloud billing configuration.</p>
      {dryRun.dry_run_error ? <p className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-rose-800">{dryRun.dry_run_error}</p> : null}
    </div>
  );
}

function AuditPanel({ auditLogs, queryId }: Pick<GovernanceDetailsProps, "auditLogs" | "queryId">) {
  return (
    <div className="space-y-3 text-sm">
      {queryId ? <Link className="btn-secondary" href={`/queries/${queryId}`}>Open full query history</Link> : null}
      {auditLogs.length ? (
        <ol className="space-y-3 border-l border-slate-200 pl-4">
          {auditLogs.map((log) => (
            <li key={log.id}>
              <div className="font-semibold text-slate-900">{formatDate(log.created_at)} - {log.action}</div>
              {log.details ? <pre className="mt-1 max-h-36 overflow-auto rounded-lg bg-slate-50 p-2 text-xs text-slate-700">{displayCell(log.details)}</pre> : null}
            </li>
          ))}
        </ol>
      ) : <p className="text-slate-600">Audit events are not loaded for this analysis yet.</p>}
    </div>
  );
}

export default function GovernanceDetails({ generated, validation, dryRun, execution, auditLogs, queryId }: GovernanceDetailsProps) {
  const [tab, setTab] = useState<Tab>("sql");

  return (
    <details className="app-surface p-4">
      <summary className="cursor-pointer text-base font-bold text-slate-950">How this result was generated</summary>
      <div className="mt-4 rounded-xl bg-slate-100 p-1">
        <div className="flex flex-wrap gap-1">
          <TabButton active={tab === "sql"} onClick={() => setTab("sql")}>Generated SQL</TabButton>
          <TabButton active={tab === "validation"} onClick={() => setTab("validation")}>Validation</TabButton>
          <TabButton active={tab === "cost"} onClick={() => setTab("cost")}>Cost estimate</TabButton>
          <TabButton active={tab === "audit"} onClick={() => setTab("audit")}>Audit trail</TabButton>
        </div>
      </div>
      <div className="mt-4">
        {tab === "sql" ? <SqlPanel generated={generated} execution={execution} /> : null}
        {tab === "validation" ? <ValidationPanel validation={validation} /> : null}
        {tab === "cost" ? <CostPanel dryRun={dryRun} execution={execution} /> : null}
        {tab === "audit" ? <AuditPanel auditLogs={auditLogs} queryId={queryId} /> : null}
      </div>
    </details>
  );
}