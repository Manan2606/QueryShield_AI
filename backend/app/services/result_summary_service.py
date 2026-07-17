import json
from dataclasses import dataclass

from app.core.config import settings

EMPTY_RESULT_SUMMARY = "No matching rows were returned for this question. Try broadening the question or checking whether the selected dataset contains matching values."


class ResultSummaryError(RuntimeError):
    pass


@dataclass(frozen=True)
class SummaryPayload:
    rows: list[dict]
    rows_json: str
    source_row_count: int


def _truncate_text(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 3] + "..."


def prepare_summary_payload(rows: list[dict]) -> SummaryPayload:
    capped_rows = rows[: settings.SUMMARY_MAX_ROWS]
    safe_rows: list[dict] = []
    max_chars = settings.SUMMARY_MAX_CHARS
    for row in capped_rows:
        candidate = {str(key): value for key, value in row.items()}
        serialized = json.dumps(safe_rows + [candidate], ensure_ascii=True, default=str)
        if len(serialized) > max_chars:
            break
        safe_rows.append(candidate)
    return SummaryPayload(rows=safe_rows, rows_json=json.dumps(safe_rows, ensure_ascii=True, default=str), source_row_count=len(rows))


def build_result_summary_prompt(
    question: str,
    generated_sql: str,
    rows: list[dict],
    columns: list[str] | None = None,
    row_count: int | None = None,
) -> str:
    payload = prepare_summary_payload(rows)
    column_text = ", ".join(columns or []) or "Not provided"
    sql_text = _truncate_text(" ".join(generated_sql.split()), 1200) if generated_sql else "Not provided"
    return f"""You are summarizing the result of a governed analytics query.

User question:
{question}

Generated SQL:
{sql_text}

Returned column names:
{column_text}

Returned row count:
{row_count if row_count is not None else payload.source_row_count}

Returned rows JSON:
{payload.rows_json}

Rules:
- Summarize only the returned rows JSON.
- Do not invent missing numbers.
- Do not assume access to the full dataset beyond these rows.
- Do not generate SQL.
- Do not request or use external data.
- Do not mention implementation details unless needed.
- Keep the answer concise and useful.
- If there is not enough data to identify a trend, say so.
- Return 1 short paragraph or up to 3 bullets.
- Do not return a markdown table.
"""


def generate_result_summary(
    question: str,
    generated_sql: str,
    rows: list[dict],
    columns: list[str] | None = None,
    row_count: int | None = None,
) -> str:
    if not rows:
        return EMPTY_RESULT_SUMMARY
    if not settings.AI_SUMMARY_ENABLED:
        raise ResultSummaryError("AI result summaries are disabled")
    if not settings.GEMINI_API_KEY:
        raise ResultSummaryError("GEMINI_API_KEY is not configured")

    try:
        from google import genai
    except ImportError as exc:
        raise ResultSummaryError("google-genai SDK is not installed") from exc

    prompt = build_result_summary_prompt(question, generated_sql, rows, columns, row_count)
    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(model=settings.GEMINI_MODEL, contents=prompt)
    except Exception as exc:
        raise ResultSummaryError("Gemini result summary generation failed") from exc

    text = getattr(response, "text", None)
    if not text or not text.strip():
        raise ResultSummaryError("Gemini returned an empty result summary")
    return text.strip()
