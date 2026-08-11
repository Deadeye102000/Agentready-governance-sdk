"""Sanity test for version."""

from agentready_governance_sdk import __version__


def test_version() -> None:
    assert __version__ == "0.1.0"
