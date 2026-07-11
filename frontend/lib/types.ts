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
  validation_status: string;
  is_safe: boolean | null;
  validation_errors: string[] | null;
  validation_warnings: string[] | null;
  validated_at: string | null;
  dry_run_status: string;
  estimated_bytes_processed: number | null;
  estimated_cost: string | null;
  bytes_limit_exceeded: boolean | null;
  execution_eligible: boolean;
  dry_run_at: string | null;
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
  validation_status: string;
  is_safe: boolean | null;
  validation_errors: string[] | null;
  validation_warnings: string[] | null;
  validated_at: string | null;
  dry_run_status: string;
  estimated_bytes_processed: number | null;
  estimated_cost: string | null;
  bytes_limit_exceeded: boolean | null;
  execution_eligible: boolean;
  dry_run_at: string | null;
};

export type SQLValidationResponse = {
  query_request_id: number;
  dataset_id: number;
  validation_status: string;
  is_safe: boolean;
  statement_type: string | null;
  referenced_tables: string[];
  errors: string[];
  warnings: string[];
  validated_at: string | null;
  generated_sql: string;
  normalized_sql: string | null;
};

export type QueryResultColumn = {
  name: string;
  field_type: string;
  mode: string | null;
};

export type QueryExecutionResponse = {
  query_request_id: number;
  dataset_id: number;
  execution_status: string;
  execution_job_id: string | null;
  execution_location: string | null;
  execution_bytes_processed: number | null;
  execution_bytes_billed: number | null;
  execution_cache_hit: boolean | null;
  result_row_count: number;
  result_columns: QueryResultColumn[];
  result_rows: Record<string, unknown>[];
  result_truncated: boolean;
  row_limit: number;
  execution_error: string | null;
  execution_started_at: string | null;
  execution_completed_at: string | null;
  executed_at: string | null;
  generated_sql: string;
};

export type QueryDryRunResponse = {
  query_request_id: number;
  dataset_id: number;
  dry_run_status: string;
  dry_run_valid: boolean;
  estimated_bytes_processed: number | null;
  estimated_mib_processed: number | null;
  estimated_gib_processed: number | null;
  estimated_tib_processed: number | null;
  maximum_bytes_billed: number;
  maximum_mib_billed: number;
  bytes_limit_exceeded: boolean;
  estimated_cost: string | null;
  estimated_cost_currency: string;
  execution_eligible: boolean;
  dry_run_error: string | null;
  dry_run_at: string | null;
  dry_run_job_id: string | null;
  dry_run_location: string | null;
  generated_sql: string;
  warnings: string[];
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

export type QueryHistoryItem = {
  id: number;
  dataset_id: number;
  dataset_name: string | null;
  question: string;
  generated_sql_preview: string | null;
  generation_status: string;
  validation_status: string;
  is_safe: boolean | null;
  dry_run_status: string;
  estimated_bytes_processed: number | null;
  estimated_cost: string | null;
  estimated_cost_currency: string | null;
  bytes_limit_exceeded: boolean | null;
  execution_eligible: boolean;
  execution_status: string;
  result_row_count: number | null;
  result_truncated: boolean | null;
  created_at: string;
  validated_at: string | null;
  dry_run_at: string | null;
  executed_at: string | null;
};

export type QueryHistoryListResponse = {
  items: QueryHistoryItem[];
  skip: number;
  limit: number;
  total: number;
  has_more: boolean;
};

export type QueryLifecycleResponse = {
  query: {
    id: number;
    user_id: number;
    dataset_id: number;
    dataset_name: string | null;
    bigquery_table_id: string | null;
    question: string;
    created_at: string;
    updated_at: string;
  };
  generation: {
    status: string;
    model_name: string | null;
    generated_sql: string | null;
    generated_for_table_id: string | null;
    error_message: string | null;
  };
  validation: {
    status: string;
    is_safe: boolean | null;
    statement_type: string | null;
    referenced_tables: string[];
    errors: string[];
    warnings: string[];
    validated_at: string | null;
  };
  dry_run: {
    status: string;
    dry_run_valid: boolean | null;
    estimated_bytes_processed: number | null;
    estimated_mib_processed: number | null;
    estimated_gib_processed: number | null;
    estimated_tib_processed: number | null;
    maximum_bytes_billed: number | null;
    estimated_cost: string | null;
    estimated_cost_currency: string | null;
    bytes_limit_exceeded: boolean | null;
    execution_eligible: boolean;
    dry_run_error: string | null;
    dry_run_job_id: string | null;
    dry_run_location: string | null;
    dry_run_at: string | null;
  };
  execution: {
    status: string;
    execution_job_id: string | null;
    execution_location: string | null;
    execution_bytes_processed: number | null;
    execution_bytes_billed: number | null;
    execution_cache_hit: boolean | null;
    result_row_count: number | null;
    result_columns: QueryResultColumn[];
    result_rows: Record<string, unknown>[];
    result_truncated: boolean | null;
    execution_error: string | null;
    execution_started_at: string | null;
    execution_completed_at: string | null;
    executed_at: string | null;
  };
  audit_summary: {
    total_events: number;
    latest_event_at: string | null;
  };
};

export type AuditLog = {
  id: number;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  details: Record<string, unknown> | null;
  created_at: string;
};

export type AuditLogListResponse = {
  items: AuditLog[];
  skip: number;
  limit: number;
  total: number;
  has_more: boolean;
};
