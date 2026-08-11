"""Round-trip tests for Pydantic models ensuring camelCase compatibility."""

from datetime import datetime, timezone

from agentready_governance_sdk.models.audit import AuditLogEntry
from agentready_governance_sdk.models.common import (
    ActorType,
    ApprovalGateMode,
    ApprovalStatus,
    ExecutionStatus,
    FeatureFlagState,
    ToolCallStatus,
)
from agentready_governance_sdk.models.executions import (
    AgentExecution,
    CreateExecutionInput,
    UpdateExecutionInput,
)
from agentready_governance_sdk.models.governance import (
    ApprovalGate,
    ApprovalRequest,
    FeatureFlag,
    UpsertAgentFeatureFlagInput,
    UpsertApprovalGateInput,
)
from agentready_governance_sdk.models.traces import (
    CreateToolCallTraceInput,
    ToolCallTrace,
    UpdateToolCallTraceInput,
)


def test_agent_execution_roundtrip() -> None:
    payload = {
        "id": "exec_123",
        "organizationId": "org_456",
        "projectId": "proj_789",
        "agentId": "agent_007",
        "taskId": "task_111",
        "contractId": "contract_222",
        "status": "WAITING_FOR_APPROVAL",
        "objective": "Perform automated database migration",
        "input": {"targetEnv": "production"},
        "output": None,
        "riskScore": 85,
        "maxAttempts": 3,
        "attemptCount": 1,
        "timeoutMs": 60000,
        "timedOutAt": None,
        "failureReason": None,
        "startedAt": "2026-08-11T12:00:00Z",
        "completedAt": None,
        "createdAt": "2026-08-11T11:59:00Z",
        "updatedAt": "2026-08-11T12:00:00Z",
    }

    # Deserialization & Python snake_case access
    execution = AgentExecution.model_validate(payload)
    assert execution.id == "exec_123"
    assert execution.organization_id == "org_456"
    assert execution.project_id == "proj_789"
    assert execution.agent_id == "agent_007"
    assert execution.status == ExecutionStatus.WAITING_FOR_APPROVAL
    assert execution.risk_score == 85
    assert execution.max_attempts == 3
    assert execution.attempt_count == 1
    assert execution.timeout_ms == 60000

    # Serialization back to camelCase JSON dictionary
    dumped = execution.model_dump(by_alias=True, mode="json")
    assert dumped["organizationId"] == "org_456"
    assert dumped["projectId"] == "proj_789"
    assert dumped["riskScore"] == 85
    assert dumped["status"] == "WAITING_FOR_APPROVAL"
    assert dumped["maxAttempts"] == 3


def test_create_execution_input_serialization() -> None:
    create_input = CreateExecutionInput(
        project_id="proj_789",
        agent_id="agent_007",
        objective="Run compliance audit",
        risk_score=42,
        timeout_ms=30000,
        input={"scope": "all"},
    )
    assert create_input.project_id == "proj_789"
    assert create_input.risk_score == 42

    dumped = create_input.model_dump(by_alias=True, mode="json", exclude_none=True)
    assert dumped["projectId"] == "proj_789"
    assert dumped["agentId"] == "agent_007"
    assert dumped["riskScore"] == 42
    assert dumped["timeoutMs"] == 30000


def test_update_execution_input_serialization() -> None:
    now = datetime.now(timezone.utc)
    update_input = UpdateExecutionInput(
        status=ExecutionStatus.SUCCEEDED,
        output={"result": "OK"},
        completed_at=now,
    )
    assert update_input.status == ExecutionStatus.SUCCEEDED

    dumped = update_input.model_dump(by_alias=True, mode="json", exclude_none=True)
    assert dumped["status"] == "SUCCEEDED"
    assert dumped["output"] == {"result": "OK"}
    assert "completedAt" in dumped


def test_tool_call_trace_roundtrip() -> None:
    payload = {
        "id": "trace_999",
        "organizationId": "org_456",
        "executionId": "exec_123",
        "agentId": "agent_007",
        "toolName": "db_execute_sql",
        "status": "RUNNING",
        "input": {"query": "DROP TABLE test;"},
        "output": None,
        "error": None,
        "latencyMs": 120,
        "approvalRequestId": "app_555",
        "startedAt": "2026-08-11T12:00:00Z",
        "completedAt": None,
    }

    trace = ToolCallTrace.model_validate(payload)
    assert trace.id == "trace_999"
    assert trace.execution_id == "exec_123"
    assert trace.tool_name == "db_execute_sql"
    assert trace.status == ToolCallStatus.RUNNING
    assert trace.latency_ms == 120
    assert trace.approval_request_id == "app_555"

    dumped = trace.model_dump(by_alias=True, mode="json")
    assert dumped["executionId"] == "exec_123"
    assert dumped["toolName"] == "db_execute_sql"
    assert dumped["latencyMs"] == 120
    assert dumped["approvalRequestId"] == "app_555"


