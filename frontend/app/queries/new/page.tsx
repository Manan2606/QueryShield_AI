"use client";

import Link from "next/link";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import AiSummaryCard from "@/components/analysis/AiSummaryCard";
import AnalysisErrorState from "@/components/analysis/AnalysisErrorState";
import AnalysisProgress, { type AnalysisStage } from "@/components/analysis/AnalysisProgress";
import AnalysisResultHeader from "@/components/analysis/AnalysisResultHeader";
import DatasetSelector from "@/components/analysis/DatasetSelector";
import GovernanceDetails from "@/components/analysis/GovernanceDetails";
import QuestionComposer from "@/components/analysis/QuestionComposer";
import ResultChart from "@/components/analysis/ResultChart";
import AppShell from "@/components/mvp/AppShell";
import EmptyState from "@/components/mvp/EmptyState";
import ResultTable from "@/components/mvp/ResultTable";
import StatusBadge from "@/components/mvp/StatusBadge";
import * as api from "@/lib/api";
import type { AuditLog, Dataset, QueryDryRunResponse, QueryExecutionResponse, QueryGenerateResponse, SQLValidationResponse } from "@/lib/types";

export default function NewQueryPage() {
  return (
    <AppShell title="Analysis">
      {({ token }) => (
        <Suspense fallback={<div className="app-surface p-4 text-sm text-slate-600">Loading analysis workspace...</div>}>
          <NewQueryContent token={token} />
        </Suspense>
      )}
    </AppShell>
  );
}

function friendlyApiError(err: unknown, fallback: string): string {
  return err instanceof api.ApiError ? err.message : fallback;
}

function validationFailureMessage(validation: SQLValidationResponse): string {
  if (validation.errors.length) return validation.errors[0];
  if (validation.validation_status !== "passed") return "The generated query did not pass validation.";
  return "The generated query was not marked safe.";
}

function dryRunFailureMessage(dryRun: QueryDryRunResponse): string {
  if (dryRun.bytes_limit_exceeded) return "This analysis would process more data than the allowed limit.";
  if (dryRun.dry_run_error) return dryRun.dry_run_error;
  if (!dryRun.dry_run_valid) return "We couldn't estimate this query safely, so it was not executed.";
  if (!dryRun.execution_eligible) return "The backend did not mark this analysis as eligible for execution.";
  return "We couldn't estimate this query safely, so it was not executed.";
}

