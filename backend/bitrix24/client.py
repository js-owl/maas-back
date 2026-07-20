"""Bitrix24 REST API HTTP client."""

import logging
from typing import Any

import httpx

from backend.bitrix24.exceptions import BitrixAPIError

logger = logging.getLogger(__name__)


def _strip_none(obj: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of the dict with keys whose value is None removed."""
    return {k: v for k, v in obj.items() if v is not None}


class BitrixClient:
    """
    Low-level async client for Bitrix24 REST API.

    Webhook: base_url = https://{portal}/rest/{user_id}/{webhook_code}/
    OAuth: base_url = https://{portal}/rest/, access_token passed to constructor;
    client adds 'auth': token to every request body.
    """

    def __init__(
        self,
        base_url: str,
        *,
        access_token: str | None = None,
        timeout: float = 30.0,
        verify_tls: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.access_token = access_token
        self.timeout = timeout
        self.verify_tls = verify_tls

    async def call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        """
        Invoke a Bitrix24 REST method.

        Sends POST to {base_url}{method} with JSON body. Excludes None values
        from params. On success returns the 'result' value; on error raises
        BitrixAPIError(code, description).
        """
        data = await self.call_full(method, params)
        return data.get("result")

    async def call_full(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Like call(), but returns the full Bitrix JSON body (result, next, total, …)."""
        params = params or {}
        payload = _strip_none(params)
        if self.access_token:
            payload["auth"] = self.access_token

        url = f"{self.base_url}{method}"
        if logger.isEnabledFor(logging.DEBUG):
            log_payload = {k: ("***" if k == "auth" else v) for k, v in payload.items()}
            logger.debug("Bitrix24 request %s %s", method, log_payload)

        async with httpx.AsyncClient(timeout=self.timeout, verify=self.verify_tls) as client:
            response = await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )

        try:
            data = response.json()
        except Exception as e:
            logger.debug("Bitrix24 response non-JSON: %s", response.text[:500])
            raise BitrixAPIError(
                "INVALID_RESPONSE",
                str(e),
                status_code=response.status_code,
                headers=dict(response.headers),
            ) from e

        if "error" in data:
            code = data.get("error", "UNKNOWN")
            description = data.get("error_description", "")
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Bitrix24 error %s: %s", code, description)
            raise BitrixAPIError(
                code,
                description,
                status_code=response.status_code,
                headers=dict(response.headers),
            )

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Bitrix24 response %s result keys: %s", method, type(data.get("result")))

        return data
