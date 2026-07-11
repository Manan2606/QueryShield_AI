import type { ReactNode } from "react";

type SectionCardProps = {
  title: string;
  description?: string;
  children: ReactNode;
};

export default function SectionCard({ title, description, children }: SectionCardProps) {
  return (
    <section className="relative overflow-hidden rounded-2xl border border-slate-200/80 bg-white/90 p-6 shadow-[0_24px_70px_rgba(15,23,42,0.08)] backdrop-blur-xl">
      <div className="absolute inset-x-0 top-0 h-1 bg-[linear-gradient(90deg,_#0f172a_0%,_#14b8a6_50%,_#f59e0b_100%)]" />
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-slate-950">{title}</h2>
        {description ? <p className="mt-1 text-sm leading-6 text-slate-600">{description}</p> : null}
      </div>
      {children}
    </section>
  );
}
