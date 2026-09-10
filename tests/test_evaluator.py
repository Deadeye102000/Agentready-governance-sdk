"""Tests for the trajectory evaluator — loaded from the shared JSON fixture file.

Both this file and the TypeScript test suite in
``packages/agent-contracts/src/evaluator.test.ts`` must consume
``tests/fixtures/trajectory_eval_cases.json``.  Any case that fails here but
passes there (or vice-versa) indicates a cross-language algorithm divergence.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from agentready_governance_sdk.evaluator import evaluate_trajectory_traces
from agentready_governance_sdk.models.contracts import TrajectoryEvaluationResult

FIXTURE_FILE = Path(__file__).parent / "fixtures" / "trajectory_eval_cases.json"


def _load_cases() -> list[tuple[str, dict[str, Any]]]:
    cases = json.loads(FIXTURE_FILE.read_text())
    return [(c["id"], c) for c in cases]


@pytest.mark.parametrize("case_id,case", _load_cases())
def test_evaluate_trajectory_from_fixture(case_id: str, case: dict[str, Any]) -> None:
    """Run one fixture case through evaluate_trajectory_traces and assert result."""
    result = evaluate_trajectory_traces(
        traces=case["traces"],
        policy=case["policy"],
    )

    expected = case["expected"]
    assert result.passed == expected["passed"], (
        f"[{case_id}] passed mismatch: got {result.passed}, want {expected['passed']}"
    )
    assert result.score == expected["score"], (
        f"[{case_id}] score mismatch: got {result.score}, want {expected['score']}"
    )
    assert result.matched_steps == expected["matched_steps"], (
        f"[{case_id}] matched_steps mismatch: got {result.matched_steps}"
    )
    assert result.total_expected == expected["total_expected"], (
        f"[{case_id}] total_expected mismatch: got {result.total_expected}"
    )
    assert result.violations == expected["violations"], (
        f"[{case_id}] violations mismatch:\n"
        f"  got  {result.violations}\n"
        f"  want {expected['violations']}"
    )


@pytest.mark.parametrize("case_id,case", _load_cases())
def test_evaluate_trajectory_dict_input(case_id: str, case: dict[str, Any]) -> None:
    """evaluate_trajectory_traces must also accept a raw dict as policy input."""
    result = evaluate_trajectory_traces(
        traces=case["traces"],
        policy=case["policy"],  # dict, not TrajectoryPolicy model
    )
    assert isinstance(result, TrajectoryEvaluationResult)
    expected = case["expected"]
    assert result.passed == expected["passed"]


class TestEvaluatorEdgeCases:
    """Additional edge cases not in the JSON fixture."""

    def test_score_rounds_to_two_decimal_places(self) -> None:
        """Score is rounded to exactly 2 dp (mirrors TS Number(score.toFixed(2)))."""
        result = evaluate_trajectory_traces(
            traces=[{"tool_name": "a"}],
            policy={
                "mode": "STRICT_SEQUENCE",
                "expected_steps": [
                    {"tool": "a"},
                    {"tool": "b"},
                    {"tool": "c"},
                ],
            },
        )
        # 1/3 = 0.333... should round to 0.33
        assert result.score == 0.33

    def test_all_optional_no_required_score_is_1(self) -> None:
        """When all expected steps are optional, score is 1.0 even with no matches."""
        result = evaluate_trajectory_traces(
            traces=[],
            policy={
                "mode": "STRICT_SEQUENCE",
                "expected_steps": [
                    {"tool": "a", "required": False},
                    {"tool": "b", "required": False},
                ],
            },
        )
        assert result.score == 1.0
        assert result.passed is True
        assert result.total_expected == 0

    def test_multiple_violations_accumulated(self) -> None:
        """Max calls exceeded + forbidden tool + missing step = 3 violations."""
        result = evaluate_trajectory_traces(
            traces=[
                {"tool_name": "bad_tool", "step_index": 0},
                {"tool_name": "other", "step_index": 1},
                {"tool_name": "extra", "step_index": 2},
            ],
            policy={
                "mode": "STRICT_SEQUENCE",
                "expected_steps": [{"tool": "good_tool"}],
                "forbidden_tools": ["bad_tool"],
                "max_tool_calls": 2,
            },
        )
        assert result.passed is False
        assert len(result.violations) == 3
