"""Tests for HTTP transport layer, status handling, and retry policy."""

from unittest.mock import MagicMock

import httpx
import pytest
import respx

from agentready_governance_sdk._transport import (
    _ERROR_MAP,
    _raise_for_status,
    _WaitRetryAfterOrExponential,
    get_async_retry_policy,
    get_retry_policy,
)
from agentready_governance_sdk.exceptions import (
    AgentReadyAPIError,
    RateLimitError,
    ValidationError,
)


def test_raise_for_status_mapped_errors() -> None:
    for code_str, exc_cls in _ERROR_MAP.items():
        resp = httpx.Response(
            status_code=400,
            json={
                "error": {
                    "code": code_str,
                    "message": f"Test {code_str}",
                    "details": {"foo": "bar"},
                }
            },
        )
        with pytest.raises(exc_cls) as exc_info:
            _raise_for_status(resp)
        assert exc_info.value.code == code_str
        assert exc_info.value.message == f"Test {code_str}"
        assert exc_info.value.details == {"foo": "bar"}


def test_raise_for_status_unmapped_error_code() -> None:
    resp = httpx.Response(
        status_code=418,
        json={
            "error": {
                "code": "IM_A_TEAPOT",
                "message": "I am a teapot",
                "details": {},
            }
        },
    )
    with pytest.raises(AgentReadyAPIError) as exc_info:
        _raise_for_status(resp)
    assert exc_info.value.__class__ is AgentReadyAPIError
    assert exc_info.value.code == "IM_A_TEAPOT"
    assert exc_info.value.status_code == 418
    assert exc_info.value.message == "I am a teapot"


def test_raise_for_status_non_json_body() -> None:
    resp = httpx.Response(
        status_code=500,
        text="Internal Server Error Crash",
    )
    with pytest.raises(AgentReadyAPIError) as exc_info:
        _raise_for_status(resp)
    assert exc_info.value.status_code == 500
    assert exc_info.value.message == "Internal Server Error Crash"


@respx.mock
def test_400_validation_error_no_retry() -> None:
    respx.get("http://localhost:3001/test").respond(
        status_code=400,
        json={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid input",
                "details": {},
            }
        },
    )

    calls = 0

    def attempt_request() -> httpx.Response:
        nonlocal calls
        calls += 1
        resp = httpx.get("http://localhost:3001/test")
        _raise_for_status(resp)
        return resp

    retrier = get_retry_policy(max_retries=3)
    with pytest.raises(ValidationError):
        retrier(attempt_request)

    assert calls == 1  # Exactly 1 call, no retries performed


@respx.mock
def test_429_succeeds_after_retry() -> None:
    respx.get("http://localhost:3001/test").side_effect = [
        httpx.Response(
            status_code=429,
            json={
                "error": {
                    "code": "RATE_LIMITED",
                    "message": "Rate limit",
                    "details": {},
                }
            },
        ),
        httpx.Response(status_code=200, json={"status": "ok"}),
    ]

    calls = 0

    def attempt_request() -> dict:
        nonlocal calls
        calls += 1
        resp = httpx.get("http://localhost:3001/test")
        _raise_for_status(resp)
        return resp.json()

    retrier = get_retry_policy(max_retries=3, min_backoff=0.001, max_backoff=0.01)
    result = retrier(attempt_request)
    assert result == {"status": "ok"}
    assert calls == 2


@respx.mock
async def test_async_retry_policy_429_retry() -> None:
    respx.get("http://localhost:3001/test-async").side_effect = [
        httpx.Response(
            status_code=429,
            json={
                "error": {
                    "code": "RATE_LIMITED",
                    "message": "Rate limit",
                    "details": {},
                }
            },
        ),
        httpx.Response(status_code=200, json={"status": "ok"}),
    ]

    calls = 0

    async def attempt_request() -> dict:
        nonlocal calls
        calls += 1
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:3001/test-async")
            _raise_for_status(resp)
            return resp.json()

    retrier = get_async_retry_policy(max_retries=3, min_backoff=0.001, max_backoff=0.01)
    result = await retrier(attempt_request)
    assert result == {"status": "ok"}
    assert calls == 2


def test_retry_after_wait_strategy() -> None:
    resp_with_header = httpx.Response(
        status_code=429,
        headers={"Retry-After": "12.5"},
        json={
            "error": {
                "code": "RATE_LIMITED",
                "message": "Too Many Requests",
                "details": {},
            }
        },
    )
    with pytest.raises(RateLimitError) as exc_info:
        _raise_for_status(resp_with_header)
    assert exc_info.value.retry_after == 12.5

    wait_strat = _WaitRetryAfterOrExponential(min=1.0, max=60.0)
    mock_state = MagicMock()
    mock_state.outcome.failed = True
    mock_state.outcome.exception.return_value = exc_info.value

    wait_seconds = wait_strat(mock_state)
    assert wait_seconds == 12.5
