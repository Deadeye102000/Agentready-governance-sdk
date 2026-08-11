"""Tests for wait_for_approval and observability in AsyncGovernanceClient."""

import pytest
import respx
from httpx import Response

from agentready_governance_sdk.client import AsyncGovernanceClient
from agentready_governance_sdk.exceptions import (
    ApprovalRejectedError,
    ApprovalTimeoutError,
)
from agentready_governance_sdk.models.audit import AuditLogEntry
from agentready_governance_sdk.models.common import ActorType, ExecutionStatus
from agentready_governance_sdk.models.executions import AgentExecution

BASE_URL = "http://localhost:3001"
API_KEY = "test-key"


@pytest.fixture
def client() -> AsyncGovernanceClient:
    return AsyncGovernanceClient(api_key=API_KEY, base_url=BASE_URL)


@respx.mock
async def test_wait_for_approval_approved_running(
    client: AsyncGovernanceClient,
) -> None:
    exec_waiting = {
        "id": "exec_100",
        "organizationId": "org_1",
        "projectId": "proj_1",
        "agentId": "agent_1",
        "status": "WAITING_FOR_APPROVAL",
        "objective": "Gated task",
        "createdAt": "2026-08-11T12:00:00Z",
        "updatedAt": "2026-08-11T12:00:00Z",
    }
    exec_running = {
        "id": "exec_100",
        "organizationId": "org_1",
        "projectId": "proj_1",
        "agentId": "agent_1",
        "status": "RUNNING",
        "objective": "Gated task",
        "createdAt": "2026-08-11T12:00:00Z",
        "updatedAt": "2026-08-11T12:01:00Z",
    }

    respx.get(f"{BASE_URL}/api/v1/executions/exec_100").side_effect = [
        Response(status_code=200, json=exec_waiting),
        Response(status_code=200, json=exec_running),
    ]

    result = await client.wait_for_approval(
        "exec_100", poll_interval=0.001, timeout=5.0
    )
    assert isinstance(result, AgentExecution)
    assert result.status == ExecutionStatus.RUNNING


@respx.mock
async def test_wait_for_approval_rejected(client: AsyncGovernanceClient) -> None:
    exec_waiting = {
        "id": "exec_101",
        "organizationId": "org_1",
        "projectId": "proj_1",
        "agentId": "agent_1",
        "status": "WAITING_FOR_APPROVAL",
        "objective": "Gated task",
        "createdAt": "2026-08-11T12:00:00Z",
        "updatedAt": "2026-08-11T12:00:00Z",
    }
    exec_failed = {
        "id": "exec_101",
        "organizationId": "org_1",
        "projectId": "proj_1",
        "agentId": "agent_1",
        "status": "FAILED",
        "objective": "Gated task",
        "failureReason": "REJECTED_BY_USER",
        "createdAt": "2026-08-11T12:00:00Z",
        "updatedAt": "2026-08-11T12:01:00Z",
    }

    respx.get(f"{BASE_URL}/api/v1/executions/exec_101").side_effect = [
        Response(status_code=200, json=exec_waiting),
        Response(status_code=200, json=exec_failed),
    ]

    with pytest.raises(ApprovalRejectedError) as exc_info:
        await client.wait_for_approval("exec_101", poll_interval=0.001, timeout=5.0)
    assert "exec_101" in str(exc_info.value)


@respx.mock
async def test_wait_for_approval_cancelled(client: AsyncGovernanceClient) -> None:
    exec_waiting = {
        "id": "exec_102",
        "organizationId": "org_1",
        "projectId": "proj_1",
        "agentId": "agent_1",
        "status": "WAITING_FOR_APPROVAL",
        "objective": "Gated task",
        "createdAt": "2026-08-11T12:00:00Z",
        "updatedAt": "2026-08-11T12:00:00Z",
    }
    exec_cancelled = {
        "id": "exec_102",
        "organizationId": "org_1",
        "projectId": "proj_1",
        "agentId": "agent_1",
        "status": "CANCELLED",
        "objective": "Gated task",
        "createdAt": "2026-08-11T12:00:00Z",
        "updatedAt": "2026-08-11T12:01:00Z",
    }

    respx.get(f"{BASE_URL}/api/v1/executions/exec_102").side_effect = [
        Response(status_code=200, json=exec_waiting),
        Response(status_code=200, json=exec_cancelled),
    ]

    with pytest.raises(ApprovalRejectedError):
        await client.wait_for_approval("exec_102", poll_interval=0.001, timeout=5.0)


@respx.mock
async def test_wait_for_approval_timeout(client: AsyncGovernanceClient) -> None:
    exec_waiting = {
        "id": "exec_103",
        "organizationId": "org_1",
        "projectId": "proj_1",
        "agentId": "agent_1",
        "status": "WAITING_FOR_APPROVAL",
        "objective": "Gated task",
        "createdAt": "2026-08-11T12:00:00Z",
        "updatedAt": "2026-08-11T12:00:00Z",
    }

    respx.get(f"{BASE_URL}/api/v1/executions/exec_103").respond(
        status_code=200, json=exec_waiting
    )

    with pytest.raises(ApprovalTimeoutError) as exc_info:
        await client.wait_for_approval("exec_103", poll_interval=0.001, timeout=0.005)
    assert "timed out after 0.005s" in str(exc_info.value)


@respx.mock
async def test_list_audit_logs(client: AsyncGovernanceClient) -> None:
    audit_json = [
        {
            "id": "audit_1",
            "organizationId": "org_1",
            "actorType": "USER",
            "actorUserId": "user_1",
            "action": "APPROVAL_GRANTED",
            "targetType": "ApprovalRequest",
            "targetId": "app_1",
            "metadata": {},
            "createdAt": "2026-08-11T12:00:00Z",
        }
    ]
    respx.get(f"{BASE_URL}/api/v1/audit-logs").respond(status_code=200, json=audit_json)

    logs = await client.list_audit_logs(limit=10)
    assert len(logs) == 1
    assert isinstance(logs[0], AuditLogEntry)
    assert logs[0].actor_type == ActorType.USER
    assert logs[0].action == "APPROVAL_GRANTED"


@respx.mock
async def test_get_dashboard(client: AsyncGovernanceClient) -> None:
    dash_json = {
        "totalExecutions": 42,
        "activeGates": 5,
        "pendingApprovals": 2,
    }
    respx.get(f"{BASE_URL}/api/v1/observability/dashboard").respond(
        status_code=200, json=dash_json
    )

    dashboard = await client.get_dashboard()
    assert dashboard["totalExecutions"] == 42
    assert dashboard["activeGates"] == 5
