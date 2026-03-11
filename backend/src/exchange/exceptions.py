"""Custom exceptions for OKX exchange integration."""


class OkxApiError(Exception):
    """Raised when the OKX API returns an error response."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"OKX API Error [{code}]: {message}")
