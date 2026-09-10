"""Tests for SDK exception hierarchy and attributes."""

import pytest

from agentready_governance_sdk.exceptions import (
    AgentReadyAPIError,
    AgentReadyError,
    ApprovalRejectedError,
    ApprovalRequiredError,
    ApprovalTimeoutError,
    AuthenticationError,
    ConcurrentToolCallDisallowedError,
    ConflictError,
    IdempotencyKeyMismatchError,
    InsufficientScopeError,
    InternalServerError,
    NotFoundError,
    PayloadTooLargeError,
    PermissionDeniedError,
    RateLimitError,
    ValidationError,
)


def test_agent_ready_api_error_attributes() -> None:
    err = AgentReadyAPIError(
        message="Something went wrong",
        status_code=502,
        code="BAD_GATEWAY",
        details={"path": "/v1/test"},
    )
    assert isinstance(err, AgentReadyError)
    assert err.message == "Something went wrong"
    assert err.status_code == 502
    assert err.code == "BAD_GATEWAY"
    assert err.details == {"path": "/v1/test"}
    assert str(err) == "[502] BAD_GATEWAY: Something went wrong"


@pytest.mark.parametrize(
    "exc_cls,expected_status,expected_code",
    [
        (ValidationError, 400, "VALIDATION_ERROR"),
        (AuthenticationError, 401, "UNAUTHORIZED"),
        (PermissionDeniedError, 403, "FORBIDDEN"),
        (InsufficientScopeError, 403, "INSUFFICIENT_SCOPE"),
        (NotFoundError, 404, "NOT_FOUND"),
        (ConflictError, 409, "CONFLICT"),
        (PayloadTooLargeError, 413, "PAYLOAD_TOO_LARGE"),
        (RateLimitError, 429, "RATE_LIMITED"),
        (ApprovalRequiredError, 403, "APPROVAL_REQUIRED"),
        (InternalServerError, 500, "INTERNAL_ERROR"),
        (ConcurrentToolCallDisallowedError, 409, "CONCURRENT_TOOL_CALL_DISALLOWED"),
        (IdempotencyKeyMismatchError, 409, "IDEMPOTENCY_KEY_MISMATCH"),
    ],
)
def test_api_exception_subclasses(
    exc_cls: type[AgentReadyAPIError], expected_status: int, expected_code: str
) -> None:
    err = exc_cls(message="Custom test message", details={"field": "test"})
    assert isinstance(err, AgentReadyAPIError)
    assert isinstance(err, AgentReadyError)
    assert isinstance(err, Exception)
    assert err.status_code == expected_status
    assert err.code == expected_code
    assert err.message == "Custom test message"
    assert err.details == {"field": "test"}


def test_insufficient_scope_inheritance() -> None:
    err = InsufficientScopeError("Scope missing")
    assert isinstance(err, PermissionDeniedError)
    assert isinstance(err, AgentReadyAPIError)
    assert isinstance(err, AgentReadyError)


def test_control_flow_exceptions() -> None:
    timeout_err = ApprovalTimeoutError("Timed out after 30s")
    assert isinstance(timeout_err, AgentReadyError)
    assert not isinstance(timeout_err, AgentReadyAPIError)
    assert timeout_err.message == "Timed out after 30s"

    rejected_err = ApprovalRejectedError("User rejected action")
    assert isinstance(rejected_err, AgentReadyError)
    assert not isinstance(rejected_err, AgentReadyAPIError)
    assert rejected_err.message == "User rejected action"
