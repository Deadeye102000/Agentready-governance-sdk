"""HTTP transport layer and error mapping for AgentReady Governance SDK."""

from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    RetryCallState,
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
)
from tenacity.wait import wait_base, wait_exponential_jitter

from agentready_governance_sdk._constants import DEFAULT_MAX_RETRIES
from agentready_governance_sdk.exceptions import (
    AgentReadyAPIError,
    ApprovalRequiredError,
    AuthenticationError,
    ConflictError,
    InsufficientScopeError,
    InternalServerError,
    NotFoundError,
    PayloadTooLargeError,
    PermissionDeniedError,
    RateLimitError,
    ValidationError,
)

# Error code to exception mapping dictionary
_ERROR_MAP: dict[str, type[AgentReadyAPIError]] = {
    "VALIDATION_ERROR": ValidationError,
    "UNAUTHENTICATED": AuthenticationError,
    "PERMISSION_DENIED": PermissionDeniedError,
    "INSUFFICIENT_SCOPE": InsufficientScopeError,
    "NOT_FOUND": NotFoundError,
    "CONFLICT": ConflictError,
    "PAYLOAD_TOO_LARGE": PayloadTooLargeError,
    "RATE_LIMIT_EXCEEDED": RateLimitError,
    "APPROVAL_REQUIRED": ApprovalRequiredError,
    "INTERNAL_SERVER_ERROR": InternalServerError,
}


def _raise_for_status(response: httpx.Response) -> None:
    """Parse AgentReady API error envelope and raise corresponding SDK exception."""
    if response.is_success:
        return

    status_code = response.status_code
    code = "UNKNOWN_ERROR"
    message = response.reason_phrase or f"HTTP {status_code} Error"
    details: dict[str, Any] = {}

    try:
        data = response.json()
        if (
            isinstance(data, dict)
            and "error" in data
            and isinstance(data["error"], dict)
        ):
            err_obj = data["error"]
            code = err_obj.get("code", code)
            message = err_obj.get("message", message)
            details = err_obj.get("details", details)
        elif isinstance(data, dict):
            code = data.get("code", code)
            message = data.get("message", message)
            details = data.get("details", details)
    except Exception:
        if response.text:
            message = response.text

    exc_cls = _ERROR_MAP.get(code, AgentReadyAPIError)

    if exc_cls is RateLimitError or issubclass(exc_cls, RateLimitError):
        retry_after_hdr = response.headers.get("Retry-After") or response.headers.get(
            "retry-after"
        )
        retry_after_val: float | None = None
        if retry_after_hdr:
            try:
                retry_after_val = float(retry_after_hdr)
            except ValueError:
                pass
        raise RateLimitError(
            message=message,
            status_code=status_code,
            code=code,
            details=details,
            retry_after=retry_after_val,
        )

    raise exc_cls(
        message=message,
        status_code=status_code,
        code=code,
        details=details,
    )


class _WaitRetryAfterOrExponential(wait_base):
    """Wait strategy respecting RateLimitError.retry_after or exponential backoff."""

    def __init__(self, min: float = 1.0, max: float = 60.0) -> None:
        self._fallback = wait_exponential_jitter(initial=min, max=max)

    def __call__(self, retry_state: RetryCallState) -> float:
        if retry_state.outcome and retry_state.outcome.failed:
            exc = retry_state.outcome.exception()
            if isinstance(exc, RateLimitError) and exc.retry_after is not None:
                return exc.retry_after
        return float(self._fallback(retry_state))


def get_retry_policy(
    max_retries: int = DEFAULT_MAX_RETRIES,
    min_backoff: float = 1.0,
    max_backoff: float = 60.0,
) -> Retrying:
    """Build a synchronous tenacity Retrying policy for transient HTTP errors."""
    return Retrying(
        retry=retry_if_exception_type((RateLimitError, InternalServerError)),
        wait=_WaitRetryAfterOrExponential(min=min_backoff, max=max_backoff),
        stop=stop_after_attempt(max_retries),
        reraise=True,
    )


def get_async_retry_policy(
    max_retries: int = DEFAULT_MAX_RETRIES,
    min_backoff: float = 1.0,
    max_backoff: float = 60.0,
) -> AsyncRetrying:
    """Build an asynchronous tenacity AsyncRetrying policy for transient HTTP errors."""
    return AsyncRetrying(
        retry=retry_if_exception_type((RateLimitError, InternalServerError)),
        wait=_WaitRetryAfterOrExponential(min=min_backoff, max=max_backoff),
        stop=stop_after_attempt(max_retries),
        reraise=True,
    )
