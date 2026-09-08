from io import BytesIO

import pytest
from fastapi import UploadFile

from app.services.storage_service import (
    EmptyUploadError,
    LocalFileStorage,
    S3FileStorage,
    StoredObjectNotFoundError,
    UploadTooLargeError,
)


class MissingObjectError(Exception):
    response = {"Error": {"Code": "NoSuchKey"}}


class MemoryS3Client:
    def __init__(self):
        self.objects: dict[tuple[str, str], bytes] = {}
        self.put_options = {}

    def put_object(self, **options):
        self.put_options = options
        Bucket = options["Bucket"]
        Key = options["Key"]
        Body = options["Body"]
        self.objects[(Bucket, Key)] = Body

    def get_object(self, *, Bucket, Key):
        try:
            content = self.objects[(Bucket, Key)]
        except KeyError as exc:
            raise MissingObjectError from exc
        return {"Body": BytesIO(content)}

    def delete_object(self, *, Bucket, Key):
        self.objects.pop((Bucket, Key), None)


@pytest.mark.asyncio
async def test_local_storage_supports_store_read_and_delete(tmp_path):
    storage = LocalFileStorage(tmp_path)
    upload = UploadFile(filename="certificate.pdf", file=BytesIO(b"document"))

    stored = await storage.store(upload, "documents/certificate.pdf", 100)

    assert stored.size == 8
    assert await storage.read(stored.key) == b"document"
    await storage.delete(stored.key)
    with pytest.raises(StoredObjectNotFoundError):
        await storage.read(stored.key)


@pytest.mark.asyncio
async def test_storage_rejects_empty_and_oversized_objects(tmp_path):
    storage = LocalFileStorage(tmp_path)

    with pytest.raises(EmptyUploadError):
        await storage.store_bytes(b"", "documents/empty.pdf", 100)
    with pytest.raises(UploadTooLargeError):
        await storage.store_bytes(b"too large", "documents/large.pdf", 4)


@pytest.mark.asyncio
async def test_s3_storage_round_trip_and_encryption():
    client = MemoryS3Client()
    storage = S3FileStorage(
        "pramaan-test",
        region="ap-south-1",
        client=client,
    )

    stored = await storage.store_bytes(b"document", "documents/test.pdf", 100)

    assert await storage.read(stored.key) == b"document"
    assert client.objects[("pramaan-test", stored.key)] == b"document"
    assert client.put_options["ServerSideEncryption"] == "AES256"
    await storage.delete(stored.key)
    with pytest.raises(StoredObjectNotFoundError):
        await storage.read(stored.key)


@pytest.mark.asyncio
async def test_r2_storage_omits_unsupported_sse_header():
    client = MemoryS3Client()
    storage = S3FileStorage(
        "pramaan-test",
        region="auto",
        endpoint_url="https://account-id.r2.cloudflarestorage.com",
        server_side_encryption="none",
        client=client,
    )

    await storage.store_bytes(b"document", "documents/test.pdf", 100)

    assert "ServerSideEncryption" not in client.put_options
