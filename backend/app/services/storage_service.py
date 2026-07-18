from __future__ import annotations

import os
import uuid
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import UploadFile

from app.core.config import settings


UPLOAD_CHUNK_SIZE = 1024 * 1024


class UploadStorageError(RuntimeError):
    pass


class UploadTooLargeError(ValueError):
    pass


class StoredUpload:
    def __init__(
        self,
        original_filename: str,
        storage_path: str,
        analysis_path: str | None = None,
    ):
        self.original_filename = original_filename
        self.storage_path = storage_path
        self.analysis_path = analysis_path or storage_path


class UploadStorage:
    def save_upload(self, file: UploadFile, dataset_id: int) -> StoredUpload:
        raise NotImplementedError

    def exists(self, storage_path: str) -> bool:
        raise NotImplementedError

    def local_path_for_read(self, storage_path: str) -> str:
        raise NotImplementedError

    def cleanup_local_path(self, local_path: str) -> None:
        return None


def _copy_upload_to_path(file: UploadFile, destination: str | Path) -> int:
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    total_bytes = 0
    destination_path = Path(destination)

    with destination_path.open("wb") as handle:
        while True:
            chunk = file.file.read(UPLOAD_CHUNK_SIZE)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > max_bytes:
                raise UploadTooLargeError("File is too large")
            handle.write(chunk)

    if total_bytes == 0:
        raise ValueError("Empty file")
    return total_bytes


class LocalUploadStorage(UploadStorage):
    def save_upload(self, file: UploadFile, dataset_id: int) -> StoredUpload:
        backend_root = Path(__file__).resolve().parents[2]
        upload_dir = Path(settings.UPLOAD_DIR)
        if not upload_dir.is_absolute():
            upload_dir = backend_root / upload_dir
        upload_dir.mkdir(parents=True, exist_ok=True)

        suffix = Path(file.filename or "upload.csv").suffix.lower() or ".csv"
        safe_name = f"dataset_{dataset_id}_{uuid.uuid4().hex}{suffix}"
        storage_path = upload_dir / safe_name

        try:
            _copy_upload_to_path(file, storage_path)
        except Exception:
            try:
                storage_path.unlink()
            except FileNotFoundError:
                pass
            raise

        return StoredUpload(file.filename or safe_name, str(storage_path))

    def exists(self, storage_path: str) -> bool:
        return Path(storage_path).exists()

    def local_path_for_read(self, storage_path: str) -> str:
        return storage_path


class GCSUploadStorage(UploadStorage):
    def __init__(self, bucket_name: str):
        if not bucket_name:
            raise UploadStorageError(
                "GCS_UPLOAD_BUCKET must be configured when STORAGE_BACKEND=gcs"
            )
        self.bucket_name = bucket_name

    def _client(self):
        try:
            from google.cloud import storage
        except ImportError as exc:
            raise UploadStorageError(
                "google-cloud-storage is not installed. Install backend requirements before using GCS uploads."
            ) from exc
        if settings.GOOGLE_APPLICATION_CREDENTIALS:
            os.environ.setdefault(
                "GOOGLE_APPLICATION_CREDENTIALS",
                settings.GOOGLE_APPLICATION_CREDENTIALS,
            )
        return storage.Client(project=settings.GCP_PROJECT_ID or None)

    def save_upload(self, file: UploadFile, dataset_id: int) -> StoredUpload:
        suffix = Path(file.filename or "upload.csv").suffix.lower() or ".csv"
        object_name = f"uploads/dataset_{dataset_id}/{uuid.uuid4().hex}{suffix}"
        storage_path = f"gs://{self.bucket_name}/{object_name}"

        with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            analysis_path = temp_file.name

        try:
            _copy_upload_to_path(file, analysis_path)
            bucket = self._client().bucket(self.bucket_name)
            blob = bucket.blob(object_name)
            blob.upload_from_filename(
                analysis_path, content_type=file.content_type or "text/csv"
            )
        except Exception as exc:
            self.cleanup_local_path(analysis_path)
            if isinstance(exc, (UploadStorageError, UploadTooLargeError, ValueError)):
                raise
            raise UploadStorageError(
                f"Failed to upload CSV to Cloud Storage bucket '{self.bucket_name}': {exc}"
            ) from exc

        return StoredUpload(
            file.filename or Path(object_name).name, storage_path, analysis_path
        )

    def exists(self, storage_path: str) -> bool:
        bucket_name, object_name = parse_gcs_uri(storage_path)
        try:
            bucket = self._client().bucket(bucket_name)
            return bucket.blob(object_name).exists()
        except Exception as exc:
            raise UploadStorageError(
                f"Failed to check Cloud Storage object '{storage_path}': {exc}"
            ) from exc

    def local_path_for_read(self, storage_path: str) -> str:
        bucket_name, object_name = parse_gcs_uri(storage_path)
        with NamedTemporaryFile(
            delete=False, suffix=Path(object_name).suffix or ".csv"
        ) as temp_file:
            temp_path = temp_file.name
        try:
            bucket = self._client().bucket(bucket_name)
            bucket.blob(object_name).download_to_filename(temp_path)
        except Exception as exc:
            self.cleanup_local_path(temp_path)
            raise UploadStorageError(
                f"Failed to download Cloud Storage object '{storage_path}': {exc}"
            ) from exc
        return temp_path

    def cleanup_local_path(self, local_path: str) -> None:
        try:
            os.remove(local_path)
        except FileNotFoundError:
            return None


def parse_gcs_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("gs://"):
        raise ValueError("Expected a gs:// Cloud Storage URI")
    bucket_and_object = uri.removeprefix("gs://")
    bucket, _, object_name = bucket_and_object.partition("/")
    if not bucket or not object_name:
        raise ValueError("Cloud Storage URI must include a bucket and object path")
    return bucket, object_name


def get_upload_storage() -> UploadStorage:
    if settings.use_gcs_uploads:
        return GCSUploadStorage(settings.GCS_UPLOAD_BUCKET)
    return LocalUploadStorage()
