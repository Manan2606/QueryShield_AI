type QuestionComposerProps = {
  question: string;
  onChange: (question: string) => void;
  onAnalyze: () => void;
  disabled: boolean;
  running: boolean;
};

const examples = [
  "Total sales by category",
  "Monthly revenue trend",
  "Top-performing regions",
  "Average order value",
  "Number of records by status",
];

export default function QuestionComposer({ question, onChange, onAnalyze, disabled, running }: QuestionComposerProps) {
  return (
    <div className="space-y-4">
      <label className="field-label" htmlFor="analysis-question">
        Ask a question
        <textarea
          className="input-field min-h-32 resize-y text-base"
          disabled={running}
          id="analysis-question"
          maxLength={2000}
          onChange={(event) => onChange(event.target.value)}
          placeholder="What were total sales by region?"
          value={question}
        />
      </label>
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">General examples</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {examples.map((example) => (
            <button
              className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm font-semibold text-slate-700 transition hover:border-teal-200 hover:bg-teal-50 hover:text-teal-800 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={running}
              key={example}
              onClick={() => onChange(example)}
              type="button"
            >
              {example}
            </button>
          ))}
        </div>
      </div>
      <button className="btn-primary w-full sm:w-auto" disabled={disabled || running} onClick={onAnalyze} type="button">
        {running ? "Analyzing..." : "Analyze"}
      </button>
    </div>
  );
}