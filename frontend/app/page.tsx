"use client";

import { useEffect, useState } from "react";
import ApiResponsePanel from "@/components/ApiResponsePanel";
import AuthSection from "@/components/AuthSection";
import BackendStatusSection from "@/components/BackendStatusSection";
import CurrentUserSection from "@/components/CurrentUserSection";
import DatasetActions from "@/components/DatasetActions";
import DatasetCreateForm from "@/components/DatasetCreateForm";
import DatasetList from "@/components/DatasetList";
import NaturalLanguageSqlSection from "@/components/NaturalLanguageSqlSection";
import * as api from "@/lib/api";
import { clearStoredToken, getStoredToken, storeToken } from "@/lib/auth";
import type {
  ApiPanelState,
  BackendStatusKey,
  BackendStatusResult,
  BigQueryTableInfo,
  CSVPreviewResponse,
  Dataset,
  DatasetColumn,
  QueryDryRunResponse,
  QueryGenerateResponse,
  SQLValidationResponse,
  User,
} from "@/lib/types";

function nowStamp(): string {
  return new Date().toLocaleString();
}

function errorPayload(error: unknown): { status?: number; data: unknown; message: string } {
  if (error instanceof api.ApiError) {
    return {
      status: error.status,
      data: error.data ?? { message: error.message },
      message: error.message,
    };
  }

  if (error instanceof Error) {
    return { data: { message: error.message }, message: error.message };
  }

  return { data: { message: "Unknown error", error }, message: "Unknown error" };
}

