export type User = {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
};

export type AuthToken = {
  access_token: string;
  token_type: string;
};

export type DatasetColumn = {
  id?: number;
  name: string;
  data_type: string;
  nullable: boolean;
  ordinal_position: number;
  sample_values: string[] | null;
};

export type Dataset = {
  id: number;
  owner_id: number;
  name: string;
  description: string | null;
  source_type: string;
  original_filename: string | null;
  storage_path: string | null;
  bigquery_table_id: string | null;
  status: string;
  load_error: string | null;
  loaded_at: string | null;
  row_count: number | null;
  column_count: number | null;
  created_at: string;
  updated_at: string;
};

export type DatasetDetail = Dataset & {
  columns: DatasetColumn[];
};

export type CSVUploadResponse = {
  message: string;
  dataset_id: number;
  filename: string;
  row_count: number;
  column_count: number;
  columns: DatasetColumn[];
};

export type CSVPreviewResponse = {
  dataset_id: number;
  columns: string[];
  rows: Record<string, string | number | boolean | null | undefined>[];
};

export type BigQueryLoadResponse = {
  message: string;
  dataset_id: number;
  status: string;
  bigquery_table_id: string;
  row_count: number | null;
  column_count: number | null;
};

export type BigQueryTableField = {
  name: string;
  type: string;
  mode: string;
};

export type BigQueryTableInfo = {
  dataset_id: number;
  bigquery_table_id: string;
  num_rows: number | null;
  num_bytes: number | null;
  schema: BigQueryTableField[];
};


export type QueryGenerateResponse = {
  id: number;
  dataset_id: number;
  question: string;
  generated_sql: string;
  model_name: string | null;
  status: string;
  created_at: string;
};

export type QueryRequestSummary = {
  id: number;
  dataset_id: number;
  question: string;
  generated_sql: string | null;
  model_name: string | null;
  status: string;
  error_message: string | null;
  created_at: string;
};
export type ApiPanelState = {
  operation: string;
  ok: boolean;
  status?: number;
  data?: unknown;
  error?: unknown;
  timestamp: string;
};

export type BackendStatusKey = "root" | "health" | "database";

export type BackendStatusResult = {
  ok: boolean;
  status?: number;
  message: string;
};
