import re
from dataclasses import dataclass, field
from datetime import datetime

from fastapi import status
from sqlalchemy.orm import Session

from app.services.audit_service import create_audit_log
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.query_request import QueryRequest

try:
    import sqlglot
    from sqlglot import exp
except (
    ImportError
) as exc:  # pragma: no cover - exercised only when dependencies are missing.
    sqlglot = None
    exp = None
    SQLGLOT_IMPORT_ERROR = exc
else:
    SQLGLOT_IMPORT_ERROR = None


READ_ONLY_ERROR = "Only read-only SELECT queries are allowed"
SELECT_STAR_WARNING = "SELECT * may scan unnecessary columns"
MISSING_LIMIT_WARNING = "Query may return many rows because no LIMIT is present"

FORBIDDEN_PATTERN_MESSAGES: tuple[tuple[str, str], ...] = (
    (r"\bINSERT\b", READ_ONLY_ERROR),
    (r"\bUPDATE\b", READ_ONLY_ERROR),
    (r"\bDELETE\b", READ_ONLY_ERROR),
    (r"\bMERGE\b", READ_ONLY_ERROR),
    (r"\bCREATE(?:\s+OR\s+REPLACE)?\b", READ_ONLY_ERROR),
    (r"\bDROP\b", READ_ONLY_ERROR),
    (r"\bALTER\b", READ_ONLY_ERROR),
    (r"\bTRUNCATE\b", READ_ONLY_ERROR),
    (r"\bGRANT\b", READ_ONLY_ERROR),
    (r"\bREVOKE\b", READ_ONLY_ERROR),
    (r"\bCALL\b", READ_ONLY_ERROR),
    (r"\bEXECUTE\s+IMMEDIATE\b", "BigQuery scripting and dynamic SQL are not allowed"),
    (r"\bEXPORT\s+DATA\b", "BigQuery export statements are not allowed"),
    (r"\bLOAD\s+DATA\b", "BigQuery load statements are not allowed"),
    (r"\bASSERT\b", "BigQuery scripting statements are not allowed"),
    (r"\bBEGIN\b", "BigQuery scripting blocks are not allowed"),
    (r"\bCOMMIT\b", "BigQuery transaction statements are not allowed"),
    (r"\bROLLBACK\b", "BigQuery transaction statements are not allowed"),
    (r"\bDECLARE\b", "BigQuery scripting variables are not allowed"),
    (r"\bSET\b", "BigQuery scripting variables are not allowed"),
    (r"\bEXTERNAL_QUERY\s*\(", "External query functions are not allowed"),
    (
        r"\bML\.PREDICT\s*\(",
        "BigQuery ML prediction is not supported in validation step 8",
    ),
)


@dataclass(frozen=True)
class ValidationResult:
    is_safe: bool
    statement_type: str | None = None
    referenced_tables: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    normalized_sql: str | None = None


class SQLValidationRequestError(RuntimeError):
    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class SQLValidatorInternalError(RuntimeError):
    pass


def _add_audit_log(
    db: Session,
    user_id: int,
    action: str,
    query_request_id: int | None = None,
    details: dict | None = None,
) -> None:
    create_audit_log(
        db,
        user_id,
        action,
        "query_request",
        str(query_request_id) if query_request_id is not None else None,
        details,
    )


def _strip_sql_comments(sql: str) -> str:
    result: list[str] = []
    index = 0
    in_single = False
    in_double = False
    in_backtick = False
    while index < len(sql):
        char = sql[index]
        nxt = sql[index + 1] if index + 1 < len(sql) else ""
        if char == "'" and not in_double and not in_backtick:
            in_single = not in_single
            result.append(char)
            index += 1
            continue
        if char == '"' and not in_single and not in_backtick:
            in_double = not in_double
            result.append(char)
            index += 1
            continue
        if char == "`" and not in_single and not in_double:
            in_backtick = not in_backtick
            result.append(char)
            index += 1
            continue
        if (
            not in_single
            and not in_double
            and not in_backtick
            and char == "-"
            and nxt == "-"
        ):
            index += 2
            while index < len(sql) and sql[index] not in "\r\n":
                index += 1
            result.append(" ")
            continue
        if (
            not in_single
            and not in_double
            and not in_backtick
            and char == "/"
            and nxt == "*"
        ):
            index += 2
            while index + 1 < len(sql) and not (
                sql[index] == "*" and sql[index + 1] == "/"
            ):
                index += 1
            index += 2 if index + 1 < len(sql) else 0
            result.append(" ")
            continue
        result.append(char)
        index += 1
    return "".join(result)


