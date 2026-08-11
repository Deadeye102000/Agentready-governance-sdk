"""Tests for synchronous GovernanceClient wrapper."""

import pytest
import respx
from httpx import Response

from agentready_governance_sdk.models.common import ExecutionStatus, FeatureFlagState
from agentready_governance_sdk.models.executions import (
    AgentExecution,
    CreateExecutionInput,
)
from agentready_governance_sdk.models.governance import FeatureFlag
from agentready_governance_sdk.models.traces import ToolCallTrace
from agentready_governance_sdk.sync_client import GovernanceClient

BASE_URL = "http://localhost:3001"
API_KEY = "test-key-sync"


@pytest.fixture
def sync_client() -> GovernanceClient:
    return GovernanceClient(api_key=API_KEY, base_url=BASE_URL)


@respx.mock
def test_sync_create_execution(sync_client: GovernanceClient) -> None:
    exec_json = {
        "id": "exec_sync_1",
        "organizationId": "org_1",
        "projectId": "proj_1",
        "agentId": "agent_1",
        "status": "QUEUED",
        "objective": "Sync execution creation",
        "createdAt": "2026-08-11T12:00:00Z",
        "updatedAt": "2026-08-11T12:00:00Z",
    }
    route = respx.post(f"{BASE_URL}/api/v1/executions").respond(
        status_code=201, json=exec_json
    )

    inp = CreateExecutionInput(
        project_id="proj_1",
        agent_id="agent_1",
        objective="Sync execution creation",
    )
    result = sync_client.create_execution(inp)
    assert route.called
    assert isinstance(result, AgentExecution)
    assert result.id == "exec_sync_1"
    assert result.status == ExecutionStatus.QUEUED


@respx.mock
def test_sync_list_feature_flags(sync_client: GovernanceClient) -> None:
    flags_json = [
        {
            "id": "flag_sync_1",
            "organizationId": "org_1",
            "capability": "db:write",
            "state": "ENABLED",
            "createdAt": "2026-08-11T12:00:00Z",
            "updatedAt": "2026-08-11T12:00:00Z",
        }
    ]
    respx.get(f"{BASE_URL}/api/v1/feature-flags").respond(
        status_code=200, json=flags_json
    )

    flags = sync_client.list_feature_flags()
    assert len(flags) == 1
    assert isinstance(flags[0], FeatureFlag)
    assert flags[0].id == "flag_sync_1"
    assert flags[0].state == FeatureFlagState.ENABLED


@respx.mock
def test_sync_wait_for_approval(sync_client: GovernanceClient) -> None:
    exec_waiting = {
        "id": "exec_sync_2",
        "organizationId": "org_1",
        "projectId": "proj_1",
        "agentId": "agent_1",
        "status": "WAITING_FOR_APPROVAL",
        "objective": "Gated task",
        "createdAt": "2026-08-11T12:00:00Z",
        "updatedAt": "2026-08-11T12:00:00Z",
    }
    exec_running = {
        "id": "exec_sync_2",
        "organizationId": "org_1",
        "projectId": "proj_1",
        "agentId": "agent_1",
        "status": "RUNNING",
        "objective": "Gated task",
        "createdAt": "2026-08-11T12:00:00Z",
        "updatedAt": "2026-08-11T12:01:00Z",
    }

    respx.get(f"{BASE_URL}/api/v1/executions/exec_sync_2").side_effect = [
        Response(status_code=200, json=exec_waiting),
        Response(status_code=200, json=exec_running),
    ]

    result = sync_client.wait_for_approval(
        "exec_sync_2", poll_interval=0.001, timeout=5.0
    )
    assert isinstance(result, AgentExecution)
    assert result.status == ExecutionStatus.RUNNING


@respx.mock
def test_sync_record_tool_call_blocks(sync_client: GovernanceClient) -> None:
    trace_json = {
        "id": "trace_sync_1",
        "organizationId": "org_1",
        "executionId": "exec_1",
        "agentId": "agent_1",
        "toolName": "shell",
        "status": "SUCCEEDED",
        "startedAt": "2026-08-11T12:00:00Z",
    }
    respx.post(f"{BASE_URL}/api/v1/tool-call-traces").respond(
        status_code=201, json=trace_json
    )

    result = sync_client.record_tool_call(
        {"executionId": "exec_1", "agentId": "agent_1", "toolName": "shell"}
    )
    assert isinstance(result, ToolCallTrace)
    assert result.id == "trace_sync_1"


def test_sync_context_manager() -> None:
    with GovernanceClient(api_key=API_KEY, base_url=BASE_URL) as client:
        assert client._async_client.api_key == API_KEY