def test_tool_call_trace_inputs() -> None:
    create_trace = CreateToolCallTraceInput(
        execution_id="exec_123",
        agent_id="agent_007",
        tool_name="bash_exec",
        input={"cmd": "ls -la"},
    )
    dumped_create = create_trace.model_dump(by_alias=True, mode="json")
    assert dumped_create["executionId"] == "exec_123"
    assert dumped_create["agentId"] == "agent_007"
    assert dumped_create["toolName"] == "bash_exec"
    assert dumped_create["status"] == "PENDING"

    update_trace = UpdateToolCallTraceInput(
        status=ToolCallStatus.SUCCEEDED,
        output={"exit_code": 0},
        latency_ms=45,
    )
    dumped_update = update_trace.model_dump(
        by_alias=True, mode="json", exclude_none=True
    )
    assert dumped_update["status"] == "SUCCEEDED"
    assert dumped_update["latencyMs"] == 45


def test_approval_gate_roundtrip() -> None:
    payload = {
        "id": "gate_1",
        "organizationId": "org_456",
        "capability": "db:write",
        "mode": "REQUIRE_APPROVAL",
        "reason": "Production write protection",
        "riskLevel": 75,
        "enabled": True,
        "createdAt": "2026-08-11T10:00:00Z",
        "updatedAt": "2026-08-11T10:00:00Z",
    }

    gate = ApprovalGate.model_validate(payload)
    assert gate.organization_id == "org_456"
    assert gate.capability == "db:write"
    assert gate.mode == ApprovalGateMode.REQUIRE_APPROVAL
    assert gate.risk_level == 75
    assert gate.enabled is True

    dumped = gate.model_dump(by_alias=True, mode="json")
    assert dumped["organizationId"] == "org_456"
    assert dumped["riskLevel"] == 75
    assert dumped["mode"] == "REQUIRE_APPROVAL"


def test_upsert_approval_gate_input() -> None:
    gate_input = UpsertApprovalGateInput(
        capability="fs:write",
        mode=ApprovalGateMode.BLOCKED,
        risk_level=90,
    )
    dumped = gate_input.model_dump(by_alias=True, mode="json")
    assert dumped["capability"] == "fs:write"
    assert dumped["mode"] == "BLOCKED"
    assert dumped["riskLevel"] == 90


def test_feature_flag_roundtrip() -> None:
    payload = {
        "id": "flag_1",
        "organizationId": "org_456",
        "agentId": "agent_007",
        "capability": "file:delete",
        "state": "DISABLED",
        "description": "Disable deletion by agent",
        "createdAt": "2026-08-11T10:00:00Z",
        "updatedAt": "2026-08-11T10:00:00Z",
    }

    flag = FeatureFlag.model_validate(payload)
    assert flag.organization_id == "org_456"
    assert flag.agent_id == "agent_007"
    assert flag.capability == "file:delete"
    assert flag.state == FeatureFlagState.DISABLED

    dumped = flag.model_dump(by_alias=True, mode="json")
    assert dumped["agentId"] == "agent_007"
    assert dumped["state"] == "DISABLED"


def test_upsert_feature_flag_input() -> None:
    flag_input = UpsertAgentFeatureFlagInput(
        capability="network:outbound",
        state=FeatureFlagState.ENABLED,
        agent_id="agent_007",
    )
    dumped = flag_input.model_dump(by_alias=True, mode="json", exclude_none=True)
    assert dumped["capability"] == "network:outbound"
    assert dumped["state"] == "ENABLED"
    assert dumped["agentId"] == "agent_007"


def test_approval_request_roundtrip() -> None:
    payload = {
        "id": "app_555",
        "organizationId": "org_456",
        "agentId": "agent_007",
        "requestedAction": "db:drop_table",
        "reason": "Database cleanup task",
        "payload": {"table": "legacy_logs"},
        "status": "PENDING",
        "expiresAt": "2026-08-12T12:00:00Z",
        "reviewedByUserId": None,
        "reviewedAt": None,
        "createdAt": "2026-08-11T12:00:00Z",
        "updatedAt": "2026-08-11T12:00:00Z",
    }

    req = ApprovalRequest.model_validate(payload)
    assert req.requested_action == "db:drop_table"
    assert req.status == ApprovalStatus.PENDING
    assert req.payload == {"table": "legacy_logs"}

    dumped = req.model_dump(by_alias=True, mode="json")
    assert dumped["requestedAction"] == "db:drop_table"
    assert dumped["status"] == "PENDING"


def test_audit_log_entry_roundtrip() -> None:
    payload = {
        "id": "audit_100",
        "organizationId": "org_456",
        "actorType": "AGENT",
        "actorUserId": None,
        "actorAgentId": "agent_007",
        "action": "APPROVAL_GATE_TRIGGERED",
        "targetType": "ApprovalGate",
        "targetId": "gate_1",
        "metadata": {"riskScore": 85},
        "createdAt": "2026-08-11T12:00:00Z",
    }

    entry = AuditLogEntry.model_validate(payload)
    assert entry.actor_type == ActorType.AGENT
    assert entry.actor_agent_id == "agent_007"
    assert entry.target_type == "ApprovalGate"

    dumped = entry.model_dump(by_alias=True, mode="json")
    assert dumped["actorType"] == "AGENT"
    assert dumped["actorAgentId"] == "agent_007"
    assert dumped["targetType"] == "ApprovalGate"
