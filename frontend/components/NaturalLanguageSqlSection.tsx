import { FormEvent, useEffect, useState } from "react";
import type { Dataset, QueryGenerateResponse } from "@/lib/types";
import SectionCard from "./SectionCard";

type NaturalLanguageSqlSectionProps = {
  token: string | null;
  dataset: Dataset | null;
  generatedQuery: QueryGenerateResponse | null;
  loading: boolean;
  onGenerate: (question: string) => Promise<void>;
};

export default function NaturalLanguageSqlSection({ token, dataset, generatedQuery, loading, onGenerate }: NaturalLanguageSqlSectionProps) {
  const [question, setQuestion] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setQuestion("");
    setCopied(false);
  }, [dataset?.id]);

  async function submitGenerate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onGenerate(question);
  }

  async function copySql() {
    if (!generatedQuery?.generated_sql) {
      return;
    }
    await navigator.clipboard.writeText(generatedQuery.generated_sql);
    setCopied(true);
  }

  const canGenerate = Boolean(token && dataset && question.trim() && !loading);

  return (
    <SectionCard title="Natural Language to SQL" description="Generate BigQuery SQL for the selected loaded dataset. Generated only - not executed.">
      {!token ? <p className="text-sm text-amber-700">Log in before generating SQL.</p> : null}
      {!dataset ? <p className="text-sm text-slate-600">Select a dataset before generating SQL.</p> : null}
      {dataset ? (
        <div className="space-y-4">
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-sm font-semibold text-slate-900">{dataset.name}</span>
              <span className="status-badge bg-slate-200 text-slate-700">{dataset.status}</span>
            </div>
            <p className="mt-2 break-all text-sm text-slate-600">{dataset.bigquery_table_id || "No BigQuery table ID"}</p>
          </div>

          <form className="space-y-3" onSubmit={submitGenerate}>
            <label className="field-label">Analytics question
              <textarea
                className="input-field min-h-28 resize-y"
                disabled={!token || !dataset}
                maxLength={2000}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="What is the total sales amount by region?"
                value={question}
              />
            </label>
            <div className="flex flex-wrap items-center gap-3">
              <button className="btn-primary" disabled={!canGenerate} type="submit">
                {loading ? "Generating SQL..." : "Generate SQL"}
              </button>
              <span className="status-badge bg-sky-100 text-sky-800">Generated only - not executed</span>
            </div>
          </form>

          {generatedQuery ? (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-3">
                <h3 className="text-sm font-semibold text-slate-900">Generated SQL</h3>
                <button className="btn-secondary" onClick={copySql} type="button">{copied ? "Copied" : "Copy SQL"}</button>
              </div>
              <pre className="max-h-96 overflow-auto rounded-md bg-slate-950 p-4 text-sm text-slate-100"><code>{generatedQuery.generated_sql}</code></pre>
            </div>
          ) : null}
        </div>
      ) : null}
    </SectionCard>
  );
}
