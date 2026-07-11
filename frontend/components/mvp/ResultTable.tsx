import { displayCell } from "./format";

export default function ResultTable({ columns, rows }: { columns: { name: string }[]; rows: Record<string, unknown>[] }) {
  const headers = columns.length ? columns.map((column) => column.name) : Object.keys(rows[0] || {});
  if (!headers.length) return <p className="text-sm text-slate-600">No rows returned.</p>;

  return (
    <div className="overflow-x-auto rounded-md border border-slate-200 bg-white">
      <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
        <thead className="bg-slate-100 text-xs uppercase text-slate-600">
          <tr>{headers.map((header) => <th className="px-3 py-2 font-semibold" key={header}>{header}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-slate-100 text-slate-700">
          {rows.map((row, index) => (
            <tr key={index}>
              {headers.map((header) => <td className="max-w-sm whitespace-pre-wrap px-3 py-2 align-top" key={header}>{displayCell(row[header])}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
