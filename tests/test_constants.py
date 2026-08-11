"""Tests for SDK default constants."""

from agentready_governance_sdk._constants import (
    DEFAULT_BASE_URL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RATE_LIMIT_AUTH_RPM,
    DEFAULT_RATE_LIMIT_GENERAL_RPM,
    DEFAULT_TIMEOUT,
)


def test_constants_values() -> None:
    assert DEFAULT_BASE_URL == "http://localhost:3001"
    assert DEFAULT_TIMEOUT == 30.0
    assert DEFAULT_MAX_RETRIES == 3
    assert DEFAULT_RATE_LIMIT_GENERAL_RPM == 300
    assert DEFAULT_RATE_LIMIT_AUTH_RPM == 20
