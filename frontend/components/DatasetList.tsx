import type { Dataset } from "@/lib/types";
import SectionCard from "./SectionCard";

type DatasetListProps = {
  token: string | null;
  datasets: Dataset[];
  selectedDatasetId: number | null;
  loading: string | null;
  onRefresh: () => void;
  onSelect: (dataset: Dataset) => void;
  onDelete: (dataset: Dataset) => void;
};

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "-";
  }
  return new Date(value).toLocaleString();
}

export default function DatasetList({ token, datasets, selectedDatasetId, loading, onRefresh, onSelect, onDelete }: DatasetListProps) {
  return (
    <SectionCard title="Dataset List" description="Lists datasets owned by the authenticated user.">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <button className="btn-primary" disabled={!token || loading === "listDatasets"} onClick={onRefresh} type="button">
          {loading === "listDatasets" ? "Loading datasets..." : "Refresh"}
        </button>
        <span className="text-sm text-slate-600">{datasets.length} dataset{datasets.length === 1 ? "" : "s"}</span>
      </div>
      {!token ? <p className="text-sm text-amber-700">Log in to list datasets.</p> : null}
      {token && datasets.length === 0 ? <p className="text-sm text-slate-600">No datasets found.</p> : null}
      {datasets.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2">ID</th>
                <th className="px-3 py-2">Name</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">File</th>
                <th className="px-3 py-2">Rows</th>
                <th className="px-3 py-2">Columns</th>
                <th className="px-3 py-2">BigQuery</th>
                <th className="px-3 py-2">Updated</th>
                <th className="px-3 py-2">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {datasets.map((dataset) => (
                <tr key={dataset.id} className={dataset.id === selectedDatasetId ? "bg-emerald-50" : "bg-white"}>
                  <td className="px-3 py-3 align-top text-slate-700">{dataset.id}</td>
                  <td className="px-3 py-3 align-top">
                    <div className="font-medium text-slate-900">{dataset.name}</div>
                    <div className="max-w-xs text-xs text-slate-500">{dataset.description || "-"}</div>
                  </td>
                  <td className="px-3 py-3 align-top"><span className="status-badge bg-slate-100 text-slate-700">{dataset.status}</span></td>
                  <td className="px-3 py-3 align-top text-slate-700">{dataset.original_filename || "-"}</td>
                  <td className="px-3 py-3 align-top text-slate-700">{dataset.row_count ?? "-"}</td>
                  <td className="px-3 py-3 align-top text-slate-700">{dataset.column_count ?? "-"}</td>
                  <td className="max-w-xs break-all px-3 py-3 align-top text-xs text-slate-700">{dataset.bigquery_table_id || "-"}</td>
                  <td className="px-3 py-3 align-top text-slate-700">{formatDate(dataset.updated_at)}</td>
                  <td className="px-3 py-3 align-top">
                    <div className="flex flex-wrap gap-2">
                      <button className="btn-secondary" onClick={() => onSelect(dataset)} type="button">Select</button>
                      <button className="btn-danger" disabled={loading === `deleteDataset:${dataset.id}`} onClick={() => onDelete(dataset)} type="button">
                        {loading === `deleteDataset:${dataset.id}` ? "Deleting..." : "Delete"}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </SectionCard>
  );
}
