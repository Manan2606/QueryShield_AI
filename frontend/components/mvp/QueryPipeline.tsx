import StatusBadge from "./StatusBadge";

const labels = ["Generated", "Validated", "Cost Checked", "Executed"];

export default function QueryPipeline({ statuses }: { statuses: string[] }) {
  return (
    <div className="app-surface p-4">
      <div className="grid gap-3 md:grid-cols-4">
        {labels.map((label, index) => {
          const status = statuses[index] || "waiting";
          const complete = ["generated", "passed", "succeeded"].includes(status);
          return (
            <div className="relative rounded-md border border-slate-200 bg-gradient-to-br from-white to-slate-50 p-4" key={label}>
              {index < labels.length - 1 ? <div className="absolute left-[calc(100%_-_0.35rem)] top-1/2 hidden h-px w-4 bg-slate-300 md:block" /> : null}
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-bold uppercase tracking-normal text-slate-500">Stage {index + 1}</p>
                  <p className="mt-2 text-sm font-bold text-slate-950">{label}</p>
                </div>
                <span className={`flex h-8 w-8 items-center justify-center rounded-full border text-xs font-black ${complete ? "border-teal-200 bg-teal-50 text-teal-800" : "border-slate-200 bg-white text-slate-500"}`}>{index + 1}</span>
              </div>
              <div className="mt-4"><StatusBadge status={status} /></div>
            </div>
          );
        })}
      </div>
    </div>
  );
}