def _normalize_identifier(value: str) -> str:
    return value.strip().strip("`").strip('"').lower()


def _normalize_table_id(value: str) -> str:
    cleaned = value.strip().rstrip(";")
    cleaned = re.sub(r"\s+AS\s+.+$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+.+$", "", cleaned)
    cleaned = cleaned.replace("`", "").replace('"', "")
    return cleaned.lower()


def _table_parts(table) -> list[str]:
    parts = []
    for part in getattr(table, "parts", []) or []:
        name = getattr(part, "name", None) or str(part)
        if name:
            parts.append(name.strip('`"'))
    if parts:
        return parts
    rendered = table.sql(dialect="bigquery")
    rendered = re.sub(r"\s+AS\s+.+$", "", rendered, flags=re.IGNORECASE)
    rendered = re.sub(r"\s+.+$", "", rendered)
    return [piece.strip('`"') for piece in rendered.split(".") if piece]


def _table_name(table) -> str:
    return ".".join(_table_parts(table))


def _cte_names(expression) -> set[str]:
    names: set[str] = set()
    for cte in expression.find_all(exp.CTE):
        alias = cte.alias
        if alias:
            names.add(_normalize_identifier(alias))
    return names


def _referenced_physical_tables(expression) -> tuple[list[str], set[str]]:
    ctes = _cte_names(expression)
    referenced: list[str] = []
    physical_aliases: set[str] = set()
    for table in expression.find_all(exp.Table):
        name = _table_name(table)
        if not name:
            continue
        normalized_name = _normalize_table_id(name)
        if len(_table_parts(table)) == 1 and normalized_name in ctes:
            continue
        if normalized_name not in {_normalize_table_id(item) for item in referenced}:
            referenced.append(name)
        alias = table.alias
        if alias:
            physical_aliases.add(_normalize_identifier(alias))
        physical_aliases.add(_normalize_identifier(_table_parts(table)[-1]))
    return referenced, physical_aliases


def _statement_type(expression) -> str:
    if isinstance(expression, exp.Select):
        return "SELECT"
    return (
        expression.key.upper()
        if getattr(expression, "key", None)
        else expression.__class__.__name__.upper()
    )


def _has_aggregation(expression) -> bool:
    aggregate_cls = getattr(exp, "AggFunc", None)
    if aggregate_cls is None:
        return False
    return any(True for _ in expression.find_all(aggregate_cls))


def _has_table_function(expression) -> bool:
    table_function_cls = getattr(exp, "TableFunction", None)
    if table_function_cls is None:
        return False
    return any(True for _ in expression.find_all(table_function_cls))


def _function_name(function) -> str:
    name = getattr(function, "name", None)
    if name:
        return str(name).upper()
    sql = function.sql(dialect="bigquery").split("(", 1)[0]
    return sql.upper()


def _validate_columns(
    expression, allowed_columns: list[str] | None, physical_aliases: set[str]
) -> list[str]:
    if not allowed_columns:
        return []
    allowed = {_normalize_identifier(column) for column in allowed_columns}
    warnings: list[str] = []
    uncertain: set[str] = set()
    for column in expression.find_all(exp.Column):
        name = _normalize_identifier(column.name)
        qualifier = _normalize_identifier(column.table or "")
        if not name or name == "*" or name in allowed:
            continue
        if qualifier and qualifier in physical_aliases:
            warnings.append(
                f"Column '{column.sql(dialect='bigquery')}' is not in the stored dataset schema"
            )
        elif not qualifier:
            uncertain.add(name)
    if uncertain:
        warnings.append(
            "Column validation is conservative; review possible aliases or unknown columns: "
            + ", ".join(sorted(uncertain))
        )
    return warnings


