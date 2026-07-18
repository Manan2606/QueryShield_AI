import csv
import re
from collections.abc import Iterable

from fastapi import UploadFile

from app.core.config import settings
from app.services.storage_service import UploadTooLargeError, get_upload_storage


ALLOWED_CONTENT_TYPES = {"text/csv", "application/csv", "application/vnd.ms-excel"}
BIGQUERY_COLUMN_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,299}$")


def validate_csv_file(file: UploadFile) -> None:
    if file.filename is None or file.filename == "":
        raise ValueError("No file selected")

    if not file.filename.lower().endswith(".csv"):
        raise ValueError("Only .csv files are supported")

    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError("Unsupported file content type")

    if file.size is not None and file.size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise UploadTooLargeError("File is too large")


def save_upload_file(file: UploadFile, dataset_id: int) -> tuple[str, str, str]:
    validate_csv_file(file)
    stored_upload = get_upload_storage().save_upload(file, dataset_id)
    return (
        stored_upload.original_filename,
        stored_upload.storage_path,
        stored_upload.analysis_path,
    )


def infer_column_type(values: list[str]) -> str:
    non_empty = [
        value.strip()
        for value in values
        if value is not None and str(value).strip() != ""
    ]
    if not non_empty:
        return "STRING"

    bool_values = {"true", "false", "yes", "no", "y", "n", "0", "1"}
    if all(value.lower() in bool_values for value in non_empty):
        return "BOOLEAN"

    try:
        int(values[0])
    except (TypeError, ValueError):
        int_value = False
    else:
        int_value = all(str(value).strip().lstrip("+").isdigit() for value in non_empty)

    if int_value:
        return "INTEGER"

    try:
        float(values[0])
    except (TypeError, ValueError):
        float_value = False
    else:
        float_value = all(_is_float(value) for value in non_empty)

    if float_value:
        return "FLOAT"

    if all(_is_date(value) for value in non_empty):
        return "DATE"

    if all(_is_datetime(value) for value in non_empty):
        return "DATETIME"

    return "STRING"


def _initial_type_state(column_count: int) -> list[dict[str, bool | int]]:
    return [
        {
            "non_empty": 0,
            "boolean": True,
            "integer": True,
            "float": True,
            "date": True,
            "datetime": True,
        }
        for _ in range(column_count)
    ]


def _update_type_state(state: dict[str, bool | int], value: str) -> None:
    stripped = str(value).strip()
    if not stripped:
        return

    state["non_empty"] = int(state["non_empty"]) + 1
    state["boolean"] = bool(state["boolean"]) and stripped.lower() in {
        "true",
        "false",
        "yes",
        "no",
        "y",
        "n",
        "0",
        "1",
    }
    state["integer"] = bool(state["integer"]) and stripped.lstrip("+").isdigit()
    state["float"] = bool(state["float"]) and _is_float(stripped)
    state["date"] = bool(state["date"]) and _is_date(stripped)
    state["datetime"] = bool(state["datetime"]) and _is_datetime(stripped)


def _type_from_state(state: dict[str, bool | int]) -> str:
    if int(state["non_empty"]) == 0:
        return "STRING"
    if state["boolean"]:
        return "BOOLEAN"
    if state["integer"]:
        return "INTEGER"
    if state["float"]:
        return "FLOAT"
    if state["date"]:
        return "DATE"
    if state["datetime"]:
        return "DATETIME"
    return "STRING"


def _validate_headers(raw_headers: list[str]) -> list[str]:
    headers = [header.strip() for header in raw_headers]
    if not headers:
        raise ValueError("CSV must include at least one header column")
    if len(headers) > settings.MAX_CSV_COLUMNS:
        raise ValueError(
            f"CSV has too many columns; maximum is {settings.MAX_CSV_COLUMNS}"
        )

    seen: set[str] = set()
    for index, header in enumerate(headers, start=1):
        if not header:
            raise ValueError(f"CSV header at position {index} is blank")
        if not BIGQUERY_COLUMN_NAME_PATTERN.match(header):
            raise ValueError(f"Invalid BigQuery column name: {header}")
        normalized = header.lower()
        if normalized in seen:
            raise ValueError(f"Duplicate CSV header: {header}")
        seen.add(normalized)
    return headers


def _validate_row_width(row: list[str], expected_columns: int, row_number: int) -> None:
    if len(row) != expected_columns:
        raise ValueError(
            f"CSV row {row_number} has {len(row)} columns; expected {expected_columns}"
        )


def _append_samples(
    samples: list[list[str]], row: list[str], column_count: int
) -> None:
    for index in range(column_count):
        if len(samples[index]) < 5:
            samples[index].append(row[index])


def _infer_types_from_rows(
    rows: Iterable[list[str]], column_count: int
) -> tuple[int, list[str], list[list[str]]]:
    samples: list[list[str]] = [[] for _ in range(column_count)]
    type_states = _initial_type_state(column_count)
    row_count = 0

    for row_number, row in enumerate(rows, start=2):
        _validate_row_width(row, column_count, row_number)
        row_count += 1
        _append_samples(samples, row, column_count)
        for index in range(column_count):
            _update_type_state(type_states[index], row[index])

    inferred_types = [_type_from_state(state) for state in type_states]
    return row_count, inferred_types, samples


def _is_float(value: str) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def _is_date(value: str) -> bool:
    from datetime import datetime

    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            datetime.strptime(value, fmt)
            return True
        except ValueError:
            continue
    return False


def _is_datetime(value: str) -> bool:
    from datetime import datetime

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            datetime.strptime(value, fmt)
            return True
        except ValueError:
            continue
    return False


def analyze_csv(file_path: str) -> dict:
    try:
        with open(file_path, newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle)
            try:
                headers = _validate_headers(next(reader))
            except StopIteration as exc:
                raise ValueError("CSV file is empty") from exc

            column_count = len(headers)
            row_count, inferred_types, samples = _infer_types_from_rows(
                reader, column_count
            )
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must be valid UTF-8") from exc
    except csv.Error as exc:
        raise ValueError(f"CSV is malformed: {exc}") from exc

    columns = [
        {
            "name": header,
            "data_type": inferred_types[index - 1],
            "nullable": True,
            "ordinal_position": index,
            "sample_values": samples[index - 1],
        }
        for index, header in enumerate(headers, start=1)
    ]

    return {
        "row_count": row_count,
        "column_count": column_count,
        "columns": columns,
    }


def preview_csv(file_path: str, limit: int) -> dict:
    try:
        with open(file_path, newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle)
            try:
                columns = _validate_headers(next(reader))
            except StopIteration as exc:
                raise ValueError("CSV file is empty") from exc

            rows = []
            for row_number, row in enumerate(reader, start=2):
                if len(rows) >= limit:
                    break
                _validate_row_width(row, len(columns), row_number)
                rows.append(dict(zip(columns, row, strict=True)))
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must be valid UTF-8") from exc
    except csv.Error as exc:
        raise ValueError(f"CSV is malformed: {exc}") from exc

    return {"columns": columns, "rows": rows}
