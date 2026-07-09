import re
from dataclasses import dataclass
from typing import Protocol

from app.core.config import settings


class GeminiGenerationError(RuntimeError):
    pass


class DatasetColumnLike(Protocol):
    name: str
    data_type: str


FORBIDDEN_SQL_KEYWORDS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "MERGE",
    "DROP",
    "ALTER",
    "CREATE",
    "TRUNCATE",
    "GRANT",
    "REVOKE",
)


@dataclass(frozen=True)
class SqlValidationResult:
    sql: str


def build_sql_generation_prompt(table_id: str, columns: list[DatasetColumnLike], question: str) -> str:
    column_lines = "\n".join(f"* {column.name}: {column.data_type}" for column in columns)
    return f"""You generate BigQuery Standard SQL for QueryShield AI.

Rules:
* Use BigQuery Standard SQL.
* Query only the supplied table.
* Use the exact fully qualified table ID.
* Use only supplied columns.
* Return one read-only SQL query.
* Return only SQL.
* Do not include Markdown fences.
* Do not include explanations.
* Do not use INSERT, UPDATE, DELETE, MERGE, DROP, ALTER, CREATE, TRUNCATE, GRANT, or REVOKE.
* Prefer explicit column names.
* Use backticks around the fully qualified BigQuery table ID.
* Use aggregation correctly.
* Add a reasonable LIMIT for raw row-listing questions when appropriate.
* Do not invent columns.
* Do not query metadata tables.
* Do not query another dataset or table.

Table:
`{table_id}`

Columns:
{column_lines}

User question:
{question}
"""


def clean_generated_sql(raw_output: str) -> str:
    output = raw_output.strip()
    if not output:
        raise GeminiGenerationError("Gemini returned empty SQL")

    fenced_match = re.search(r"```(?:sql)?\s*(.*?)```", output, flags=re.IGNORECASE | re.DOTALL)
    if fenced_match:
        output = fenced_match.group(1).strip()
    else:
        statement_match = re.search(r"\b(SELECT|WITH)\b", output, flags=re.IGNORECASE)
        if statement_match:
            output = output[statement_match.start() :].strip()

    if not output:
        raise GeminiGenerationError("Gemini returned empty SQL")
    return output


def validate_generated_sql(sql: str, table_id: str) -> SqlValidationResult:
    normalized = sql.strip()
    if not normalized:
        raise GeminiGenerationError("Generated SQL is empty")

    if not re.match(r"^(SELECT|WITH)\b", normalized, flags=re.IGNORECASE):
        raise GeminiGenerationError("Generated SQL must start with SELECT or WITH")

    if table_id not in normalized:
        raise GeminiGenerationError("Generated SQL does not reference the selected BigQuery table")

    for keyword in FORBIDDEN_SQL_KEYWORDS:
        if re.search(rf"\b{keyword}\b", normalized, flags=re.IGNORECASE):
            raise GeminiGenerationError(f"Generated SQL contains forbidden keyword: {keyword}")

    return SqlValidationResult(sql=normalized)


def generate_bigquery_sql(table_id: str, columns: list[DatasetColumnLike], question: str) -> str:
    if not settings.GEMINI_API_KEY:
        raise GeminiGenerationError("GEMINI_API_KEY is not configured")

    try:
        from google import genai
    except ImportError as exc:
        raise GeminiGenerationError("google-genai SDK is not installed") from exc

    prompt = build_sql_generation_prompt(table_id, columns, question)
    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(model=settings.GEMINI_MODEL, contents=prompt)
    except Exception as exc:
        raise GeminiGenerationError("Gemini SQL generation failed") from exc

    text = getattr(response, "text", None)
    if not text:
        raise GeminiGenerationError("Gemini returned empty SQL")
    return text