def validate_generated_sql(
    sql: str,
    allowed_table_id: str,
    allowed_columns: list[str] | None = None,
) -> ValidationResult:
    if sqlglot is None or exp is None:
        raise SQLValidatorInternalError(
            "sqlglot is not installed"
        ) from SQLGLOT_IMPORT_ERROR

    normalized_sql = sql.strip()
    if not normalized_sql:
        return ValidationResult(is_safe=False, errors=["Generated SQL is empty"])

    errors: list[str] = []
    warnings: list[str] = []
    statement_type: str | None = None
    referenced_tables: list[str] = []

    try:
        statements = sqlglot.parse(normalized_sql, read="bigquery")
    except Exception:
        return ValidationResult(
            is_safe=False,
            errors=["SQL could not be parsed"],
            normalized_sql=normalized_sql,
        )

    if len(statements) != 1:
        return ValidationResult(
            is_safe=False,
            errors=["Exactly one SQL statement is allowed"],
            normalized_sql=normalized_sql,
        )

    expression = statements[0]
    statement_type = _statement_type(expression)
    comment_stripped_sql = _strip_sql_comments(normalized_sql)

    for pattern, message in FORBIDDEN_PATTERN_MESSAGES:
        if re.search(pattern, comment_stripped_sql, flags=re.IGNORECASE):
            if message not in errors:
                errors.append(message)

    if not isinstance(expression, exp.Select):
        if READ_ONLY_ERROR not in errors:
            errors.append(READ_ONLY_ERROR)

    if re.search(r"\bCROSS\s+JOIN\b", comment_stripped_sql, flags=re.IGNORECASE):
        errors.append("Explicit CROSS JOIN is not allowed")

    referenced_tables, physical_aliases = _referenced_physical_tables(expression)
    allowed_normalized = _normalize_table_id(allowed_table_id)
    referenced_normalized = [_normalize_table_id(table) for table in referenced_tables]

    if not referenced_tables:
        errors.append("SQL must reference the selected BigQuery table")

    for table, normalized_table in zip(
        referenced_tables, referenced_normalized, strict=False
    ):
        if "information_schema" in normalized_table:
            errors.append("INFORMATION_SCHEMA access is not allowed")
        if "*" in normalized_table:
            errors.append("Wildcard table access is not allowed")
        if normalized_table != allowed_normalized:
            errors.append(f"Query references unauthorized table: {table}")

    if referenced_tables and allowed_normalized not in referenced_normalized:
        errors.append("SQL must reference the selected BigQuery table")

    if _has_table_function(expression):
        errors.append("Table functions are not allowed in validation step 8")

    for function in expression.find_all(exp.Func):
        function_name = _function_name(function)
        if function_name in {"EXTERNAL_QUERY", "EXECUTE_IMMEDIATE"}:
            errors.append(
                f"Dangerous BigQuery function is not allowed: {function_name}"
            )
        if function_name == "ML.PREDICT" or function_name.endswith(".ML.PREDICT"):
            errors.append(
                "BigQuery ML prediction is not supported in validation step 8"
            )

    if any(True for _ in expression.find_all(exp.Star)):
        warnings.append(SELECT_STAR_WARNING)

    has_limit = any(
        select.args.get("limit") is not None
        for select in expression.find_all(exp.Select)
    )
    has_group = any(
        select.args.get("group") is not None
        for select in expression.find_all(exp.Select)
    )
    if not has_limit and not has_group and not _has_aggregation(expression):
        warnings.append(MISSING_LIMIT_WARNING)

    warnings.extend(_validate_columns(expression, allowed_columns, physical_aliases))

    deduped_errors = list(dict.fromkeys(errors))
    deduped_warnings = list(dict.fromkeys(warnings))
    return ValidationResult(
        is_safe=not deduped_errors,
        statement_type=statement_type,
        referenced_tables=referenced_tables,
        errors=deduped_errors,
        warnings=deduped_warnings,
        normalized_sql=expression.sql(dialect="bigquery")
        if not deduped_errors
        else normalized_sql,
    )


def _to_validation_response(query_request: QueryRequest) -> dict:
    return {
        "query_request_id": query_request.id,
        "dataset_id": query_request.dataset_id,
        "validation_status": query_request.validation_status,
        "is_safe": bool(query_request.is_safe),
        "statement_type": query_request.statement_type,
        "referenced_tables": query_request.referenced_tables or [],
        "errors": query_request.validation_errors or [],
        "warnings": query_request.validation_warnings or [],
        "validated_at": query_request.validated_at,
        "generated_sql": query_request.generated_sql or "",
        "normalized_sql": None,
    }


