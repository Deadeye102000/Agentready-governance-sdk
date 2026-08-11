"""Tests for AsyncGovernanceClient execution and tool call trace methods."""

import pytest
import respx

from agentready_governance_sdk.client import AsyncGovernanceClient
from agentready_governance_sdk.exceptions import PermissionDeniedError
from agentready_governance_sdk.models.common import ExecutionStatus, ToolCallStatus
from agentready_governance_sdk.models.executions import (
    AgentExecution,
    CreateExecutionInput,
    UpdateExecutionInput,
)
from agentready_governance_sdk.models.traces import (
    CreateToolCallTraceInput,
    ToolCallTrace,
    UpdateToolCallTraceInput,
)

BASE_URL = "http://localhost:3001"
API_KEY = "test-key"


@pytest.fixture
def client() -> AsyncGovernanceClient:
    return AsyncGovernanceClient(api_key=API_KEY, base_url=BASE_URL)


@respx.mock
async def test_create_execution_queued(client: AsyncGovernanceClient) -> None:
    exec_json = {
        "id": "exec_1",
        "organizationId": "org_1",
        "projectId": "proj_1",
        "agentId": "agent_1",
        "status": "QUEUED",
        "objective": "Run task",
        "input": {},
        "riskScore": 10,
        "maxAttempts": 1,
        "attemptCount": 0,
        "createdAt": "2026-08-11T12:00:00Z",
        "updatedAt": "2026-08-11T12:00:00Z",
    }
    route = respx.post(f"{BASE_URL}/api/v1/executions").respond(
        status_code=201, json=exec_json
    )

    inp = CreateExecutionInput(
        project_id="proj_1",
        agent_id="agent_1",
        objective="Run task",
    )
    result = await client.create_execution(inp)
    assert route.called
    assert isinstance(result, AgentExecution)
    assert result.id == "exec_1"
    assert result.status == ExecutionStatus.QUEUED


@respx.mock
async def test_create_execution_waiting_for_approval(
    client: AsyncGovernanceClient,
) -> None:
    exec_json = {
        "id": "exec_2",
        "organizationId": "org_1",
        "projectId": "proj_1",
        "agentId": "agent_1",
        "status": "WAITING_FOR_APPROVAL",
        "objective": "Run gated task",
        "input": {},
        "riskScore": 90,
        "createdAt": "2026-08-11T12:00:00Z",
        "updatedAt": "2026-08-11T12:00:00Z",
    }
    respx.post(f"{BASE_URL}/api/v1/executions").respond(status_code=201, json=exec_json)

    inp = CreateExecutionInput(
        project_id="proj_1",
        agent_id="agent_1",
        objective="Run gated task",
        risk_score=90,
    )
    # Must NOT raise exception for WAITING_FOR_APPROVAL status in 201 response!
    result = await client.create_execution(inp)
    assert isinstance(result, AgentExecution)
    assert result.id == "exec_2"
    assert result.status == ExecutionStatus.WAITING_FOR_APPROVAL


@respx.mock
async def test_create_execution_403_error(client: AsyncGovernanceClient) -> None:
    respx.post(f"{BASE_URL}/api/v1/executions").respond(
        status_code=403,
        json={
            "error": {
                "code": "PERMISSION_DENIED",
                "message": "Tenant mismatch or forbidden action",
                "details": {},
            }
        },
    )

    with pytest.raises(PermissionDeniedError):
        await client.create_execution(
            {"projectId": "proj_1", "agentId": "agent_1", "objective": "Restricted"}
        )


@respx.mock
async def test_get_execution(client: AsyncGovernanceClient) -> None:
    exec_json = {
        "id": "exec_1",
        "organizationId": "org_1",
        "projectId": "proj_1",
        "agentId": "agent_1",
        "status": "RUNNING",
        "objective": "Task 1",
        "createdAt": "2026-08-11T12:00:00Z",
        "updatedAt": "2026-08-11T12:00:00Z",
    }
    respx.get(f"{BASE_URL}/api/v1/executions/exec_1").respond(
        status_code=200, json=exec_json
    )

    result = await client.get_execution("exec_1")
    assert isinstance(result, AgentExecution)
    assert result.status == ExecutionStatus.RUNNING


