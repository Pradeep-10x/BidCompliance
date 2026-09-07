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


@dataclass(frozen=True)
class StoredObject:
    key: str
    content_hash: str
    size: int


class StorageService(Protocol):
    async def store(
        self, upload: UploadFile, object_key: str, max_size: int
    ) -> StoredObject: ...

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
        path = self._safe_path(object_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        size = 0
        try:
            with path.open("wb") as destination:
                while chunk := await upload.read(1024 * 1024):
                    size += len(chunk)
                    if size > max_size:
                        raise UploadTooLargeError
                    digest.update(chunk)
                    destination.write(chunk)
        except Exception:
            path.unlink(missing_ok=True)
            raise
        if size == 0:
            path.unlink(missing_ok=True)
            raise EmptyUploadError
        return StoredObject(object_key, digest.hexdigest(), size)

    async def delete(self, object_key: str) -> None:
        self._safe_path(object_key).unlink(missing_ok=True)


def get_storage_service() -> StorageService:
    if settings.STORAGE_BACKEND.lower() != "local":
        raise RuntimeError("Only local document storage is configured")
    return LocalFileStorage(settings.STORAGE_LOCAL_ROOT)