export default function AiSummaryCard() {
  return (
    <section className="app-surface p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-bold text-slate-950">AI Summary</h3>
          <p className="mt-1 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">AI-generated interpretation</p>
        </div>
        <span className="status-badge border-slate-200 bg-slate-100 text-slate-700">Not available</span>
      </div>
      <p className="mt-4 text-sm leading-6 text-slate-700">
        AI summary is not available for this result. You can still review the table and chart below.
      </p>
    </section>
  );
}