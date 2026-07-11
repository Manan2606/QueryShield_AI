import type { ReactNode } from "react";

export default function EmptyState({ title, action }: { title: string; action?: ReactNode }) {
  return (
    <div className="rounded-md border border-dashed border-slate-300 bg-slate-50/80 p-6 text-center">
      <div className="mx-auto mb-3 h-1.5 w-14 rounded-full bg-teal-400" />
      <p className="text-sm font-bold text-slate-900">{title}</p>
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}