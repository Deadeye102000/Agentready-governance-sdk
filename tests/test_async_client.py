"""Tests for AsyncGovernanceClient using respx mocks."""

import pytest
import respx

from agentready_governance_sdk.client import AsyncGovernanceClient
from agentready_governance_sdk.exceptions import (
    AuthenticationError,
    ConflictError,
    PermissionDeniedError,
    ValidationError,
)
from agentready_governance_sdk.models.common import ApprovalGateMode, FeatureFlagState
from agentready_governance_sdk.models.governance import (
    ApprovalGate,
    FeatureFlag,
    UpsertAgentFeatureFlagInput,
    UpsertApprovalGateInput,
)

BASE_URL = "http://localhost:3001"
API_KEY = "test-api-key-123"


@pytest.fixture
def client() -> AsyncGovernanceClient:
    return AsyncGovernanceClient(api_key=API_KEY, base_url=BASE_URL)


@respx.mock
async def test_auth_header_sent(client: AsyncGovernanceClient) -> None:
    route = respx.get(f"{BASE_URL}/api/v1/feature-flags").respond(
        status_code=200, json=[]
    )
    await client.list_feature_flags()

    assert route.called
    request = route.calls.last.request
    assert request.headers["Authorization"] == f"Bearer {API_KEY}"


@respx.mock
async def test_list_feature_flags_success(client: AsyncGovernanceClient) -> None:
    flags_json = [
        {
            "id": "flag_1",
            "organizationId": "org_1",
            "agentId": "agent_1",
            "capability": "db:write",
            "state": "ENABLED",
            "description": "Allow DB write",
            "createdAt": "2026-08-11T12:00:00Z",
            "updatedAt": "2026-08-11T12:00:00Z",
        }
    ]
    respx.get(f"{BASE_URL}/api/v1/feature-flags").respond(
        status_code=200, json=flags_json
    )

    flags = await client.list_feature_flags()
    assert len(flags) == 1
    assert isinstance(flags[0], FeatureFlag)
    assert flags[0].id == "flag_1"
    assert flags[0].capability == "db:write"
    assert flags[0].state == FeatureFlagState.ENABLED


@respx.mock
async def test_list_feature_flags_error_mapping(
    client: AsyncGovernanceClient,
) -> None:
    respx.get(f"{BASE_URL}/api/v1/feature-flags").respond(
        status_code=401,
        json={
            "error": {
                "code": "UNAUTHENTICATED",
                "message": "Invalid API key",
                "details": {},
            }
        },
    )

    with pytest.raises(AuthenticationError) as exc_info:
        await client.list_feature_flags()
    assert exc_info.value.code == "UNAUTHENTICATED"
    assert exc_info.value.status_code == 401


@respx.mock
async def test_upsert_feature_flag_success(client: AsyncGovernanceClient) -> None:
    flag_json = {
        "id": "flag_2",
        "organizationId": "org_1",
        "agentId": "agent_1",
        "capability": "fs:write",
        "state": "DISABLED",
        "description": "Block file write",
        "createdAt": "2026-08-11T12:00:00Z",
        "updatedAt": "2026-08-11T12:00:00Z",
    }
    route = respx.put(f"{BASE_URL}/api/v1/feature-flags").respond(
        status_code=200, json=flag_json
    )

    inp = UpsertAgentFeatureFlagInput(
        capability="fs:write",
        state=FeatureFlagState.DISABLED,
        agent_id="agent_1",
    )
    result = await client.upsert_feature_flag(inp)
    assert isinstance(result, FeatureFlag)
    assert result.capability == "fs:write"
    assert route.calls.last.request.content != b""


@respx.mock
async def test_upsert_feature_flag_error(client: AsyncGovernanceClient) -> None:
    respx.put(f"{BASE_URL}/api/v1/feature-flags").respond(
        status_code=403,
        json={
            "error": {
                "code": "PERMISSION_DENIED",
                "message": "Admin required",
                "details": {},
            }
        },
    )

    with pytest.raises(PermissionDeniedError):
        await client.upsert_feature_flag(
            {"capability": "fs:write", "state": "DISABLED"}
        )