export default function Home() {
  const [token, setToken] = useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [selectedColumns, setSelectedColumns] = useState<DatasetColumn[]>([]);
  const [csvPreview, setCsvPreview] = useState<CSVPreviewResponse | null>(null);
  const [bigQueryInfo, setBigQueryInfo] = useState<BigQueryTableInfo | null>(null);
  const [generatedQuery, setGeneratedQuery] = useState<QueryGenerateResponse | null>(null);
  const [apiPanel, setApiPanel] = useState<ApiPanelState | null>(null);
  const [backendStatuses, setBackendStatuses] = useState<Partial<Record<BackendStatusKey, BackendStatusResult>>>({});
  const [loading, setLoading] = useState<string | null>(null);

  function recordSuccess(operation: string, data: unknown, status?: number) {
    setApiPanel({ operation, ok: true, status, data, timestamp: nowStamp() });
  }

  function recordError(operation: string, error: unknown) {
    const payload = errorPayload(error);
    setApiPanel({ operation, ok: false, status: payload.status, error: payload.data, timestamp: nowStamp() });
    return payload;
  }

  async function refreshDatasets(activeToken: string, operation = "GET /datasets") {
    const data = await api.listDatasets(activeToken);
    setDatasets(data);
    setSelectedDataset((current) => {
      if (!current) {
        return current;
      }
      return data.find((dataset) => dataset.id === current.id) ?? current;
    });
    recordSuccess(operation, data);
    return data;
  }

  async function refreshSelectedDataset(activeToken: string, datasetId: number, operation = `GET /datasets/${datasetId}`) {
    const data = await api.getDataset(activeToken, datasetId);
    setSelectedDataset(data);
    setSelectedColumns(data.columns || []);
    recordSuccess(operation, data);
    return data;
  }

  function clearDatasetState() {
    setDatasets([]);
    setSelectedDataset(null);
    setSelectedColumns([]);
    setCsvPreview(null);
    setBigQueryInfo(null);
    setGeneratedQuery(null);
  }

  useEffect(() => {
    const storedToken = getStoredToken();
    if (!storedToken) {
      return;
    }

    setToken(storedToken);
    setLoading("restoreSession");
    api.getCurrentUser(storedToken)
      .then(async (user) => {
        setCurrentUser(user);
        const loadedDatasets = await api.listDatasets(storedToken);
        setDatasets(loadedDatasets);
        recordSuccess("Restore token and GET /users/me", { user, datasets: loadedDatasets });
      })
      .catch((error) => {
        clearStoredToken();
        setToken(null);
        setCurrentUser(null);
        clearDatasetState();
        recordError("Restore token", error);
      })
      .finally(() => setLoading(null));
  }, []);

  async function handleBackendCheck(key: BackendStatusKey) {
    const operation = key === "root" ? "GET /" : key === "health" ? "GET /health" : "GET /health/db";
    setLoading(key);
    try {
      const data = key === "root" ? await api.checkRoot() : key === "health" ? await api.checkHealth() : await api.checkDatabaseHealth();
      setBackendStatuses((current) => ({ ...current, [key]: { ok: true, message: "Backend responded successfully." } }));
      recordSuccess(operation, data);
    } catch (error) {
      const payload = recordError(operation, error);
      setBackendStatuses((current) => ({ ...current, [key]: { ok: false, status: payload.status, message: payload.message } }));
    } finally {
      setLoading(null);
    }
  }

  async function handleSignup(payload: { full_name: string; email: string; password: string }) {
    setLoading("signup");
    try {
      const data = await api.signup({
        email: payload.email,
        password: payload.password,
        full_name: payload.full_name || null,
      });
      recordSuccess("POST /auth/signup", data, 201);
    } catch (error) {
      recordError("POST /auth/signup", error);
    } finally {
      setLoading(null);
    }
  }

  async function handleLogin(email: string, password: string) {
    setLoading("login");
    try {
      const auth = await api.login(email, password);
      storeToken(auth.access_token);
      setToken(auth.access_token);
      const user = await api.getCurrentUser(auth.access_token);
      setCurrentUser(user);
      const loadedDatasets = await api.listDatasets(auth.access_token);
      setDatasets(loadedDatasets);
      recordSuccess("POST /auth/login", { auth, user, datasets: loadedDatasets });
    } catch (error) {
      clearStoredToken();
      setToken(null);
      setCurrentUser(null);
      clearDatasetState();
      recordError("POST /auth/login", error);
    } finally {
      setLoading(null);
    }
  }

  function handleLogout() {
    clearStoredToken();
    setToken(null);
    setCurrentUser(null);
    clearDatasetState();
    recordSuccess("Logout", { message: "Token removed and frontend state cleared." });
  }

  async function handleGetCurrentUser() {
    if (!token) {
      return;
    }

    setLoading("currentUser");
    try {
      const data = await api.getCurrentUser(token);
      setCurrentUser(data);
      recordSuccess("GET /users/me", data);
    } catch (error) {
      recordError("GET /users/me", error);
    } finally {
      setLoading(null);
    }
  }

  async function handleCreateDataset(payload: { name: string; description?: string | null }) {
    if (!token) {
      return;
    }

    setLoading("createDataset");
    try {
      const data = await api.createDataset(token, payload);
      await refreshDatasets(token, "GET /datasets after create");
      setSelectedDataset(data);
      setSelectedColumns([]);
      setCsvPreview(null);
      setBigQueryInfo(null);
      setGeneratedQuery(null);
      recordSuccess("POST /datasets", data, 201);
    } catch (error) {
      recordError("POST /datasets", error);
    } finally {
      setLoading(null);
    }
  }

  async function handleRefreshDatasets() {
    if (!token) {
      return;
    }

    setLoading("listDatasets");
    try {
      await refreshDatasets(token);
    } catch (error) {
      recordError("GET /datasets", error);
    } finally {
      setLoading(null);
    }
  }

  async function handleSelectDataset(dataset: Dataset) {
    if (!token) {
      return;
    }

    setSelectedDataset(dataset);
    setCsvPreview(null);
    setBigQueryInfo(null);
    setGeneratedQuery(null);
    setLoading("datasetDetail");
    try {
      await refreshSelectedDataset(token, dataset.id);
    } catch (error) {
      recordError(`GET /datasets/${dataset.id}`, error);
    } finally {
      setLoading(null);
    }
  }

  async function handleDeleteDataset(dataset: Dataset) {
    if (!token || !window.confirm(`Delete dataset ${dataset.id}: ${dataset.name}?`)) {
      return;
    }

    setLoading(`deleteDataset:${dataset.id}`);
    try {
      const data = await api.deleteDataset(token, dataset.id);
      if (selectedDataset?.id === dataset.id) {
        setSelectedDataset(null);
        setSelectedColumns([]);
        setCsvPreview(null);
        setBigQueryInfo(null);
        setGeneratedQuery(null);
      }
      await refreshDatasets(token, "GET /datasets after delete");
      recordSuccess(`DELETE /datasets/${dataset.id}`, data);
    } catch (error) {
      recordError(`DELETE /datasets/${dataset.id}`, error);
    } finally {
      setLoading(null);
    }
  }

  async function handleRefreshSelectedDataset() {
    if (!token || !selectedDataset) {
      return;
    }

    setLoading("datasetDetail");
    try {
      await refreshSelectedDataset(token, selectedDataset.id);
    } catch (error) {
      recordError(`GET /datasets/${selectedDataset.id}`, error);
    } finally {
      setLoading(null);
    }
  }

  async function handleUpdateDataset(payload: { name?: string; description?: string | null }) {
    if (!token || !selectedDataset) {
      return;
    }

    if (Object.keys(payload).length === 0) {
      recordSuccess("PATCH /datasets skipped", { message: "No metadata changes to send." });
      return;
    }

    setLoading("updateDataset");
    try {
      const data = await api.updateDataset(token, selectedDataset.id, payload);
      setSelectedDataset((current) => (current ? { ...current, ...data } : data));
      await refreshDatasets(token, "GET /datasets after update");
      recordSuccess(`PATCH /datasets/${selectedDataset.id}`, data);
    } catch (error) {
      recordError(`PATCH /datasets/${selectedDataset.id}`, error);
    } finally {
      setLoading(null);
    }
  }

  async function handleUploadCsv(file: File) {
    if (!token || !selectedDataset) {
      return;
    }

    setLoading("uploadCsv");
    try {
      const data = await api.uploadCsv(token, selectedDataset.id, file);
      await refreshSelectedDataset(token, selectedDataset.id, `GET /datasets/${selectedDataset.id} after upload`);
      await refreshDatasets(token, "GET /datasets after upload");
      setCsvPreview(null);
      setBigQueryInfo(null);
      setGeneratedQuery(null);
      recordSuccess(`POST /datasets/${selectedDataset.id}/upload-csv`, data);
    } catch (error) {
      recordError(`POST /datasets/${selectedDataset.id}/upload-csv`, error);
    } finally {
      setLoading(null);
    }
  }

  async function handlePreviewCsv() {
    if (!token || !selectedDataset) {
      return;
    }

    setLoading("previewCsv");
    try {
      const data = await api.previewCsv(token, selectedDataset.id);
      setCsvPreview(data);
      recordSuccess(`GET /datasets/${selectedDataset.id}/preview`, data);
    } catch (error) {
      recordError(`GET /datasets/${selectedDataset.id}/preview`, error);
    } finally {
      setLoading(null);
    }
  }

  async function handleLoadBigQuery() {
    if (!token || !selectedDataset) {
      return;
    }

    setLoading("loadBigQuery");
    try {
      const data = await api.loadBigQuery(token, selectedDataset.id);
      await refreshSelectedDataset(token, selectedDataset.id, `GET /datasets/${selectedDataset.id} after BigQuery load`);
      await refreshDatasets(token, "GET /datasets after BigQuery load");
      setGeneratedQuery(null);
      recordSuccess(`POST /datasets/${selectedDataset.id}/load-bigquery`, data);
    } catch (error) {
      recordError(`POST /datasets/${selectedDataset.id}/load-bigquery`, error);
    } finally {
      setLoading(null);
    }
  }

  async function handleGetBigQueryInfo() {
    if (!token || !selectedDataset) {
      return;
    }

    setLoading("bigQueryInfo");
    try {
      const data = await api.getBigQueryInfo(token, selectedDataset.id);
      setBigQueryInfo(data);
      recordSuccess(`GET /datasets/${selectedDataset.id}/bigquery-info`, data);
    } catch (error) {
      recordError(`GET /datasets/${selectedDataset.id}/bigquery-info`, error);
    } finally {
      setLoading(null);
    }
  }


  function handleValidationResult(operation: string, data: SQLValidationResponse) {
    recordSuccess(operation, data);
  }

  function handleValidationError(operation: string, error: unknown) {
    recordError(operation, error);
  }
  function handleDryRunResult(operation: string, data: QueryDryRunResponse) {
    recordSuccess(operation, data);
  }

  function handleDryRunError(operation: string, error: unknown) {
    recordError(operation, error);
  }
  async function handleGenerateSql(question: string) {
    if (!token || !selectedDataset) {
      return;
    }

    setLoading("generateSql");
    try {
      const data = await api.generateSql(token, { dataset_id: selectedDataset.id, question });
      setGeneratedQuery(data);
      recordSuccess("POST /queries/generate", data);
    } catch (error) {
      recordError("POST /queries/generate", error);
    } finally {
      setLoading(null);
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <header className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm font-semibold uppercase text-slate-500">Internal backend testing interface</p>
          <h1 className="mt-2 text-3xl font-bold tracking-normal text-slate-950">QueryShield AI Test Console</h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-600">
            Use this temporary console to exercise the completed backend flows from a browser: health checks, auth, dataset CRUD, CSV upload and preview, BigQuery loading, and SQL generation.
          </p>
        </header>

        <BackendStatusSection statuses={backendStatuses} loading={loading} onCheck={handleBackendCheck} />
        <AuthSection token={token} currentUser={currentUser} loading={loading} onSignup={handleSignup} onLogin={handleLogin} onLogout={handleLogout} />
        <CurrentUserSection token={token} user={currentUser} loading={loading === "currentUser" || loading === "restoreSession"} onGetCurrentUser={handleGetCurrentUser} />
        <DatasetCreateForm token={token} loading={loading === "createDataset"} onCreate={handleCreateDataset} />
        <DatasetList token={token} datasets={datasets} selectedDatasetId={selectedDataset?.id ?? null} loading={loading} onRefresh={handleRefreshDatasets} onSelect={handleSelectDataset} onDelete={handleDeleteDataset} />
        <DatasetActions
          token={token}
          dataset={selectedDataset}
          columns={selectedColumns}
          csvPreview={csvPreview}
          bigQueryInfo={bigQueryInfo}
          loading={loading}
          onRefreshDetail={handleRefreshSelectedDataset}
          onUpdate={handleUpdateDataset}
          onUploadCsv={handleUploadCsv}
          onPreviewCsv={handlePreviewCsv}
          onLoadBigQuery={handleLoadBigQuery}
          onGetBigQueryInfo={handleGetBigQueryInfo}
        />
        <NaturalLanguageSqlSection
          token={token}
          dataset={selectedDataset}
          generatedQuery={generatedQuery}
          loading={loading === "generateSql"}
          onGenerate={handleGenerateSql}
          onValidationResult={handleValidationResult}
          onValidationError={handleValidationError}
          onDryRunResult={handleDryRunResult}
          onDryRunError={handleDryRunError}
        />
        <ApiResponsePanel response={apiPanel} />
      </div>
    </main>
  );
}
