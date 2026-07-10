import { FormEvent, useEffect, useState } from "react";
import * as api from "@/lib/api";
import type { Dataset, QueryGenerateResponse, SQLValidationResponse } from "@/lib/types";
import SectionCard from "./SectionCard";

type NaturalLanguageSqlSectionProps = {
  token: string | null;
  dataset: Dataset | null;
  generatedQuery: QueryGenerateResponse | null;
  loading: boolean;
  onGenerate: (question: string) => Promise<void>;
  onValidationResult: (operation: string, data: SQLValidationResponse) => void;
  onValidationError: (operation: string, error: unknown) => void;
};

function validationBadgeClass(status: string): string {
  if (status === "passed") {
    return "status-badge bg-emerald-100 text-emerald-800";
  }
  if (status === "failed" || status === "error") {
    return "status-badge bg-red-100 text-red-800";
  }
  if (status === "validating") {
    return "status-badge bg-sky-100 text-sky-800";
  }
  return "status-badge bg-slate-200 text-slate-700";
}

function ValidationResultPanel({ result }: { result: SQLValidationResponse | null }) {
  if (!result) {
    return <span className="status-badge bg-slate-200 text-slate-700">Not validated</span>;
  }

  return (
    <div className="space-y-3 rounded-md border border-slate-200 bg-white p-3">
      <div className="flex flex-wrap items-center gap-3">
        <span className={validationBadgeClass(result.validation_status)}>{result.validation_status}</span>
        <span className={result.is_safe ? "status-badge bg-emerald-100 text-emerald-800" : "status-badge bg-red-100 text-red-800"}>
          {result.is_safe ? "Safe" : "Unsafe"}
        </span>
        {result.statement_type ? <span className="status-badge bg-slate-200 text-slate-700">{result.statement_type}</span> : null}
      </div>
      <p className="text-sm font-medium text-slate-900">Validation does not execute the query.</p>
      {result.validated_at ? <p className="text-xs text-slate-500">Validated at {new Date(result.validated_at).toLocaleString()}</p> : null}

      <div>
        <h4 className="text-xs font-semibold uppercase text-slate-500">Referenced tables</h4>
        {result.referenced_tables.length ? (
          <ul className="mt-1 space-y-1 text-sm text-slate-700">
            {result.referenced_tables.map((table) => <li className="break-all" key={table}>{table}</li>)}
          </ul>
        ) : <p className="mt-1 text-sm text-slate-600">None detected.</p>}
      </div>

      {result.errors.length ? (
        <div className="rounded-md border border-red-200 bg-red-50 p-3">
          <h4 className="text-sm font-semibold text-red-900">Validation errors</h4>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-red-800">
            {result.errors.map((error) => <li key={error}>{error}</li>)}
          </ul>
        </div>
      ) : null}

      {result.warnings.length ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-3">
          <h4 className="text-sm font-semibold text-amber-900">Validation warnings</h4>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-800">
            {result.warnings.map((warning) => <li key={warning}>{warning}</li>)}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

export default function NaturalLanguageSqlSection({
  token,
  dataset,
  generatedQuery,
  loading,
  onGenerate,
  onValidationResult,
  onValidationError,
}: NaturalLanguageSqlSectionProps) {
  const [question, setQuestion] = useState("");
  const [copied, setCopied] = useState(false);
  const [validationResult, setValidationResult] = useState<SQLValidationResponse | null>(null);
  const [validationLoading, setValidationLoading] = useState<"validate" | "stored" | null>(null);

  useEffect(() => {
    setQuestion("");
    setCopied(false);
    setValidationResult(null);
  }, [dataset?.id]);

  useEffect(() => {
    setCopied(false);
    setValidationResult(null);
  }, [generatedQuery?.id]);

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

  async function validateSql() {
    if (!token || !generatedQuery) {
      return;
    }
    const operation = `POST /queries/${generatedQuery.id}/validate`;
    setValidationLoading("validate");
    try {
      const data = await api.validateSql(token, generatedQuery.id);
      setValidationResult(data);
      onValidationResult(operation, data);
    } catch (error) {
      onValidationError(operation, error);
    } finally {
      setValidationLoading(null);
    }
  }

  async function viewStoredValidation() {
    if (!token || !generatedQuery) {
      return;
    }
    const operation = `GET /queries/${generatedQuery.id}/validation`;
    setValidationLoading("stored");
    try {
      const data = await api.getSqlValidation(token, generatedQuery.id);
      setValidationResult(data);
      onValidationResult(operation, data);
    } catch (error) {
      onValidationError(operation, error);
    } finally {
      setValidationLoading(null);
    }
  }

  const canGenerate = Boolean(token && dataset && question.trim() && !loading);
  const canValidate = Boolean(token && generatedQuery?.generated_sql && !validationLoading);

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
                <button className="btn-primary" disabled={!canValidate} onClick={validateSql} type="button">
                  {validationLoading === "validate" ? "Validating..." : "Validate SQL"}
                </button>
                <button className="btn-secondary" disabled={!canValidate} onClick={viewStoredValidation} type="button">
                  {validationLoading === "stored" ? "Loading..." : "View Stored Validation"}
                </button>
              </div>
              <pre className="max-h-96 overflow-auto rounded-md bg-slate-950 p-4 text-sm text-slate-100"><code>{generatedQuery.generated_sql}</code></pre>
              <ValidationResultPanel result={validationResult} />
              {validationResult?.is_safe !== true ? (
                <p className="text-sm text-slate-600">Execution-related actions remain unavailable until validation passes.</p>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}
    </SectionCard>
  );
}
