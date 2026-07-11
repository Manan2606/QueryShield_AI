"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import AppShell from "@/components/mvp/AppShell";
import EmptyState from "@/components/mvp/EmptyState";
import ErrorAlert from "@/components/mvp/ErrorAlert";
import StatusBadge from "@/components/mvp/StatusBadge";
import { displayCell, formatDate, formatNumber } from "@/components/mvp/format";
import * as api from "@/lib/api";
import type { BigQueryTableInfo, CSVPreviewResponse, DatasetDetail } from "@/lib/types";

type PageProps = { params: Promise<{ id: string }> };

export default function DatasetDetailPage({ params }: PageProps) {
  const [datasetId, setDatasetId] = useState<number | null>(null);

  useEffect(() => {
    params.then((value) => setDatasetId(Number(value.id)));
  }, [params]);

  return <AppShell title="Dataset detail">{({ token }) => datasetId ? <DatasetDetailContent datasetId={datasetId} token={token} /> : null}</AppShell>;
}

function DatasetDetailContent({ token, datasetId }: { token: string; datasetId: number }) {
  const [dataset, setDataset] = useState<DatasetDetail | null>(null);
  const [preview, setPreview] = useState<CSVPreviewResponse | null>(null);
  const [bigQueryInfo, setBigQueryInfo] = useState<BigQueryTableInfo | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState<string | null>("load");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const previewHeaders = useMemo(() => preview?.columns || [], [preview]);

  async function load(includePreview = true) {
    setLoading("load");
    setError(null);
    try {
      const detail = await api.getDataset(token, datasetId);
      setDataset(detail);
      setName(detail.name);
      setDescription(detail.description || "");
      if (includePreview) {
        try {
          setPreview(await api.previewCsv(token, datasetId));
        } catch {
          setPreview(null);
        }
        try {
          setBigQueryInfo(await api.getBigQueryInfo(token, datasetId));
        } catch {
          setBigQueryInfo(null);
        }
      }
    } catch (err) {
      setError(err instanceof api.ApiError ? err.message : "Dataset failed to load.");
    } finally {
      setLoading(null);
    }
  }

  useEffect(() => { void load(); }, [token, datasetId]);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading("save");
    setError(null);
    setNotice(null);
    try {
      await api.updateDataset(token, datasetId, { name, description: description || null });
      setNotice("Dataset details saved.");
      await load(false);
    } catch (err) {
      setError(err instanceof api.ApiError ? err.message : "Dataset details could not be saved.");
      setLoading(null);
    }
  }

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;
    setLoading("upload");
    setError(null);
    setNotice(null);
    try {
      await api.uploadCsv(token, datasetId, file);
      setFile(null);
      setNotice("CSV uploaded and schema detected.");
      await load(true);
    } catch (err) {
      setError(err instanceof api.ApiError ? err.message : "CSV upload failed.");
      setLoading(null);
    }
  }

  async function loadToBigQuery() {
    if (!window.confirm("Load this uploaded CSV into BigQuery?")) return;
    setLoading("bigquery");
    setError(null);
    setNotice(null);
    try {
      await api.loadBigQuery(token, datasetId);
      setNotice("Dataset loaded to BigQuery.");
      await load(true);
    } catch (err) {
      setError(err instanceof api.ApiError ? err.message : "BigQuery load failed.");
      setLoading(null);
    }
  }

  if (!dataset && loading === "load") {
    return <div className="app-surface p-4 text-sm text-slate-600">Loading dataset...</div>;
  }

  if (!dataset) {
    return <ErrorAlert message={error || "Dataset not found."} />;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <Link className="text-sm font-semibold text-indigo-700" href="/datasets">Back to datasets</Link>
          <div className="mt-2 flex flex-wrap items-center gap-3"><h2 className="text-xl font-bold text-slate-950">{dataset.name}</h2><StatusBadge status={dataset.status} /></div>
          <p className="mt-1 text-sm text-slate-600">Created {formatDate(dataset.created_at)} - Updated {formatDate(dataset.updated_at)}</p>
        </div>
        {dataset.status === "loaded" ? <Link className="btn-primary" href={`/queries/new?dataset_id=${dataset.id}`}>Ask question</Link> : null}
      </div>

      <ErrorAlert message={error} />
      {notice ? <div className="rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</div> : null}

      <section className="grid gap-6 xl:grid-cols-3">
        <form className="app-surface p-4 xl:col-span-1" onSubmit={save}>
          <h3 className="text-base font-bold text-slate-950">Dataset settings</h3>
          <div className="mt-4 space-y-3">
            <label className="field-label">Name<input className="input-field" required value={name} onChange={(event) => setName(event.target.value)} /></label>
            <label className="field-label">Description<textarea className="input-field min-h-24" value={description} onChange={(event) => setDescription(event.target.value)} /></label>
            <button className="btn-primary" disabled={loading === "save"} type="submit">{loading === "save" ? "Saving..." : "Save changes"}</button>
          </div>
        </form>

        <form className="app-surface p-4 xl:col-span-2" onSubmit={upload}>
          <h3 className="text-base font-bold text-slate-950">CSV source</h3>
          <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-3">
            <div><dt className="font-semibold text-slate-900">File</dt><dd className="text-slate-600">{dataset.original_filename || "No CSV uploaded"}</dd></div>
            <div><dt className="font-semibold text-slate-900">Rows</dt><dd className="text-slate-600">{formatNumber(dataset.row_count)}</dd></div>
            <div><dt className="font-semibold text-slate-900">Columns</dt><dd className="text-slate-600">{formatNumber(dataset.column_count)}</dd></div>
          </dl>
          <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end">
            <label className="field-label flex-1">Upload CSV<input className="input-field" accept=".csv,text/csv" type="file" onChange={(event) => setFile(event.target.files?.[0] || null)} /></label>
            <button className="btn-primary" disabled={!file || loading === "upload"} type="submit">{loading === "upload" ? "Uploading..." : "Upload"}</button>
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button className="btn-warning" disabled={!dataset.storage_path || loading === "bigquery"} onClick={loadToBigQuery} type="button">{loading === "bigquery" ? "Loading..." : "Load to BigQuery"}</button>
            {dataset.bigquery_table_id ? <span className="break-all text-sm font-semibold text-slate-700">{dataset.bigquery_table_id}</span> : <span className="text-sm text-slate-600">Upload a CSV before loading to BigQuery.</span>}
          </div>
        </form>
      </section>

      <section className="app-surface p-4">
        <h3 className="text-base font-bold text-slate-950">Detected schema</h3>
        <div className="mt-4 table-shell">
          <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr><th className="px-3 py-2">Position</th><th className="px-3 py-2">Name</th><th className="px-3 py-2">Type</th><th className="px-3 py-2">Nullable</th><th className="px-3 py-2">Sample values</th></tr></thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {dataset.columns.map((column) => <tr key={`${column.ordinal_position}-${column.name}`}><td className="px-3 py-2">{column.ordinal_position}</td><td className="px-3 py-2 font-semibold text-slate-900">{column.name}</td><td className="px-3 py-2">{column.data_type}</td><td className="px-3 py-2">{column.nullable ? "Yes" : "No"}</td><td className="px-3 py-2">{(column.sample_values || []).join(", ")}</td></tr>)}
            </tbody>
          </table>
          {!dataset.columns.length ? <div className="p-4"><EmptyState title="Upload a CSV to detect schema" /></div> : null}
        </div>
      </section>

      <section className="app-surface p-4">
        <h3 className="text-base font-bold text-slate-950">CSV preview</h3>
        {previewHeaders.length ? <div className="mt-4 table-shell"><table className="min-w-full divide-y divide-slate-200 text-left text-sm"><thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr>{previewHeaders.map((header) => <th className="px-3 py-2" key={header}>{header}</th>)}</tr></thead><tbody className="divide-y divide-slate-100 text-slate-700">{preview?.rows.map((row, index) => <tr key={index}>{previewHeaders.map((header) => <td className="max-w-sm whitespace-pre-wrap px-3 py-2 align-top" key={header}>{displayCell(row[header])}</td>)}</tr>)}</tbody></table></div> : <EmptyState title="No CSV preview available" />}
      </section>

      {bigQueryInfo ? <section className="app-surface p-4"><h3 className="text-base font-bold text-slate-950">BigQuery table</h3><dl className="mt-3 grid gap-3 text-sm sm:grid-cols-3"><div><dt className="font-semibold text-slate-900">Table</dt><dd className="break-all text-slate-600">{bigQueryInfo.bigquery_table_id}</dd></div><div><dt className="font-semibold text-slate-900">Rows</dt><dd className="text-slate-600">{formatNumber(bigQueryInfo.num_rows)}</dd></div><div><dt className="font-semibold text-slate-900">Bytes</dt><dd className="text-slate-600">{formatNumber(bigQueryInfo.num_bytes)}</dd></div></dl></section> : null}
    </div>
  );
}