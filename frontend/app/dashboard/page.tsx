"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import AppShell from "@/components/mvp/AppShell";
import EmptyState from "@/components/mvp/EmptyState";
import ErrorAlert from "@/components/mvp/ErrorAlert";
import StatusBadge from "@/components/mvp/StatusBadge";
import { formatDate, formatNumber } from "@/components/mvp/format";
import * as api from "@/lib/api";
import type { Dataset, QueryHistoryItem } from "@/lib/types";

function metric(label: string, value: number | string, tone: string) {
  return (
    <div className="metric-card">
      <div className={`absolute inset-x-0 top-0 h-1 ${tone}`} />
      <p className="metric-label">{label}</p>
      <p className="metric-value">{value}</p>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <AppShell title="Dashboard">
      {({ token }) => <DashboardContent token={token} />}
    </AppShell>
  );
}

function DashboardContent({ token }: { token: string }) {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [queries, setQueries] = useState<QueryHistoryItem[]>([]);
  const [totalQueries, setTotalQueries] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [datasetData, queryData] = await Promise.all([
          api.listDatasets(token),
          api.listQueryHistory(token, { limit: 8 }),
        ]);
        if (!mounted) return;
        setDatasets(datasetData);
        setQueries(queryData.items);
        setTotalQueries(queryData.total);
      } catch (err) {
        if (mounted) setError(err instanceof api.ApiError ? err.message : "Dashboard failed to load.");
      } finally {
        if (mounted) setLoading(false);
      }
    }
    void load();
    return () => { mounted = false; };
  }, [token]);

  const stats = useMemo(() => {
    const loaded = datasets.filter((dataset) => dataset.status === "loaded").length;
    const blocked = queries.filter((query) => ["blocked", "failed", "error", "timed_out"].includes(query.execution_status) || query.bytes_limit_exceeded).length;
    return { loaded, blocked };
  }, [datasets, queries]);

  return (
    <div className="space-y-6">
      <ErrorAlert message={error} />

      <section className="app-surface overflow-hidden p-6">
        <div className="grid gap-5 lg:grid-cols-[1.15fr_0.85fr] lg:items-center">
          <div>
            <p className="inline-flex rounded-full border border-teal-200 bg-teal-50 px-3 py-1 text-xs font-bold uppercase tracking-[0.2em] text-teal-700">Phase-1 control plane</p>
            <h2 className="mt-3 text-3xl font-black tracking-normal text-slate-950">Governed analytics workflow</h2>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">Move from dataset onboarding to generated SQL, validation, dry runs, bounded execution, history, and audit review in one polished workspace.</p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <Link className="rounded-2xl border border-teal-200 bg-teal-50 p-4 text-sm font-bold text-teal-900 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md" href="/datasets">Upload CSV</Link>
            <Link className="rounded-2xl border border-slate-200 bg-white p-4 text-sm font-bold text-slate-900 shadow-sm transition hover:-translate-y-0.5 hover:border-teal-200 hover:shadow-md" href="/queries/new">Ask a question</Link>
          </div>
        </div>
      </section>

      <div className="grid gap-4 md:grid-cols-4">
        {metric("Datasets", loading ? "..." : datasets.length, "bg-slate-950")}
        {metric("Loaded datasets", loading ? "..." : stats.loaded, "bg-teal-500")}
        {metric("Query requests", loading ? "..." : totalQueries, "bg-amber-400")}
        {metric("Recent blocked", loading ? "..." : stats.blocked, "bg-rose-400")}
      </div>

      <section className="grid gap-6 xl:grid-cols-2">
        <div className="app-surface p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="panel-title">Recent datasets</h2>
              <p className="panel-subtitle">Upload status and BigQuery readiness.</p>
            </div>
            <Link className="btn-secondary" href="/datasets">View all</Link>
          </div>
          <div className="mt-4 space-y-3">
            {datasets.slice(0, 5).map((dataset) => (
              <Link className="interactive-row" href={`/datasets/${dataset.id}`} key={dataset.id}>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-bold text-slate-950">{dataset.name}</p>
                    <p className="mt-1 text-sm text-slate-600">{formatNumber(dataset.row_count)} rows - {formatNumber(dataset.column_count)} columns</p>
                  </div>
                  <StatusBadge status={dataset.status} />
                </div>
              </Link>
            ))}
            {!datasets.length && !loading ? <EmptyState title="No datasets yet" action={<Link className="btn-primary" href="/datasets">Create dataset</Link>} /> : null}
          </div>
        </div>

        <div className="app-surface p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="panel-title">Recent query activity</h2>
              <p className="panel-subtitle">Latest generation, validation, and execution states.</p>
            </div>
            <Link className="btn-secondary" href="/history">Open history</Link>
          </div>
          <div className="mt-4 space-y-3">
            {queries.map((query) => (
              <Link className="interactive-row" href={`/queries/${query.id}`} key={query.id}>
                <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <p className="font-bold text-slate-950">{query.question}</p>
                    <p className="mt-1 text-sm text-slate-600">{query.dataset_name || "Dataset unavailable"} - {formatDate(query.created_at)}</p>
                  </div>
                  <StatusBadge status={query.execution_status} />
                </div>
              </Link>
            ))}
            {!queries.length && !loading ? <EmptyState title="No query history yet" action={<Link className="btn-primary" href="/queries/new">Ask a question</Link>} /> : null}
          </div>
        </div>
      </section>

      <section className="grid gap-3 md:grid-cols-3">
        <Link className="app-surface p-4 text-sm font-bold text-slate-900 transition hover:-translate-y-0.5 hover:border-teal-200" href="/datasets">Dataset onboarding</Link>
        <Link className="app-surface p-4 text-sm font-bold text-slate-900 transition hover:-translate-y-0.5 hover:border-teal-200" href="/queries/new">Governed query pipeline</Link>
        <Link className="app-surface p-4 text-sm font-bold text-slate-900 transition hover:-translate-y-0.5 hover:border-teal-200" href="/audit-logs">Audit trail</Link>
      </section>
    </div>
  );
}