"use client";

import { FormEvent, useEffect, useState } from "react";
import AppShell from "@/components/mvp/AppShell";
import EmptyState from "@/components/mvp/EmptyState";
import ErrorAlert from "@/components/mvp/ErrorAlert";
import { displayCell, formatDate } from "@/components/mvp/format";
import * as api from "@/lib/api";
import type { AuditLogListResponse } from "@/lib/types";

export default function AuditLogsPage() {
  return <AppShell title="Audit Logs">{({ token }) => <AuditLogsContent token={token} />}</AppShell>;
}

function AuditLogsContent({ token }: { token: string }) {
  const [logs, setLogs] = useState<AuditLogListResponse | null>(null);
  const [action, setAction] = useState("");
  const [resourceType, setResourceType] = useState("");
  const [resourceId, setResourceId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [skip, setSkip] = useState(0);
  const limit = 50;

  async function load(nextSkip = skip) {
    setLoading(true);
    setError(null);
    try {
      setLogs(await api.listAuditLogs(token, { skip: nextSkip, limit, action, resource_type: resourceType, resource_id: resourceId }));
      setSkip(nextSkip);
    } catch (err) {
      setError(err instanceof api.ApiError ? err.message : "Audit logs failed to load.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(0); }, [token]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void load(0);
  }

  return (
    <div className="space-y-6">
      <ErrorAlert message={error} />
      <section className="app-surface p-4">
        <form className="grid gap-3 lg:grid-cols-5" onSubmit={submit}>
          <label className="field-label">Action<input className="input-field" value={action} onChange={(event) => setAction(event.target.value)} placeholder="query.executed" /></label>
          <label className="field-label">Resource type<input className="input-field" value={resourceType} onChange={(event) => setResourceType(event.target.value)} placeholder="query_request" /></label>
          <label className="field-label">Resource id<input className="input-field" value={resourceId} onChange={(event) => setResourceId(event.target.value)} /></label>
          <div className="flex items-end gap-2 lg:col-span-2"><button className="btn-primary" disabled={loading} type="submit">{loading ? "Loading..." : "Apply filters"}</button><button className="btn-secondary" onClick={() => { setAction(""); setResourceType(""); setResourceId(""); }} type="button">Clear</button></div>
        </form>
      </section>

      <section className="overflow-hidden app-surface shadow-sm">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr><th className="px-3 py-2">Time</th><th className="px-3 py-2">Action</th><th className="px-3 py-2">Resource</th><th className="px-3 py-2">Details</th></tr></thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {logs?.items.map((log) => <tr key={log.id}><td className="px-3 py-2 align-top">{formatDate(log.created_at)}</td><td className="px-3 py-2 align-top font-semibold text-slate-900">{log.action}</td><td className="px-3 py-2 align-top">{log.resource_type || "None"}{log.resource_id ? `:${log.resource_id}` : ""}</td><td className="max-w-xl whitespace-pre-wrap px-3 py-2 align-top text-xs">{displayCell(log.details)}</td></tr>)}
            </tbody>
          </table>
        </div>
        {logs && logs.items.length === 0 ? <div className="p-4"><EmptyState title="No audit events match the filters" /></div> : null}
      </section>

      <div className="flex items-center justify-between text-sm text-slate-600"><span>{logs ? `${logs.total.toLocaleString()} total records` : "No page loaded"}</span><div className="flex gap-2"><button className="btn-secondary" disabled={!logs || skip === 0 || loading} onClick={() => void load(Math.max(0, skip - limit))} type="button">Previous</button><button className="btn-secondary" disabled={!logs?.has_more || loading} onClick={() => void load(skip + limit)} type="button">Next</button></div></div>
    </div>
  );
}