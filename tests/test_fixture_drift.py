"""Drift protection tests for shared trajectory evaluation fixtures.

Verifies that tests/fixtures/trajectory_eval_cases.json matches the pinned upstream
SHA-256 checksum from Deadeye102000/Agentready (packages/agent-contracts).
"""

import hashlib
import json
import os
from pathlib import Path

import pytest

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "trajectory_eval_cases.json"

# Canonical upstream reference in Deadeye102000/Agentready:
# Path: packages/agent-contracts/test/fixtures/trajectory_eval_cases.json
PINNED_UPSTREAM_COMMIT = "1e0d183707400f0fbb2bd1a8b4773d99ba16dde3"
PINNED_FIXTURE_SHA256 = (
    "c694f2cdbfb4864c17f1695529421ab97bf3bec5c547058e13bc6ad1daee53b6"
)

# Note: A failing hash check means either real corruption or a legitimate
# intentional upstream fixture change requiring the pin to be manually bumped,
# not itself a bug.


def test_fixture_hash_matches_pinned_upstream() -> None:
    """Verify local fixture matches the canonical pinned SHA-256 hash."""
    assert FIXTURE_PATH.is_file(), f"Fixture file not found at {FIXTURE_PATH}"

    hasher = hashlib.sha256()
    hasher.update(FIXTURE_PATH.read_bytes())
    actual_hash = hasher.hexdigest()

    assert actual_hash == PINNED_FIXTURE_SHA256, (
        f"Fixture SHA-256 mismatch!\n"
        f"  Actual:   {actual_hash}\n"
        f"  Expected: {PINNED_FIXTURE_SHA256}\n"
        f"Pinned upstream commit: {PINNED_UPSTREAM_COMMIT}.\n"
        f"If the fixture was intentionally updated in the main repo, update "
        f"PINNED_FIXTURE_SHA256 and PINNED_UPSTREAM_COMMIT accordingly."
    )


def test_fixture_structure_and_schema() -> None:
    """Verify fixture is non-empty and every case has valid evaluator structure."""
    cases = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert isinstance(cases, list) and len(cases) > 0, "Fixture cases must not be empty"

    required_keys = {"id", "description", "policy", "traces", "expected"}
    expected_subkeys = {
        "passed",
        "score",
        "matched_steps",
        "total_expected",
        "violations",
    }

    for case in cases:
        assert required_keys.issubset(case.keys()), f"Missing keys in {case.get('id')}"
        assert expected_subkeys.issubset(
            case["expected"].keys()
        ), f"Case {case.get('id')} missing expected fields"


def test_fixture_matches_sibling_repo_if_available() -> None:
    """When running in dev with sibling Agentready workspace, assert byte identity."""
    sibling_env = os.environ.get("AGENTREADY_MAIN_REPO_PATH")
    candidate_paths = [
        (
            Path(sibling_env)
            / "packages"
            / "agent-contracts"
            / "test"
            / "fixtures"
            / "trajectory_eval_cases.json"
            if sibling_env
            else None
        ),
        Path(__file__).resolve().parents[2]
        / "Agentready"
        / "packages"
        / "agent-contracts"
        / "test"
        / "fixtures"
        / "trajectory_eval_cases.json",
    ]

    upstream_fixture = next((p for p in candidate_paths if p and p.is_file()), None)
    if not upstream_fixture:
        pytest.skip("Sibling Agentready repo not detected at candidate paths")

    local_bytes = FIXTURE_PATH.read_bytes()
    upstream_bytes = upstream_fixture.read_bytes()

    assert local_bytes == upstream_bytes, (
        f"Drift detected between local fixture and sibling repository at "
        f"{upstream_fixture}!\nSync the file or bump the pinned commit hash."
    )
