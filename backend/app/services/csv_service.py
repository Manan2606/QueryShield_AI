import csv
import os
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.models.dataset_column import DatasetColumn


ALLOWED_CONTENT_TYPES = {"text/csv", "application/csv", "application/vnd.ms-excel"}


def validate_csv_file(file: UploadFile) -> None:
    if file.filename is None or file.filename == "":
        raise ValueError("No file selected")

    if not file.filename.lower().endswith(".csv"):
        raise ValueError("Only .csv files are supported")

    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError("Unsupported file content type")

    if file.size is not None and file.size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise ValueError("File is too large")


def save_upload_file(file: UploadFile, dataset_id: int) -> tuple[str, str]:
    validate_csv_file(file)

    backend_root = Path(__file__).resolve().parents[2]
    upload_dir = Path(settings.UPLOAD_DIR)
    if not upload_dir.is_absolute():
        upload_dir = backend_root / upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename).suffix.lower() or ".csv"
    safe_name = f"dataset_{dataset_id}_{uuid.uuid4().hex}{suffix}"
    storage_path = upload_dir / safe_name

    contents = file.file.read()
    if not contents:
        raise ValueError("Empty file")

    with storage_path.open("wb") as handle:
        handle.write(contents)

    return file.filename, str(storage_path)


def infer_column_type(values: list[str]) -> str:
    non_empty = [value.strip() for value in values if value is not None and str(value).strip() != ""]
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
    with open(file_path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        rows = list(reader)

    if not rows:
        raise ValueError("CSV file is empty")

    headers = [header.strip() for header in rows[0]]
    data_rows = rows[1:]
    row_count = len(data_rows)
    column_count = len(headers)

    columns: list[dict] = []
    for index, header in enumerate(headers, start=1):
        values = [row[index - 1] if index - 1 < len(row) else "" for row in data_rows]
        columns.append(
            {
                "name": header or f"column_{index}",
                "data_type": infer_column_type(values),
                "nullable": True,
                "ordinal_position": index,
                "sample_values": values[:5],
            }
        )

    return {
        "row_count": row_count,
        "column_count": column_count,
        "columns": columns,
    }


def preview_csv(file_path: str, limit: int) -> dict:
    with open(file_path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)[:limit]

    columns = list(rows[0].keys()) if rows else []
    return {"columns": columns, "rows": rows}
