from typing import Any

import httpx

from app.core.config import settings
from app.schemas.ml1 import ML1Request, ML1Response


class ML1IntegrationError(Exception):
    pass


class ML1TransportError(ML1IntegrationError):
    pass


class ML1ResponseError(ML1IntegrationError):
    pass


class ML1Client:
    def __init__(self, http_client: httpx.AsyncClient | None = None):
        self._client = http_client

    async def document_intelligence(self, request: ML1Request) -> ML1Response:
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(
            base_url=settings.ML1_BASE_URL.rstrip("/"),
            timeout=httpx.Timeout(
                settings.ML1_TOTAL_TIMEOUT_SECONDS,
                connect=settings.ML1_CONNECT_TIMEOUT_SECONDS,
                read=settings.ML1_READ_TIMEOUT_SECONDS,
            ),
        )
        try:
            try:
                response = await client.post(
                    "/ml1/document-intelligence", json=request.model_dump(mode="json")
                )
                response.raise_for_status()
            except (httpx.HTTPError, httpx.TimeoutException) as exc:
                raise ML1TransportError(str(exc)) from exc
            try:
                return ML1Response.model_validate(response.json())
            except (ValueError, TypeError) as exc:
                raise ML1ResponseError("Invalid ML-1 response envelope") from exc
        finally:
            if owns_client:
                await client.aclose()
