import type { BackendStatusKey, BackendStatusResult } from "@/lib/types";
import SectionCard from "./SectionCard";

type BackendStatusSectionProps = {
  statuses: Partial<Record<BackendStatusKey, BackendStatusResult>>;
  loading: string | null;
  onCheck: (key: BackendStatusKey) => void;
};

const checks: { key: BackendStatusKey; label: string; path: string }[] = [
  { key: "root", label: "Check Root", path: "GET /" },
  { key: "health", label: "Check Health", path: "GET /health" },
  { key: "database", label: "Check Database", path: "GET /health/db" },
];

export default function BackendStatusSection({ statuses, loading, onCheck }: BackendStatusSectionProps) {
  return (
    <SectionCard title="Backend Status" description="These checks do not require authentication.">
      <div className="grid gap-3 md:grid-cols-3">
        {checks.map((check) => {
          const status = statuses[check.key];
          const isLoading = loading === check.key;
          return (
            <div key={check.key} className="rounded-md border border-slate-200 p-3">
              <div className="mb-3 flex items-center justify-between gap-2">
                <span className="text-sm font-medium text-slate-800">{check.path}</span>
                {status ? (
                  <span className={`rounded-full px-2 py-1 text-xs font-medium ${status.ok ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"}`}>
                    {status.ok ? "OK" : "Failed"}
                  </span>
                ) : null}
              </div>
              <button className="btn-primary w-full" disabled={isLoading} onClick={() => onCheck(check.key)}>
                {isLoading ? "Checking..." : check.label}
              </button>
              {status ? <p className="mt-2 text-xs text-slate-600">{status.message}</p> : null}
            </div>
          );
        })}
      </div>
    </SectionCard>
  );
}