@respx.mock
async def test_list_executions(client: AsyncGovernanceClient) -> None:
    respx.get(f"{BASE_URL}/api/v1/executions").respond(status_code=200, json=[])
    results = await client.list_executions(
        project_id="proj_1", status=ExecutionStatus.RUNNING
    )
    assert results == []


@respx.mock
async def test_update_execution(client: AsyncGovernanceClient) -> None:
    exec_json = {
        "id": "exec_1",
        "organizationId": "org_1",
        "projectId": "proj_1",
        "agentId": "agent_1",
        "status": "SUCCEEDED",
        "objective": "Task 1",
        "output": {"result": "ok"},
        "createdAt": "2026-08-11T12:00:00Z",
        "updatedAt": "2026-08-11T12:00:00Z",
    }
    respx.patch(f"{BASE_URL}/api/v1/executions/exec_1").respond(
        status_code=200, json=exec_json
    )

    inp = UpdateExecutionInput(
        status=ExecutionStatus.SUCCEEDED, output={"result": "ok"}
    )
    result = await client.update_execution("exec_1", inp)
    assert result.status == ExecutionStatus.SUCCEEDED
    assert result.output == {"result": "ok"}


@respx.mock
async def test_record_tool_call_fire_and_forget(
    client: AsyncGovernanceClient,
) -> None:
    trace_json = {
        "id": "trace_1",
        "organizationId": "org_1",
        "executionId": "exec_1",
        "agentId": "agent_1",
        "toolName": "shell",
        "status": "PENDING",
        "startedAt": "2026-08-11T12:00:00Z",
    }
    route = respx.post(f"{BASE_URL}/api/v1/tool-call-traces").respond(
        status_code=201, json=trace_json
    )

    inp = CreateToolCallTraceInput(
        execution_id="exec_1",
        agent_id="agent_1",
        tool_name="shell",
    )

    result = await client.record_tool_call(inp, fire_and_forget=True)
    # Must return None immediately
    assert result is None

    # Await client close to complete background tasks and verify request was sent
    await client.close()
    assert route.called


@respx.mock
async def test_record_tool_call_awaited(client: AsyncGovernanceClient) -> None:
    trace_json = {
        "id": "trace_2",
        "organizationId": "org_1",
        "executionId": "exec_1",
        "agentId": "agent_1",
        "toolName": "python_exec",
        "status": "SUCCEEDED",
        "output": {"stdout": "hello"},
        "latencyMs": 45,
        "startedAt": "2026-08-11T12:00:00Z",
    }
    respx.post(f"{BASE_URL}/api/v1/tool-call-traces").respond(
        status_code=201, json=trace_json
    )

    inp = CreateToolCallTraceInput(
        execution_id="exec_1",
        agent_id="agent_1",
        tool_name="python_exec",
    )

    result = await client.record_tool_call(inp, fire_and_forget=False)
    assert isinstance(result, ToolCallTrace)
    assert result.id == "trace_2"
    assert result.status == ToolCallStatus.SUCCEEDED
    assert result.latency_ms == 45


@respx.mock
async def test_update_tool_call(client: AsyncGovernanceClient) -> None:
    trace_json = {
        "id": "trace_2",
        "organizationId": "org_1",
        "executionId": "exec_1",
        "agentId": "agent_1",
        "toolName": "python_exec",
        "status": "FAILED",
        "error": "SyntaxError",
        "latencyMs": 12,
        "startedAt": "2026-08-11T12:00:00Z",
    }
    respx.patch(f"{BASE_URL}/api/v1/tool-call-traces/trace_2").respond(
        status_code=200, json=trace_json
    )

    inp = UpdateToolCallTraceInput(
        status=ToolCallStatus.FAILED, error="SyntaxError", latency_ms=12
    )
    result = await client.update_tool_call("trace_2", inp)
    assert result.status == ToolCallStatus.FAILED
    assert result.error == "SyntaxError"
