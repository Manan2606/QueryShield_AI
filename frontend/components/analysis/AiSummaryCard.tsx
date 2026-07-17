type AiSummaryCardProps = {
  summary: string | null;
  status: string;
  error?: string | null;
};

const FALLBACK = "AI summary is not available for this result. You can still review the table below.";

function statusLabel(status: string) {
  if (status === "completed") return "Completed";
  if (status === "failed") return "Unavailable";
  if (status === "disabled") return "Disabled";
  if (status === "pending") return "Pending";
  return "Not available";
}

function badgeClass(status: string) {
  if (status === "completed") return "status-badge border-emerald-200 bg-emerald-50 text-emerald-700";
  if (status === "failed") return "status-badge border-amber-200 bg-amber-50 text-amber-700";
  return "status-badge border-slate-200 bg-slate-100 text-slate-700";
}

export default function AiSummaryCard({ summary, status, error }: AiSummaryCardProps) {
  const display = status === "completed" && summary ? summary : error || FALLBACK;
  return (
    <section className="app-surface p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-bold text-slate-950">AI Summary</h3>
          <p className="mt-1 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">AI-generated interpretation based only on returned results</p>
        </div>
        <span className={badgeClass(status)}>{statusLabel(status)}</span>
      </div>
      <p className="mt-4 whitespace-pre-wrap text-sm leading-6 text-slate-700">{display}</p>
    </section>
  );
}
