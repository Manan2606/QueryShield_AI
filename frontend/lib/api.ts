import type {
  AuthToken,
  BigQueryLoadResponse,
  BigQueryTableInfo,
  CSVPreviewResponse,
  CSVUploadResponse,
  Dataset,
  DatasetDetail,
  QueryDryRunResponse,
  QueryGenerateResponse,
  QueryRequestSummary,
  SQLValidationResponse,
  User,
} from "./types";

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

type ApiRequestOptions = {
  method?: string;
  body?: unknown;
  token?: string | null;
  headers?: HeadersInit;
};

export class ApiError extends Error {
  status?: number;
  data?: unknown;
  isNetworkError: boolean;

  constructor(message: string, options: { status?: number; data?: unknown; isNetworkError?: boolean } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = options.status;
    this.data = options.data;
    this.isNetworkError = options.isNetworkError ?? false;
  }
}

function backendMessage(status: number, data: unknown): string {
  if (data && typeof data === "object" && "detail" in data) {
    const detail = (data as { detail: unknown }).detail;
    if (typeof detail === "string") {
      return detail;
    }
    return JSON.stringify(detail);
  }

  return `Request failed with status ${status}`;
}

async function parseResponse(response: Response): Promise<unknown> {
  if (response.status === 204) {
    return undefined;
  }

  const text = await response.text();
  if (!text) {
    return undefined;
  }

  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const method = options.method || "GET";
  let body: BodyInit | undefined;

  if (options.token) {
    headers.set("Authorization", `Bearer ${options.token}`);
  }

  if (options.body instanceof FormData) {
    body = options.body;
  } else if (options.body instanceof URLSearchParams) {
    headers.set("Content-Type", "application/x-www-form-urlencoded");
    body = options.body;
  } else if (options.body !== undefined) {
    if (!headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    body = JSON.stringify(options.body);
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body,
    });
  } catch (error) {
    throw new ApiError("Backend is unreachable.", { data: error, isNetworkError: true });
  }

  const data = await parseResponse(response);
  if (!response.ok) {
    throw new ApiError(backendMessage(response.status, data), {
      status: response.status,
      data,
    });
  }

  return data as T;
}

export function checkRoot() {
  return apiRequest<Record<string, unknown>>("/");
}

export function checkHealth() {
  return apiRequest<Record<string, unknown>>("/health");
}

export function checkDatabaseHealth() {
  return apiRequest<Record<string, unknown>>("/health/db");
}

export function signup(payload: { email: string; password: string; full_name?: string | null }) {
  return apiRequest<User>("/auth/signup", { method: "POST", body: payload });
}

export function login(email: string, password: string) {
  const form = new URLSearchParams();
  form.set("username", email);
  form.set("password", password);
  return apiRequest<AuthToken>("/auth/login", { method: "POST", body: form });
}

export function getCurrentUser(token: string) {
  return apiRequest<User>("/users/me", { token });
}

export function createDataset(token: string, payload: { name: string; description?: string | null }) {
  return apiRequest<Dataset>("/datasets", { method: "POST", token, body: payload });
}

export function listDatasets(token: string) {
  return apiRequest<Dataset[]>("/datasets", { token });
}

export function getDataset(token: string, datasetId: number) {
  return apiRequest<DatasetDetail>(`/datasets/${datasetId}`, { token });
}

export function updateDataset(token: string, datasetId: number, payload: { name?: string; description?: string | null }) {
  return apiRequest<Dataset>(`/datasets/${datasetId}`, { method: "PATCH", token, body: payload });
}

export function deleteDataset(token: string, datasetId: number) {
  return apiRequest<{ message: string }>(`/datasets/${datasetId}`, { method: "DELETE", token });
}

export function uploadCsv(token: string, datasetId: number, file: File) {
  const form = new FormData();
  form.set("file", file);
  return apiRequest<CSVUploadResponse>(`/datasets/${datasetId}/upload-csv`, { method: "POST", token, body: form });
}

export function previewCsv(token: string, datasetId: number) {
  return apiRequest<CSVPreviewResponse>(`/datasets/${datasetId}/preview`, { token });
}

export function loadBigQuery(token: string, datasetId: number) {
  return apiRequest<BigQueryLoadResponse>(`/datasets/${datasetId}/load-bigquery`, { method: "POST", token });
}

export function getBigQueryInfo(token: string, datasetId: number) {
  return apiRequest<BigQueryTableInfo>(`/datasets/${datasetId}/bigquery-info`, { token });
}

export function generateSql(token: string, payload: { dataset_id: number; question: string }) {
  return apiRequest<QueryGenerateResponse>("/queries/generate", { method: "POST", token, body: payload });
}

export function listQueryRequests(token: string, datasetId?: number) {
  const query = datasetId ? `?dataset_id=${datasetId}` : "";
  return apiRequest<QueryRequestSummary[]>(`/queries${query}`, { token });
}


export function validateSql(token: string, queryRequestId: number) {
  return apiRequest<SQLValidationResponse>(`/queries/${queryRequestId}/validate`, { method: "POST", token });
}

export function getSqlValidation(token: string, queryRequestId: number) {
  return apiRequest<SQLValidationResponse>(`/queries/${queryRequestId}/validation`, { token });
}

export function runCostDryRun(token: string, queryRequestId: number) {
  return apiRequest<QueryDryRunResponse>(`/queries/${queryRequestId}/dry-run`, { method: "POST", token });
}

export function getCostDryRun(token: string, queryRequestId: number) {
  return apiRequest<QueryDryRunResponse>(`/queries/${queryRequestId}/dry-run`, { token });
}
