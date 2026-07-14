type AnalysisErrorStateProps = {
  title: string;
  message: string | null;
  suggestions?: string[];
  onRetry?: () => void;
};

export default function AnalysisErrorState({ title, message, suggestions = [], onRetry }: AnalysisErrorStateProps) {
  if (!message) return null;
  return (
    <section className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-rose-900 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-base font-bold">{title}</h3>
          <p className="mt-1 text-sm leading-6">{message}</p>
          {suggestions.length ? (
            <ul className="mt-3 list-disc space-y-1 pl-5 text-sm">
              {suggestions.map((suggestion) => <li key={suggestion}>{suggestion}</li>)}
            </ul>
          ) : null}
        </div>
        {onRetry ? <button className="btn-secondary" onClick={onRetry} type="button">Retry</button> : null}
      </div>
    </section>
  );
}