function NewQueryContent({ token }: { token: string }) {
  const searchParams = useSearchParams();
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [datasetId, setDatasetId] = useState(searchParams.get("dataset_id") || "");
  const [question, setQuestion] = useState("");
  const [generated, setGenerated] = useState<QueryGenerateResponse | null>(null);
  const [validation, setValidation] = useState<SQLValidationResponse | null>(null);
  const [dryRun, setDryRun] = useState<QueryDryRunResponse | null>(null);
  const [execution, setExecution] = useState<QueryExecutionResponse | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [stage, setStage] = useState<AnalysisStage>("idle");
  const [loadingDatasets, setLoadingDatasets] = useState(true);
  const [errorTitle, setErrorTitle] = useState("Analysis could not be completed");
  const [error, setError] = useState<string | null>(null);
  const [costBlocked, setCostBlocked] = useState(false);

  useEffect(() => {
    let mounted = true;
    async function loadDatasets() {
      setLoadingDatasets(true);
      setError(null);
      try {
        const data = await api.listDatasets(token);
        if (!mounted) return;
        setDatasets(data);
      } catch (err) {
        if (mounted) {
          setErrorTitle("Datasets could not be loaded");
          setError(friendlyApiError(err, "Datasets failed to load."));
          setStage("failed");
        }
      } finally {
        if (mounted) setLoadingDatasets(false);
      }
    }
    void loadDatasets();
    return () => { mounted = false; };
  }, [token]);

  const selectedDataset = useMemo(() => datasets.find((dataset) => String(dataset.id) === datasetId) || null, [datasets, datasetId]);
  const loadedDatasets = useMemo(() => datasets.filter((dataset) => dataset.status === "loaded"), [datasets]);
  const running = ["generating", "validating", "estimating", "executing", "summarizing"].includes(stage);
  const queryId = generated?.id || validation?.query_request_id || dryRun?.query_request_id || execution?.query_request_id || null;
  const canAnalyze = Boolean(selectedDataset?.status === "loaded" && question.trim() && !running);

  function resetAnalysis() {
    setGenerated(null);
    setValidation(null);
    setDryRun(null);
    setExecution(null);
    setAuditLogs([]);
    setStage("idle");
    setError(null);
    setCostBlocked(false);
  }

  function handleDatasetChange(nextDatasetId: string) {
    setDatasetId(nextDatasetId);
    resetAnalysis();
  }

  function handleQuestionChange(nextQuestion: string) {
    setQuestion(nextQuestion);
    if (generated || validation || dryRun || execution || error) {
      resetAnalysis();
    }
  }

  async function loadAuditLogs(nextQueryId: number) {
    try {
      const response = await api.getQueryAuditLogs(token, nextQueryId);
      setAuditLogs(response.items);
    } catch {
      setAuditLogs([]);
    }
  }

  async function analyze() {
    if (!selectedDataset || selectedDataset.status !== "loaded" || !question.trim()) return;

    setGenerated(null);
    setValidation(null);
    setDryRun(null);
    setExecution(null);
    setAuditLogs([]);
    setError(null);
    setErrorTitle("Analysis could not be completed");
    setCostBlocked(false);

    let nextGenerated: QueryGenerateResponse | null = null;
    try {
      setStage("generating");
      nextGenerated = await api.generateSql(token, { dataset_id: selectedDataset.id, question: question.trim() });
      setGenerated(nextGenerated);
    } catch (err) {
      setStage("failed");
      setErrorTitle("We couldn't generate a query from that question.");
      setError(friendlyApiError(err, "Try making the question more specific."));
      return;
    }

    try {
      setStage("validating");
      const nextValidation = await api.validateSql(token, nextGenerated.id);
      setValidation(nextValidation);
      if (nextValidation.validation_status !== "passed" || nextValidation.is_safe !== true) {
        setStage("blocked");
        setErrorTitle("This query was blocked by QueryShield's safety rules.");
        setError(validationFailureMessage(nextValidation));
        await loadAuditLogs(nextGenerated.id);
        return;
      }
    } catch (err) {
      setStage("failed");
      setErrorTitle("This query was blocked by QueryShield's safety rules.");
      setError(friendlyApiError(err, "Validation could not be completed."));
      await loadAuditLogs(nextGenerated.id);
      return;
    }

    let nextDryRun: QueryDryRunResponse;
    try {
      setStage("estimating");
      nextDryRun = await api.runCostDryRun(token, nextGenerated.id);
      setDryRun(nextDryRun);
      if (nextDryRun.dry_run_status !== "passed" || !nextDryRun.dry_run_valid || !nextDryRun.execution_eligible || nextDryRun.bytes_limit_exceeded) {
        setStage("blocked");
        setCostBlocked(nextDryRun.bytes_limit_exceeded);
        setErrorTitle(nextDryRun.bytes_limit_exceeded ? "This analysis would process more data than the allowed limit." : "We couldn't estimate this query safely, so it was not executed.");
        setError(dryRunFailureMessage(nextDryRun));
        await loadAuditLogs(nextGenerated.id);
        return;
      }
    } catch (err) {
      setStage("failed");
      setErrorTitle("We couldn't estimate this query safely, so it was not executed.");
      setError(friendlyApiError(err, "Dry run failed before execution."));
      await loadAuditLogs(nextGenerated.id);
      return;
    }

    try {
      setStage("executing");
      const nextExecution = await api.executeQuery(token, nextGenerated.id, { row_limit: 100 });
      setExecution(nextExecution);
      if (nextExecution.execution_status !== "succeeded") {
        setStage("failed");
        setErrorTitle("The query passed its checks but could not be completed.");
        setError(nextExecution.execution_error || "Execution did not complete successfully.");
        await loadAuditLogs(nextGenerated.id);
        return;
      }
    } catch (err) {
      setStage("failed");
      setErrorTitle("The query passed its checks but could not be completed.");
      setError(friendlyApiError(err, "Execution failed."));
      await loadAuditLogs(nextGenerated.id);
      return;
    }

    setStage("summarizing");
    await loadAuditLogs(nextGenerated.id);
    setStage("complete");
  }

  return (
    <div className="space-y-6">
      <section className="app-surface p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-2xl font-black text-slate-950">Ask a question. Get governed results.</h2>
              {selectedDataset ? <StatusBadge status={selectedDataset.status === "loaded" ? "ready" : selectedDataset.status} /> : null}
            </div>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              QueryShield generates SQL, checks safety, estimates processing, and runs only approved analysis behind one Analyze button.
            </p>
          </div>
          <Link className="btn-secondary" href="/history">View history</Link>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[minmax(18rem,24rem)_1fr]">
        <div className="app-surface p-4">
          <DatasetSelector datasets={datasets} loading={loadingDatasets || running} onChange={handleDatasetChange} selectedDatasetId={datasetId} />
        </div>
        <div className="app-surface p-4">
          <QuestionComposer disabled={!canAnalyze} onAnalyze={() => void analyze()} onChange={handleQuestionChange} question={question} running={running} />
        </div>
      </section>

      {!datasets.length && !loadingDatasets ? <EmptyState title="Create and prepare a dataset before asking questions" action={<Link className="btn-primary" href="/datasets">Open datasets</Link>} /> : null}
      {datasets.length > 0 && !loadedDatasets.length && !loadingDatasets ? <EmptyState title="Prepare a dataset for analysis" action={<Link className="btn-primary" href="/datasets">Review datasets</Link>} /> : null}

      <AnalysisProgress stage={stage} />
      <AnalysisErrorState
        message={error}
        onRetry={stage === "failed" && selectedDataset?.status === "loaded" ? () => void analyze() : undefined}
        suggestions={costBlocked ? ["Add a date range.", "Ask for fewer columns.", "Narrow the category.", "Request a summary instead of individual rows."] : []}
        title={errorTitle}
      />

      {execution ? (
        <div className="space-y-6">
          <AnalysisResultHeader execution={execution} question={question} />
          <AiSummaryCard />
          <ResultChart execution={execution} />
          <section className="app-surface p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h3 className="text-base font-bold text-slate-950">Result table</h3>
              <span className="text-sm font-semibold text-slate-600">{execution.result_row_count.toLocaleString()} rows returned</span>
            </div>
            <div className="mt-4"><ResultTable columns={execution.result_columns} rows={execution.result_rows} /></div>
          </section>
        </div>
      ) : null}

      {(generated || validation || dryRun || execution) ? (
        <GovernanceDetails auditLogs={auditLogs} dryRun={dryRun} execution={execution} generated={generated} queryId={queryId} validation={validation} />
      ) : null}
    </div>
  );
}