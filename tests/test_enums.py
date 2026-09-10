"""Tests for domain models and enums matching AgentReady API schemas."""

from agentready_governance_sdk.models.common import (
    ActorType,
    ApiKeyScope,
    ApprovalGateMode,
    ApprovalStatus,
    EvalRunStatus,
    ExecutionStatus,
    FeatureFlagState,
    ToolCallDecision,
    ToolCallStatus,
)


def test_execution_status_values() -> None:
    assert [status.value for status in ExecutionStatus] == [
        "QUEUED",
        "RUNNING",
        "WAITING_FOR_APPROVAL",
        "SUCCEEDED",
        "FAILED",
        "CANCELLED",
    ]
    assert ExecutionStatus.QUEUED == "QUEUED"
    assert ExecutionStatus.RUNNING == "RUNNING"
    assert ExecutionStatus.WAITING_FOR_APPROVAL == "WAITING_FOR_APPROVAL"
    assert ExecutionStatus.SUCCEEDED == "SUCCEEDED"
    assert ExecutionStatus.FAILED == "FAILED"
    assert ExecutionStatus.CANCELLED == "CANCELLED"


def test_tool_call_status_values() -> None:
    assert [status.value for status in ToolCallStatus] == [
        "PENDING",
        "RUNNING",
        "SUCCEEDED",
        "FAILED",
        "BLOCKED",
        "AWAITING_APPROVAL",
    ]
    assert ToolCallStatus.PENDING == "PENDING"
    assert ToolCallStatus.RUNNING == "RUNNING"
    assert ToolCallStatus.SUCCEEDED == "SUCCEEDED"
    assert ToolCallStatus.FAILED == "FAILED"
    assert ToolCallStatus.BLOCKED == "BLOCKED"
    assert ToolCallStatus.AWAITING_APPROVAL == "AWAITING_APPROVAL"


def test_approval_gate_mode_values() -> None:
    assert [mode.value for mode in ApprovalGateMode] == [
        "AUTOMATIC",
        "REQUIRE_APPROVAL",
        "BLOCKED",
    ]
    assert ApprovalGateMode.AUTOMATIC == "AUTOMATIC"
    assert ApprovalGateMode.REQUIRE_APPROVAL == "REQUIRE_APPROVAL"
    assert ApprovalGateMode.BLOCKED == "BLOCKED"


def test_feature_flag_state_values() -> None:
    assert [state.value for state in FeatureFlagState] == ["ENABLED", "DISABLED"]
    assert FeatureFlagState.ENABLED == "ENABLED"
    assert FeatureFlagState.DISABLED == "DISABLED"


def test_approval_status_values() -> None:
    assert [status.value for status in ApprovalStatus] == [
        "PENDING",
        "APPROVED",
        "REJECTED",
        "EXPIRED",
    ]
    assert ApprovalStatus.PENDING == "PENDING"
    assert ApprovalStatus.APPROVED == "APPROVED"
    assert ApprovalStatus.REJECTED == "REJECTED"
    assert ApprovalStatus.EXPIRED == "EXPIRED"


def test_actor_type_values() -> None:
    assert [actor.value for actor in ActorType] == ["USER", "AGENT", "SYSTEM"]
    assert ActorType.USER == "USER"
    assert ActorType.AGENT == "AGENT"
    assert ActorType.SYSTEM == "SYSTEM"


def test_tool_call_decision_values() -> None:
    assert [d.value for d in ToolCallDecision] == [
        "ALLOW",
        "BLOCK",
        "WAIT_FOR_APPROVAL",
    ]
    assert ToolCallDecision.ALLOW == "ALLOW"
    assert ToolCallDecision.BLOCK == "BLOCK"
    assert ToolCallDecision.WAIT_FOR_APPROVAL == "WAIT_FOR_APPROVAL"


def test_eval_run_status_values() -> None:
    assert [s.value for s in EvalRunStatus] == [
        "QUEUED",
        "RUNNING",
        "PASSED",
        "FAILED",
        "ERRORED",
    ]
    assert EvalRunStatus.QUEUED == "QUEUED"
    assert EvalRunStatus.RUNNING == "RUNNING"
    assert EvalRunStatus.PASSED == "PASSED"
    assert EvalRunStatus.FAILED == "FAILED"
    assert EvalRunStatus.ERRORED == "ERRORED"


def test_api_key_scope_values() -> None:
    assert ApiKeyScope.AGENT_EXECUTION_WRITE == "agent_execution:write"
    assert ApiKeyScope.AGENT_EXECUTION_READ == "agent_execution:read"
    assert ApiKeyScope.GOVERNANCE_WRITE == "governance:write"
    assert ApiKeyScope.GOVERNANCE_READ == "governance:read"
    assert ApiKeyScope.EVAL_WRITE == "eval:write"
    assert ApiKeyScope.EVAL_READ == "eval:read"
    assert ApiKeyScope.AUDIT_READ == "audit:read"
    assert ApiKeyScope.API_KEY_WRITE == "api_key:write"
    assert ApiKeyScope.API_KEY_READ == "api_key:read"
