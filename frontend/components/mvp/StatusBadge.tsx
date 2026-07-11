export default function StatusBadge({ status }: { status: string | null | undefined }) {
  const value = status || "unknown";
  let className = "status-badge border-slate-200 bg-slate-100 text-slate-700";
  if (["loaded", "generated", "passed", "succeeded", "schema_detected", "safe", "eligible"].includes(value)) {
    className = "status-badge border-emerald-200 bg-emerald-50 text-emerald-800";
  } else if (["loading", "running", "validating", "pending", "waiting"].includes(value)) {
    className = "status-badge border-sky-200 bg-sky-50 text-sky-800";
  } else if (["blocked", "timed_out", "truncated"].includes(value)) {
    className = "status-badge border-amber-200 bg-amber-50 text-amber-800";
  } else if (["failed", "error"].includes(value)) {
    className = "status-badge border-rose-200 bg-rose-50 text-rose-800";
  }
  return <span className={className}>{value.replaceAll("_", " ")}</span>;
}