import StatusBadge from "@/components/mvp/StatusBadge";
import { formatDate, formatNumber } from "@/components/mvp/format";
import type { QueryExecutionResponse } from "@/lib/types";

export default function AnalysisResultHeader({ question, execution }: { question: string; execution: QueryExecutionResponse }) {
  return (
    <section className="app-surface p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-xl font-black text-slate-950">Results</h2>
            <StatusBadge status={execution.execution_status} />
            {execution.result_truncated ? <StatusBadge status="truncated" /> : null}
          </div>
          <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-700">{question}</p>
        </div>
        <dl className="grid min-w-64 gap-2 rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm sm:grid-cols-2">
          <div><dt className="meta-label">Rows</dt><dd className="meta-value font-bold">{formatNumber(execution.result_row_count)}</dd></div>
          <div><dt className="meta-label">Completed</dt><dd className="meta-value">{formatDate(execution.execution_completed_at || execution.executed_at)}</dd></div>
        </dl>
      </div>
    </section>
  );
}