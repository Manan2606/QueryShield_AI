import type { CSVPreviewResponse } from "@/lib/types";

type CsvPreviewProps = {
  preview: CSVPreviewResponse | null;
};

export default function CsvPreview({ preview }: CsvPreviewProps) {
  if (!preview) {
    return <p className="text-sm text-slate-600">No CSV preview loaded.</p>;
  }

  if (preview.rows.length === 0) {
    return <p className="text-sm text-slate-600">The CSV preview returned no rows.</p>;
  }

  return (
    <div className="overflow-x-auto rounded-md border border-slate-200">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
          <tr>
            {preview.columns.map((column) => (
              <th className="px-3 py-2" key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {preview.rows.map((row, index) => (
            <tr key={index}>
              {preview.columns.map((column) => (
                <td className="max-w-xs truncate px-3 py-2 text-slate-700" key={column}>{row[column] ?? ""}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
