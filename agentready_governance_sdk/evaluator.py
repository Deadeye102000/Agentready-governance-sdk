"""Deterministic trajectory evaluator for AgentReady SDK.

This is a direct Python port of the TypeScript evaluator in
``packages/agent-contracts/src/evaluator.ts``.  Both implementations are
tested against the same fixture file
(``tests/fixtures/trajectory_eval_cases.json``) so that any algorithmic
divergence fails at least one language's test suite.
"""

import json
from typing import Any

from agentready_governance_sdk.models.contracts import (
    ExpectedStep,
    TrajectoryEvaluationResult,
    TrajectoryMode,
    TrajectoryPolicy,
)


def evaluate_trajectory_traces(
    traces: list[dict[str, Any]],
    policy: TrajectoryPolicy | dict[str, Any],
) -> TrajectoryEvaluationResult:
    """Evaluate a sequence of tool-call traces against a trajectory policy.

    Args:
        traces: List of trace dicts.  Each dict must contain ``tool_name``
            and may optionally contain ``step_index``, ``gate_status``, and
            ``input_payload`` (a dict of arguments).
        policy: Either a :class:`TrajectoryPolicy` model instance or a raw
            dict with the same shape (camelCase or snake_case keys are both
            accepted via Pydantic's alias generator).

    Returns:
        :class:`TrajectoryEvaluationResult` with ``passed``, ``score``,
        ``matched_steps``, ``total_expected``, and ``violations``.
    """
    if isinstance(policy, dict):
        policy = TrajectoryPolicy.model_validate(policy)

    violations: list[str] = []
    mode = policy.mode
    expected_steps = policy.expected_steps
    forbidden_tools = policy.forbidden_tools
    max_tool_calls = policy.max_tool_calls

    # 1. Max tool-call limit
    if max_tool_calls is not None and len(traces) > max_tool_calls:
        violations.append(
            f"Max tool calls exceeded: executed {len(traces)}, limit {max_tool_calls}"
        )

    # 2. Forbidden tool check
    for trace in traces:
        tool_name = trace.get("tool_name", "")
        if tool_name in forbidden_tools:
            step_idx = trace.get("step_index", "unknown")
            violations.append(
                f'Forbidden tool executed: "{tool_name}" at step {step_idx}'
            )

    # 3. Sequence matching (mirrors the for-loop in evaluator.ts exactly)
    matched_steps = 0
    trace_idx = 0

    for i, expected in enumerate(expected_steps):
        step_matched = False

        if mode == TrajectoryMode.STRICT_SEQUENCE:
            if trace_idx < len(traces) and _match_step(traces[trace_idx], expected):
                step_matched = True
                trace_idx += 1

        elif mode == TrajectoryMode.SUBSEQUENCE:
            while trace_idx < len(traces):
                if _match_step(traces[trace_idx], expected):
                    step_matched = True
                    trace_idx += 1
                    break
                trace_idx += 1

        elif mode == TrajectoryMode.UNORDERED:
            if any(_match_step(t, expected) for t in traces):
                step_matched = True

        if step_matched:
            matched_steps += 1
        elif expected.required:
            violations.append(f'Missing expected step [{i}]: tool "{expected.tool}"')

    # 4. Score & pass/fail (mirrors evaluator.ts)
    required_count = sum(1 for s in expected_steps if s.required)
    raw_score = 1.0 if required_count == 0 else matched_steps / required_count
    score = min(1.0, round(raw_score, 2))

    return TrajectoryEvaluationResult(
        passed=len(violations) == 0 and score == 1.0,
        score=score,
        matched_steps=matched_steps,
        total_expected=required_count,
        violations=violations,
    )


def _match_step(trace: dict[str, Any], expected: ExpectedStep) -> bool:
    """Return True if *trace* satisfies *expected* (mirrors ``matchStep`` in TS)."""
    if trace.get("tool_name") != expected.tool:
        return False

    if expected.expected_gate_status is not None:
        if trace.get("gate_status") != expected.expected_gate_status:
            return False

    if expected.expected_args is not None:
        trace_args = trace.get("input_payload") or {}
        if not isinstance(trace_args, dict):
            trace_args = {}
        for key, val in expected.expected_args.items():
            if json.dumps(trace_args.get(key)) != json.dumps(val):
                return False

    return True
