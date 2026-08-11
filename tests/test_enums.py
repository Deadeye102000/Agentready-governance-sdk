"""Tests for domain models and enums matching AgentReady API schemas."""

from agentready_governance_sdk.models.common import (
    ActorType,
    ApprovalGateMode,
    ApprovalStatus,
    ExecutionStatus,
    FeatureFlagState,
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
    ]
    assert ToolCallStatus.PENDING == "PENDING"
    assert ToolCallStatus.RUNNING == "RUNNING"
    assert ToolCallStatus.SUCCEEDED == "SUCCEEDED"
    assert ToolCallStatus.FAILED == "FAILED"
    assert ToolCallStatus.BLOCKED == "BLOCKED"


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
