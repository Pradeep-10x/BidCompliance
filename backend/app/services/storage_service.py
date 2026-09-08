import asyncio
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings


class StorageError(Exception):
    pass


class EmptyUploadError(StorageError):
    pass


class UploadTooLargeError(StorageError):
    pass


class StoredObjectNotFoundError(StorageError):
    pass


@dataclass(frozen=True)
class StoredObject:
    key: str
    content_hash: str
    size: int


class StorageService(Protocol):
    async def store(
        self, upload: UploadFile, object_key: str, max_size: int
    ) -> StoredObject: ...

    async def store_bytes(
        self, content: bytes, object_key: str, max_size: int
    ) -> StoredObject: ...

    async def read(self, object_key: str) -> bytes: ...

    async def delete(self, object_key: str) -> None: ...


def normalize_filename(filename: str | None) -> str:
    name = (filename or "unnamed").replace("\\", "/").rsplit("/", 1)[-1]
    name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip()
    return name[:255] or "unnamed"


def generate_object_key(filename: str | None) -> str:
    suffix = Path(normalize_filename(filename)).suffix.lower()
    if suffix not in {".pdf", ".png", ".jpg", ".jpeg"}:
        suffix = ""
    return str(PurePosixPath("documents") / f"{uuid4().hex}{suffix}")


class LocalFileStorage:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, object_key: str) -> Path:
        path = (self.root / PurePosixPath(object_key)).resolve()
        if self.root != path and self.root not in path.parents:
            raise StorageError("Invalid storage object key")
        return path

    async def store(
        self, upload: UploadFile, object_key: str, max_size: int
    ) -> StoredObject:
        content = await upload.read(max_size + 1)
        return await self.store_bytes(content, object_key, max_size)

    async def store_bytes(
        self, content: bytes, object_key: str, max_size: int
    ) -> StoredObject:
        if not content:
            raise EmptyUploadError
        if len(content) > max_size:
            raise UploadTooLargeError
        path = self._safe_path(object_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_bytes(content)
        except OSError as exc:
            path.unlink(missing_ok=True)
            raise StorageError("Unable to store document locally") from exc
        return StoredObject(
            object_key,
            hashlib.sha256(content).hexdigest(),
            len(content),
        )

    async def read(self, object_key: str) -> bytes:
        path = self._safe_path(object_key)
        try:
            return path.read_bytes()
        except FileNotFoundError as exc:
            raise StoredObjectNotFoundError(object_key) from exc
        except OSError as exc:
            raise StorageError("Unable to read stored document") from exc

    async def delete(self, object_key: str) -> None:
        self._safe_path(object_key).unlink(missing_ok=True)


class S3FileStorage:
    def __init__(
        self,
        bucket: str,
        *,
        region: str,
        access_key: str | None = None,
        secret_key: str | None = None,
        endpoint_url: str | None = None,
        server_side_encryption: str | None = "AES256",
        client=None,
    ):
        if not bucket:
            raise StorageError("STORAGE_BUCKET must be configured for S3 storage")
        if bool(access_key) != bool(secret_key):
            raise StorageError(
                "Both STORAGE_ACCESS_KEY and STORAGE_SECRET_KEY must be configured"
            )
        self.bucket = bucket
        encryption = (server_side_encryption or "").strip()
        self.server_side_encryption = (
            None
            if encryption.lower() in {"", "none", "off", "disabled", "false"}
            else encryption
        )
        if client is not None:
            self.client = client
            return
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover - deployment guard
            raise StorageError("boto3 is required for S3 storage") from exc

        client_options = {
            "service_name": "s3",
            "region_name": region,
        }
        if access_key and secret_key:
            client_options.update(
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
            )
        if endpoint_url:
            client_options["endpoint_url"] = endpoint_url
        self.client = boto3.client(**client_options)

    async def store(
        self, upload: UploadFile, object_key: str, max_size: int
    ) -> StoredObject:
        content = await upload.read(max_size + 1)
        return await self.store_bytes(content, object_key, max_size)

    async def store_bytes(
        self, content: bytes, object_key: str, max_size: int
    ) -> StoredObject:
        if not content:
            raise EmptyUploadError
        if len(content) > max_size:
            raise UploadTooLargeError

        def put() -> None:
            options = {
                "Bucket": self.bucket,
                "Key": object_key,
                "Body": content,
            }
            if self.server_side_encryption:
                options["ServerSideEncryption"] = self.server_side_encryption
            self.client.put_object(
                **options,
            )

        try:
            await asyncio.to_thread(put)
        except Exception as exc:
            raise StorageError("Unable to store document in S3") from exc
        return StoredObject(
            object_key,
            hashlib.sha256(content).hexdigest(),
            len(content),
        )

    async def read(self, object_key: str) -> bytes:
        def get() -> bytes:
            response = self.client.get_object(Bucket=self.bucket, Key=object_key)
            body = response["Body"]
            try:
                return body.read()
            finally:
                body.close()

        try:
            return await asyncio.to_thread(get)
        except Exception as exc:
            response = getattr(exc, "response", {})
            code = str(response.get("Error", {}).get("Code", ""))
            if code in {"NoSuchKey", "404", "NotFound"}:
                raise StoredObjectNotFoundError(object_key) from exc
            raise StorageError("Unable to read document from S3") from exc

    async def delete(self, object_key: str) -> None:
        try:
            await asyncio.to_thread(
                self.client.delete_object,
                Bucket=self.bucket,
                Key=object_key,
            )
        except Exception as exc:
            raise StorageError("Unable to delete document from S3") from exc


def get_storage_service(local_root: str | Path | None = None) -> StorageService:
    backend = settings.STORAGE_BACKEND.lower().strip()
    if backend == "local":
        return LocalFileStorage(local_root or settings.STORAGE_LOCAL_ROOT)
    if backend == "s3":
        return S3FileStorage(
            settings.STORAGE_BUCKET,
            region=settings.STORAGE_REGION,
            access_key=settings.STORAGE_ACCESS_KEY,
            secret_key=settings.STORAGE_SECRET_KEY,
            endpoint_url=settings.STORAGE_ENDPOINT,
            server_side_encryption=settings.STORAGE_SERVER_SIDE_ENCRYPTION,
        )
    raise StorageError(f"Unsupported storage backend: {settings.STORAGE_BACKEND}")