@respx.mock
async def test_toggle_feature_flag_success(client: AsyncGovernanceClient) -> None:
    flag_json = {
        "id": "flag_3",
        "organizationId": "org_1",
        "agentId": "agent_1",
        "capability": "network:outbound",
        "state": "ENABLED",
        "createdAt": "2026-08-11T12:00:00Z",
        "updatedAt": "2026-08-11T12:00:00Z",
    }
    respx.post(f"{BASE_URL}/api/v1/feature-flags/toggle").respond(
        status_code=200, json=flag_json
    )

    result = await client.toggle_feature_flag(
        capability="network:outbound",
        state=FeatureFlagState.ENABLED,
        agent_id="agent_1",
    )
    assert isinstance(result, FeatureFlag)
    assert result.state == FeatureFlagState.ENABLED


@respx.mock
async def test_toggle_feature_flag_validation_error(
    client: AsyncGovernanceClient,
) -> None:
    respx.post(f"{BASE_URL}/api/v1/feature-flags/toggle").respond(
        status_code=400,
        json={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid capability",
                "details": {},
            }
        },
    )

    with pytest.raises(ValidationError):
        await client.toggle_feature_flag(capability="", state="ENABLED")


@respx.mock
async def test_list_approval_gates_success(client: AsyncGovernanceClient) -> None:
    gates_json = [
        {
            "id": "gate_1",
            "organizationId": "org_1",
            "capability": "deploy:prod",
            "mode": "REQUIRE_APPROVAL",
            "riskLevel": 80,
            "enabled": True,
            "createdAt": "2026-08-11T12:00:00Z",
            "updatedAt": "2026-08-11T12:00:00Z",
        }
    ]
    respx.get(f"{BASE_URL}/api/v1/approval-gates").respond(
        status_code=200, json=gates_json
    )

    gates = await client.list_approval_gates()
    assert len(gates) == 1
    assert isinstance(gates[0], ApprovalGate)
    assert gates[0].capability == "deploy:prod"
    assert gates[0].mode == ApprovalGateMode.REQUIRE_APPROVAL


@respx.mock
async def test_upsert_approval_gate_success(client: AsyncGovernanceClient) -> None:
    gate_json = {
        "id": "gate_1",
        "organizationId": "org_1",
        "capability": "deploy:prod",
        "mode": "REQUIRE_APPROVAL",
        "riskLevel": 80,
        "enabled": True,
        "createdAt": "2026-08-11T12:00:00Z",
        "updatedAt": "2026-08-11T12:00:00Z",
    }
    respx.put(f"{BASE_URL}/api/v1/approval-gates").respond(
        status_code=200, json=gate_json
    )

    inp = UpsertApprovalGateInput(
        capability="deploy:prod",
        mode=ApprovalGateMode.REQUIRE_APPROVAL,
        risk_level=80,
    )
    result = await client.upsert_approval_gate(inp)
    assert isinstance(result, ApprovalGate)
    assert result.risk_level == 80


@respx.mock
async def test_upsert_approval_gate_conflict_error(
    client: AsyncGovernanceClient,
) -> None:
    respx.put(f"{BASE_URL}/api/v1/approval-gates").respond(
        status_code=409,
        json={
            "error": {
                "code": "CONFLICT",
                "message": "Gate capability conflict",
                "details": {},
            }
        },
    )

    with pytest.raises(ConflictError):
        await client.upsert_approval_gate(
            {"capability": "deploy:prod", "mode": "BLOCKED"}
        )


async def test_async_context_manager() -> None:
    async with AsyncGovernanceClient(api_key=API_KEY, base_url=BASE_URL) as client:
        assert client.api_key == API_KEY
