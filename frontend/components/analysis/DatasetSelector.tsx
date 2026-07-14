import Link from "next/link";
import StatusBadge from "@/components/mvp/StatusBadge";
import { formatNumber } from "@/components/mvp/format";
import type { Dataset } from "@/lib/types";

type DatasetSelectorProps = {
  datasets: Dataset[];
  selectedDatasetId: string;
  onChange: (datasetId: string) => void;
  loading: boolean;
};

function readinessLabel(dataset: Dataset | null): string {
  if (!dataset) return "Choose a dataset";
  if (dataset.status === "loaded") return "Ready for analysis";
  if (dataset.storage_path) return "Needs preparation";
  return "Needs CSV upload";
}

export default function DatasetSelector({ datasets, selectedDatasetId, onChange, loading }: DatasetSelectorProps) {
  const selectedDataset = datasets.find((dataset) => String(dataset.id) === selectedDatasetId) || null;
  const isReady = selectedDataset?.status === "loaded";

  return (
    <div className="space-y-3">
      <label className="field-label" htmlFor="dataset-selector">
        Select data
        <select
          className="input-field"
          disabled={loading}
          id="dataset-selector"
          onChange={(event) => onChange(event.target.value)}
          required
          value={selectedDatasetId}
        >
          <option value="">Choose a dataset</option>
          {datasets.map((dataset) => (
            <option key={dataset.id} value={dataset.id}>{dataset.name}</option>
          ))}
        </select>
      </label>

      {selectedDataset ? (
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="text-sm font-bold text-slate-950">{selectedDataset.name}</p>
              <p className="mt-1 text-xs text-slate-600">{selectedDataset.original_filename || "No CSV file uploaded yet"}</p>
            </div>
            <StatusBadge status={isReady ? "ready" : selectedDataset.status} />
          </div>
          <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-3">
            <div><dt className="meta-label">Rows</dt><dd className="meta-value">{formatNumber(selectedDataset.row_count)}</dd></div>
            <div><dt className="meta-label">Columns</dt><dd className="meta-value">{formatNumber(selectedDataset.column_count)}</dd></div>
            <div><dt className="meta-label">Status</dt><dd className="meta-value">{readinessLabel(selectedDataset)}</dd></div>
          </dl>
          {!isReady ? (
            <div className="mt-3 flex flex-wrap items-center gap-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
              <span>This dataset needs to be prepared before analysis.</span>
              <Link className="btn-secondary" href={`/datasets/${selectedDataset.id}`}>Prepare dataset</Link>
            </div>
          ) : null}
          <details className="mt-3 text-sm text-slate-600">
            <summary className="cursor-pointer font-semibold text-slate-700">Technical dataset details</summary>
            <dl className="mt-2 grid gap-2 sm:grid-cols-2">
              <div><dt className="font-semibold text-slate-900">Dataset ID</dt><dd>{selectedDataset.id}</dd></div>
              <div><dt className="font-semibold text-slate-900">BigQuery table</dt><dd className="break-all">{selectedDataset.bigquery_table_id || "Not available"}</dd></div>
            </dl>
          </details>
        </div>
      ) : null}
    </div>
  );
}