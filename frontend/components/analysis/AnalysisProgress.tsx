export type AnalysisStage = "idle" | "generating" | "validating" | "estimating" | "executing" | "summarizing" | "complete" | "blocked" | "failed";

type ProgressStep = {
  key: AnalysisStage;
  label: string;
  description: string;
};

const steps: ProgressStep[] = [
  { key: "generating", label: "Generating the analysis", description: "Creating SQL from your question" },
  { key: "validating", label: "Checking query safety", description: "Applying QueryShield rules" },
  { key: "estimating", label: "Estimating processing cost", description: "Running a BigQuery dry run" },
  { key: "executing", label: "Running the analysis", description: "Executing only approved SQL" },
  { key: "summarizing", label: "Preparing your results", description: "Formatting table, chart, and summary state" },
];

function stepState(stage: AnalysisStage, index: number): "complete" | "active" | "blocked" | "failed" | "waiting" {
  if (stage === "complete") return "complete";
  if (stage === "blocked") return index < 3 ? "complete" : "blocked";
  if (stage === "failed") return "failed";
  const activeIndex = steps.findIndex((step) => step.key === stage);
  if (activeIndex === -1) return "waiting";
  if (index < activeIndex) return "complete";
  if (index === activeIndex) return "active";
  return "waiting";
}

export default function AnalysisProgress({ stage }: { stage: AnalysisStage }) {
  if (stage === "idle") return null;

  return (
    <section className="app-surface p-4" aria-label="Analysis progress">
      <div className="flex flex-col gap-3 md:grid md:grid-cols-5">
        {steps.map((step, index) => {
          const state = stepState(stage, index);
          const complete = state === "complete";
          const active = state === "active";
          const blocked = state === "blocked";
          const failed = state === "failed";
          return (
            <div className="rounded-xl border border-slate-200 bg-white p-3" key={step.key}>
              <div className="flex items-start gap-3">
                <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-xs font-black ${complete ? "border-emerald-200 bg-emerald-50 text-emerald-800" : active ? "border-sky-200 bg-sky-50 text-sky-800" : blocked ? "border-amber-200 bg-amber-50 text-amber-800" : failed ? "border-rose-200 bg-rose-50 text-rose-800" : "border-slate-200 bg-slate-50 text-slate-500"}`}>
                  {complete ? "✓" : index + 1}
                </span>
                <div>
                  <p className="text-sm font-bold text-slate-950">{step.label}</p>
                  <p className="mt-1 text-xs leading-5 text-slate-500">{step.description}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}