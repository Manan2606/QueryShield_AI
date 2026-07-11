"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import AppShell from "@/components/mvp/AppShell";
import EmptyState from "@/components/mvp/EmptyState";
import ErrorAlert from "@/components/mvp/ErrorAlert";
import StatusBadge from "@/components/mvp/StatusBadge";
import { formatDate, formatNumber } from "@/components/mvp/format";
import * as api from "@/lib/api";
import type { Dataset } from "@/lib/types";

export default function DatasetsPage() {
  return <AppShell title="Datasets">{({ token }) => <DatasetsContent token={token} />}</AppShell>;
}

function DatasetsContent({ token }: { token: string }) {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState<string | null>("load");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading("load");
    setError(null);
    try {
      setDatasets(await api.listDatasets(token));
    } catch (err) {
      setError(err instanceof api.ApiError ? err.message : "Datasets failed to load.");
    } finally {
      setLoading(null);
    }
  }

  useEffect(() => { void load(); }, [token]);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading("create");
    setError(null);
    try {
      await api.createDataset(token, { name, description: description || null });
      setName("");
      setDescription("");
      await load();
    } catch (err) {
      setError(err instanceof api.ApiError ? err.message : "Dataset could not be created.");
      setLoading(null);
    }
  }

  async function remove(dataset: Dataset) {
    if (!window.confirm(`Delete dataset "${dataset.name}"?`)) return;
    setLoading(`delete:${dataset.id}`);
    setError(null);
    try {
      await api.deleteDataset(token, dataset.id);
      await load();
    } catch (err) {
      setError(err instanceof api.ApiError ? err.message : "Dataset could not be deleted.");
      setLoading(null);
    }
  }

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return datasets.filter((dataset) => {
      const matchesSearch = !needle || dataset.name.toLowerCase().includes(needle) || (dataset.description || "").toLowerCase().includes(needle);
      const matchesStatus = !status || dataset.status === status;
      return matchesSearch && matchesStatus;
    });
  }, [datasets, search, status]);

  const statuses = Array.from(new Set(datasets.map((dataset) => dataset.status))).sort();

  return (
    <div className="space-y-6">
      <ErrorAlert message={error} />
      <section className="app-surface p-4">
        <h2 className="text-base font-bold text-slate-950">Create dataset</h2>
        <form className="mt-4 grid gap-3 lg:grid-cols-5" onSubmit={create}>
          <label className="field-label lg:col-span-2">Name
            <input className="input-field" required value={name} onChange={(event) => setName(event.target.value)} />
          </label>
          <label className="field-label lg:col-span-2">Description
            <input className="input-field" value={description} onChange={(event) => setDescription(event.target.value)} />
          </label>
          <div className="flex items-end">
            <button className="btn-primary w-full" disabled={loading === "create"} type="submit">{loading === "create" ? "Creating..." : "Create"}</button>
          </div>
        </form>
      </section>

      <section className="app-surface p-4">
        <div className="grid gap-3 lg:grid-cols-4">
          <label className="field-label lg:col-span-2">Search
            <input className="input-field" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Dataset name or description" />
          </label>
          <label className="field-label">Status
            <select className="input-field" value={status} onChange={(event) => setStatus(event.target.value)}>
              <option value="">All statuses</option>
              {statuses.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
          <div className="flex items-end">
            <button className="btn-secondary w-full" disabled={loading === "load"} onClick={() => void load()} type="button">Refresh</button>
          </div>
        </div>

        <div className="mt-4 table-shell">
          <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2 font-semibold">Dataset</th>
                <th className="px-3 py-2 font-semibold">Status</th>
                <th className="px-3 py-2 font-semibold">Rows</th>
                <th className="px-3 py-2 font-semibold">Columns</th>
                <th className="px-3 py-2 font-semibold">Updated</th>
                <th className="px-3 py-2 font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {filtered.map((dataset) => (
                <tr key={dataset.id}>
                  <td className="px-3 py-2 align-top"><Link className="font-semibold text-indigo-700" href={`/datasets/${dataset.id}`}>{dataset.name}</Link><div className="mt-1 text-xs text-slate-500">{dataset.description || "No description"}</div></td>
                  <td className="px-3 py-2 align-top"><StatusBadge status={dataset.status} /></td>
                  <td className="px-3 py-2 align-top">{formatNumber(dataset.row_count)}</td>
                  <td className="px-3 py-2 align-top">{formatNumber(dataset.column_count)}</td>
                  <td className="px-3 py-2 align-top">{formatDate(dataset.updated_at)}</td>
                  <td className="px-3 py-2 align-top"><div className="flex flex-wrap gap-2"><Link className="btn-secondary" href={`/datasets/${dataset.id}`}>Open</Link><button className="btn-danger" disabled={loading === `delete:${dataset.id}`} onClick={() => void remove(dataset)} type="button">Delete</button></div></td>
                </tr>
              ))}
            </tbody>
          </table>
          {!filtered.length ? <div className="p-4"><EmptyState title="No datasets match the current filters" /></div> : null}
        </div>
      </section>
    </div>
  );
}