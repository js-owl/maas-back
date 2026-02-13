"""Bitrix24 API exceptions."""


class BitrixAPIError(Exception):
    """Raised when Bitrix24 REST API returns an error response."""

    def __init__(
        self,
        code: str,
        description: str,
        *,
        status_code: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.code = code
        self.description = description
        self.status_code = status_code
        self.headers = headers or {}
        super().__init__(f"{code}: {description}")
