"""Custom exception classes for AgentReady Governance SDK."""

from typing import Any


class AgentReadyError(Exception):
    """Base exception for all AgentReady SDK errors."""


class AgentReadyAPIError(AgentReadyError):
    """Base class for HTTP API errors returned by AgentReady API."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        code: str = "API_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details if details is not None else {}

    def __str__(self) -> str:
        return f"[{self.status_code}] {self.code}: {self.message}"


class ValidationError(AgentReadyAPIError):
    """Raised when request payload or parameters fail validation (400 Bad Request)."""

    def __init__(
        self,
        message: str = "Validation error",
        status_code: int = 400,
        code: str = "VALIDATION_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message, status_code=status_code, code=code, details=details
        )


class AuthenticationError(AgentReadyAPIError):
    """Raised when authentication fails (401 Unauthorized).

    The backend emits ``code: "UNAUTHORIZED"`` for all authentication failures.
    """

    def __init__(
        self,
        message: str = "Authentication failed",
        status_code: int = 401,
        code: str = "UNAUTHORIZED",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message, status_code=status_code, code=code, details=details
        )


class PermissionDeniedError(AgentReadyAPIError):
    """Raised when actor lacks necessary permission (403 Forbidden).

    The backend emits ``code: "FORBIDDEN"`` for all authorization failures.
    """

    def __init__(
        self,
        message: str = "Permission denied",
        status_code: int = 403,
        code: str = "FORBIDDEN",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message, status_code=status_code, code=code, details=details
        )


class InsufficientScopeError(PermissionDeniedError):
    """Raised when API key scope is insufficient for the operation (403 Forbidden)."""

    def __init__(
        self,
        message: str = "Insufficient API key scope",
        status_code: int = 403,
        code: str = "INSUFFICIENT_SCOPE",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message, status_code=status_code, code=code, details=details
        )


class NotFoundError(AgentReadyAPIError):
    """Raised when requested resource is not found (404 Not Found)."""

    def __init__(
        self,
        message: str = "Resource not found",
        status_code: int = 404,
        code: str = "NOT_FOUND",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message, status_code=status_code, code=code, details=details
        )


class ConflictError(AgentReadyAPIError):
    """Raised when request conflicts with current resource state (409 Conflict)."""

    def __init__(
        self,
        message: str = "Resource conflict",
        status_code: int = 409,
        code: str = "CONFLICT",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message, status_code=status_code, code=code, details=details
        )


class ConcurrentToolCallDisallowedError(ConflictError):
    """Raised when a second tool call is checked while one is already pending (409).

    The backend emits ``code: "CONCURRENT_TOOL_CALL_DISALLOWED"``.
    Complete the pending tool call via ``report_tool_call_result`` before
    checking a new one.
    """

    def __init__(
        self,
        message: str = "A tool call is already pending for this execution",
        status_code: int = 409,
        code: str = "CONCURRENT_TOOL_CALL_DISALLOWED",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message, status_code=status_code, code=code, details=details
        )


class IdempotencyKeyMismatchError(ConflictError):
    """Raised when an idempotency key is reused with a different payload (409).

    The backend emits ``code: "IDEMPOTENCY_KEY_MISMATCH"``.
    """

    def __init__(
        self,
        message: str = "Idempotency key already used with a different payload",
        status_code: int = 409,
        code: str = "IDEMPOTENCY_KEY_MISMATCH",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message, status_code=status_code, code=code, details=details
        )


class PayloadTooLargeError(AgentReadyAPIError):
    """Raised when request payload exceeds size limits (413 Payload Too Large)."""

    def __init__(
        self,
        message: str = "Payload too large",
        status_code: int = 413,
        code: str = "PAYLOAD_TOO_LARGE",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message, status_code=status_code, code=code, details=details
        )


class RateLimitError(AgentReadyAPIError):
    """Raised when request rate limit is exceeded (429 Too Many Requests).

    The backend emits ``code: "RATE_LIMITED"``.
    Check ``retry_after`` for the number of seconds to wait before retrying.
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        status_code: int = 429,
        code: str = "RATE_LIMITED",
        details: dict[str, Any] | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(
            message=message, status_code=status_code, code=code, details=details
        )
        self.retry_after = retry_after


class ApprovalRequiredError(AgentReadyAPIError):
    """Raised when an operation is gated and requires manual approval."""

    def __init__(
        self,
        approval_request_id: str | None = None,
        tool_name: str | None = None,
        execution_id: str | None = None,
        message: str | None = None,
        status_code: int = 403,
        code: str = "APPROVAL_REQUIRED",
        details: dict[str, Any] | None = None,
    ) -> None:
        self.approval_request_id = approval_request_id
        self.tool_name = tool_name
        self.execution_id = execution_id
        if message is None:
            if approval_request_id:
                if tool_name:
                    message = (
                        f"Tool '{tool_name}' requires approval "
                        f"(request ID: {approval_request_id})"
                    )
                else:
                    message = f"Approval required (request ID: {approval_request_id})"

            else:
                message = "Approval required"
        super().__init__(
            message=message, status_code=status_code, code=code, details=details
        )


class ToolBlockedError(AgentReadyError):
    """Raised when a tool execution is blocked by policy or feature flag."""

    def __init__(
        self,
        reason: str,
        tool_name: str | None = None,
        risk_score: float | None = None,
    ) -> None:
        self.reason = reason
        self.tool_name = tool_name
        self.risk_score = risk_score
        message = (
            f"Tool '{tool_name}' was blocked: {reason}"
            if tool_name
            else f"Tool blocked: {reason}"
        )
        super().__init__(message)
        self.message = message


class PolicyTimeoutError(AgentReadyError):
    """Raised when waiting for policy evaluation or approval times out."""

    def __init__(
        self, message: str = "Policy evaluation or approval timed out"
    ) -> None:
        super().__init__(message)
        self.message = message


class InternalServerError(AgentReadyAPIError):
    """Raised when server encounters an internal error (500 Internal Server Error).

    The backend emits ``code: "INTERNAL_ERROR"``.
    """

    def __init__(
        self,
        message: str = "Internal server error",
        status_code: int = 500,
        code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message, status_code=status_code, code=code, details=details
        )


class ApprovalTimeoutError(PolicyTimeoutError):
    """SDK-side control flow exception when waiting for approval times out."""

    def __init__(
        self, message: str = "Approval request timed out waiting for decision"
    ) -> None:
        super().__init__(message)
        self.message = message


class ApprovalRejectedError(AgentReadyError):
    """SDK-side control flow exception when approval request is rejected or expired."""

    def __init__(
        self, message: str = "Approval request was rejected or expired"
    ) -> None:
        super().__init__(message)
        self.message = message