def validate_query_request(
    db: Session, current_user_id: int, query_request_id: int
) -> dict:
    query_request = (
        db.query(QueryRequest)
        .filter(
            QueryRequest.id == query_request_id, QueryRequest.user_id == current_user_id
        )
        .first()
    )
    if query_request is None:
        raise SQLValidationRequestError(
            "Query request not found", status.HTTP_404_NOT_FOUND
        )
    if query_request.generation_status != "generated":
        raise SQLValidationRequestError(
            "Query request must have generated SQL before validation"
        )
    if not query_request.generated_sql:
        raise SQLValidationRequestError("Query request does not have generated SQL")

    dataset = (
        db.query(Dataset)
        .filter(
            Dataset.id == query_request.dataset_id, Dataset.owner_id == current_user_id
        )
        .first()
    )
    if dataset is None:
        raise SQLValidationRequestError("Dataset not found", status.HTTP_404_NOT_FOUND)
    if not dataset.bigquery_table_id:
        raise SQLValidationRequestError("Dataset does not have a BigQuery table ID")

    columns = (
        db.query(DatasetColumn)
        .filter(DatasetColumn.dataset_id == dataset.id)
        .order_by(DatasetColumn.ordinal_position)
        .all()
    )
    allowed_columns = [column.name for column in columns]

    query_request.validation_status = "validating"
    _add_audit_log(
        db,
        current_user_id,
        "query.validation_started",
        query_request.id,
        {"dataset_id": dataset.id},
    )
    db.commit()
    db.refresh(query_request)

    try:
        result = validate_generated_sql(
            query_request.generated_sql, dataset.bigquery_table_id, allowed_columns
        )
        query_request.validation_status = "passed" if result.is_safe else "failed"
        query_request.is_safe = result.is_safe
        query_request.statement_type = result.statement_type
        query_request.validation_errors = result.errors
        query_request.validation_warnings = result.warnings
        query_request.referenced_tables = result.referenced_tables
        query_request.validated_at = datetime.utcnow()
        _add_audit_log(
            db,
            current_user_id,
            "query.validation_passed" if result.is_safe else "query.validation_failed",
            query_request.id,
            {
                "dataset_id": dataset.id,
                "errors": result.errors,
                "warnings": result.warnings,
            },
        )
        db.commit()
        db.refresh(query_request)
        response = _to_validation_response(query_request)
        response["normalized_sql"] = result.normalized_sql
        return response
    except SQLValidatorInternalError:
        query_request.validation_status = "error"
        query_request.is_safe = False
        query_request.validation_errors = ["SQL validator is not available"]
        query_request.validation_warnings = []
        query_request.referenced_tables = []
        query_request.validated_at = datetime.utcnow()
        _add_audit_log(
            db,
            current_user_id,
            "query.validation_error",
            query_request.id,
            {"dataset_id": dataset.id},
        )
        db.commit()
        raise
    except Exception as exc:
        query_request.validation_status = "error"
        query_request.is_safe = False
        query_request.validation_errors = ["SQL validator failed unexpectedly"]
        query_request.validation_warnings = []
        query_request.referenced_tables = []
        query_request.validated_at = datetime.utcnow()
        _add_audit_log(
            db,
            current_user_id,
            "query.validation_error",
            query_request.id,
            {"dataset_id": dataset.id, "error": str(exc)},
        )
        db.commit()
        raise SQLValidatorInternalError("SQL validator failed unexpectedly") from exc


def get_query_validation(
    db: Session, current_user_id: int, query_request_id: int
) -> dict:
    query_request = (
        db.query(QueryRequest)
        .filter(
            QueryRequest.id == query_request_id, QueryRequest.user_id == current_user_id
        )
        .first()
    )
    if query_request is None:
        raise SQLValidationRequestError(
            "Query request not found", status.HTTP_404_NOT_FOUND
        )
    if query_request.validation_status == "not_validated":
        raise SQLValidationRequestError("Query request has not been validated")
    return _to_validation_response(query_request)
