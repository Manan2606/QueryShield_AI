import { FormEvent, useEffect, useState } from "react";
import type { BigQueryTableInfo, CSVPreviewResponse, Dataset, DatasetColumn } from "@/lib/types";
import BigQueryInfo from "./BigQueryInfo";
import CsvPreview from "./CsvPreview";
import SectionCard from "./SectionCard";

type DatasetActionsProps = {
  token: string | null;
  dataset: Dataset | null;
  columns: DatasetColumn[];
  csvPreview: CSVPreviewResponse | null;
  bigQueryInfo: BigQueryTableInfo | null;
  loading: string | null;
  onRefreshDetail: () => void;
  onUpdate: (payload: { name?: string; description?: string | null }) => Promise<void>;
  onUploadCsv: (file: File) => Promise<void>;
  onPreviewCsv: () => void;
  onLoadBigQuery: () => void;
  onGetBigQueryInfo: () => void;
};

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "-";
  }
  return new Date(value).toLocaleString();
}

export default function DatasetActions({
  token,
  dataset,
  columns,
  csvPreview,
  bigQueryInfo,
  loading,
  onRefreshDetail,
  onUpdate,
  onUploadCsv,
  onPreviewCsv,
  onLoadBigQuery,
  onGetBigQueryInfo,
}: DatasetActionsProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);

  useEffect(() => {
    setName(dataset?.name || "");
    setDescription(dataset?.description || "");
    setFile(null);
  }, [dataset?.id, dataset?.name, dataset?.description]);

  async function submitUpdate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload: { name?: string; description?: string | null } = {};
    if (name && name !== dataset?.name) {
      payload.name = name;
    }
    if (description !== (dataset?.description || "")) {
      payload.description = description || null;
    }
    await onUpdate(payload);
  }

  async function submitUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (file) {
      const form = event.currentTarget;
      await onUploadCsv(file);
      setFile(null);
      form?.reset();
    }
  }

  const hasUploadedCsv = Boolean(dataset?.storage_path || dataset?.original_filename);
  const hasLoadedBigQuery = Boolean(dataset?.bigquery_table_id);

  return (
    <SectionCard title="Selected Dataset Actions" description="Select a dataset before using upload, preview, or BigQuery actions.">
      {!token ? <p className="text-sm text-amber-700">Log in before using dataset actions.</p> : null}
      {!dataset ? <p className="text-sm text-slate-600">No dataset selected.</p> : null}
      {dataset ? (
        <div className="space-y-6">
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
            <div className="mb-3 flex flex-wrap items-center gap-3">
              <h3 className="text-base font-semibold text-slate-900">{dataset.name}</h3>
              <span className="status-badge bg-slate-200 text-slate-700">{dataset.status}</span>
              <button className="btn-secondary ml-auto" disabled={loading === "datasetDetail"} onClick={onRefreshDetail} type="button">
                {loading === "datasetDetail" ? "Refreshing..." : "Refresh Dataset Detail"}
              </button>
            </div>
            <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
              <div><dt className="meta-label">ID</dt><dd className="meta-value">{dataset.id}</dd></div>
              <div><dt className="meta-label">File</dt><dd className="meta-value">{dataset.original_filename || "-"}</dd></div>
              <div><dt className="meta-label">Rows</dt><dd className="meta-value">{dataset.row_count ?? "-"}</dd></div>
              <div><dt className="meta-label">Columns</dt><dd className="meta-value">{dataset.column_count ?? "-"}</dd></div>
              <div className="lg:col-span-2"><dt className="meta-label">BigQuery table</dt><dd className="meta-value break-all">{dataset.bigquery_table_id || "-"}</dd></div>
              <div><dt className="meta-label">Loaded at</dt><dd className="meta-value">{formatDate(dataset.loaded_at)}</dd></div>
              <div><dt className="meta-label">Updated</dt><dd className="meta-value">{formatDate(dataset.updated_at)}</dd></div>
            </dl>
            {dataset.load_error ? <p className="mt-3 rounded-md bg-rose-50 p-2 text-sm text-rose-700">{dataset.load_error}</p> : null}
          </div>

          <form className="grid gap-3 md:grid-cols-[1fr_2fr_auto] md:items-end" onSubmit={submitUpdate}>
            <label className="field-label">Name
              <input className="input-field" value={name} onChange={(event) => setName(event.target.value)} />
            </label>
            <label className="field-label">Description
              <input className="input-field" value={description} onChange={(event) => setDescription(event.target.value)} />
            </label>
            <button className="btn-primary" disabled={loading === "updateDataset" || !name} type="submit">
              {loading === "updateDataset" ? "Updating..." : "Update Metadata"}
            </button>
          </form>

          <form className="grid gap-3 md:grid-cols-[1fr_auto] md:items-end" onSubmit={submitUpload}>
            <label className="field-label">CSV file
              <input className="input-field" accept=".csv,text/csv" onChange={(event) => setFile(event.target.files?.[0] || null)} type="file" />
            </label>
            <button className="btn-primary" disabled={!file || loading === "uploadCsv"} type="submit">
              {loading === "uploadCsv" ? "Uploading CSV..." : "Upload CSV"}
            </button>
          </form>

          <div className="flex flex-wrap gap-3">
            <button className="btn-primary" disabled={!hasUploadedCsv || loading === "previewCsv"} onClick={onPreviewCsv} type="button">
              {loading === "previewCsv" ? "Loading preview..." : "Preview CSV"}
            </button>
            <button className="btn-warning" disabled={!hasUploadedCsv || loading === "loadBigQuery"} onClick={onLoadBigQuery} type="button">
              {loading === "loadBigQuery" ? "Loading into BigQuery..." : "Load to BigQuery"}
            </button>
            <button className="btn-secondary" disabled={!hasLoadedBigQuery || loading === "bigQueryInfo"} onClick={onGetBigQueryInfo} type="button">
              {loading === "bigQueryInfo" ? "Fetching BigQuery info..." : "Get BigQuery Info"}
            </button>
          </div>
          {!hasUploadedCsv ? <p className="text-sm text-amber-700">Upload a CSV before previewing or loading into BigQuery.</p> : null}
          <p className="rounded-md bg-amber-50 p-3 text-sm text-amber-800">
            Loading to BigQuery sends the uploaded CSV to the Google Cloud BigQuery project configured in the backend.
          </p>

          {columns.length > 0 ? (
            <div>
              <h3 className="mb-2 text-sm font-semibold text-slate-900">Detected Schema</h3>
              <div className="overflow-x-auto rounded-md border border-slate-200">
                <table className="min-w-full text-left text-sm">
                  <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
                    <tr>
                      <th className="px-3 py-2">Name</th>
                      <th className="px-3 py-2">Type</th>
                      <th className="px-3 py-2">Nullable</th>
                      <th className="px-3 py-2">Position</th>
                      <th className="px-3 py-2">Samples</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {columns.map((column) => (
                      <tr key={`${column.ordinal_position}-${column.name}`}>
                        <td className="px-3 py-2 text-slate-900">{column.name}</td>
                        <td className="px-3 py-2 text-slate-700">{column.data_type}</td>
                        <td className="px-3 py-2 text-slate-700">{String(column.nullable)}</td>
                        <td className="px-3 py-2 text-slate-700">{column.ordinal_position}</td>
                        <td className="max-w-sm truncate px-3 py-2 text-slate-700">{column.sample_values?.join(", ") || "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}

          <div>
            <h3 className="mb-2 text-sm font-semibold text-slate-900">CSV Preview</h3>
            <CsvPreview preview={csvPreview} />
          </div>

          <div>
            <h3 className="mb-2 text-sm font-semibold text-slate-900">BigQuery Table Info</h3>
            <BigQueryInfo info={bigQueryInfo} />
          </div>
        </div>
      ) : null}
    </SectionCard>
  );
}
