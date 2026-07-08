import type { BigQueryTableInfo } from "@/lib/types";

type BigQueryInfoProps = {
  info: BigQueryTableInfo | null;
};

export default function BigQueryInfo({ info }: BigQueryInfoProps) {
  if (!info) {
    return <p className="text-sm text-slate-600">No BigQuery table info loaded.</p>;
  }

  return (
    <div className="rounded-md border border-slate-200 p-3">
      <dl className="mb-3 grid gap-3 text-sm sm:grid-cols-3">
        <div><dt className="meta-label">Full table ID</dt><dd className="meta-value break-all">{info.bigquery_table_id}</dd></div>
        <div><dt className="meta-label">Rows</dt><dd className="meta-value">{info.num_rows ?? "-"}</dd></div>
        <div><dt className="meta-label">Bytes</dt><dd className="meta-value">{info.num_bytes ?? "-"}</dd></div>
      </dl>
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-3 py-2">Field name</th>
              <th className="px-3 py-2">Field type</th>
              <th className="px-3 py-2">Field mode</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {info.schema.map((field) => (
              <tr key={`${field.name}-${field.type}-${field.mode}`}>
                <td className="px-3 py-2 text-slate-900">{field.name}</td>
                <td className="px-3 py-2 text-slate-700">{field.type}</td>
                <td className="px-3 py-2 text-slate-700">{field.mode}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
