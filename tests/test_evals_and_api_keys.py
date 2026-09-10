"""Tests for Evals, API Keys, Approval Requests, and MCP Servers."""

import respx

from agentready_governance_sdk.client import AsyncGovernanceClient
from agentready_governance_sdk.models.api_keys import (
    ApiKey,
    CreateApiKeyInput,
    CreateApiKeyResponse,
)
from agentready_governance_sdk.models.common import (
    ApiKeyScope,
    ApprovalStatus,
    EvalRunStatus,
)
from agentready_governance_sdk.models.evals import (
    CreateEvalCaseInput,
    CreateEvalRunInput,
    EvalCase,
    EvalRun,
    RegressionReport,
)
from agentready_governance_sdk.models.governance import (
    ApprovalRequest,
    McpServerRegistration,
    ReviewApprovalRequestInput,
)
from agentready_governance_sdk.sync_client import GovernanceClient

BASE_URL = "http://localhost:3001"
API_KEY = "test-key"


@respx.mock
async def test_eval_case_and_run_lifecycle() -> None:
    eval_case_json = {
        "id": "case_1",
        "organizationId": "org_1",
        "taskContractId": "contract_1",
        "name": "Refund Happy Path",
        "description": "Standard refund test case",
        "input": {"amount": 100},
        "expectedStatus": "SUCCEEDED",
        "createdAt": "2026-08-11T12:00:00Z",
        "updatedAt": "2026-08-11T12:00:00Z",
    }
    eval_run_json = {
        "id": "run_1",
        "organizationId": "org_1",
        "projectId": "proj_1",
        "evalCaseId": "case_1",
        "name": "Refund Eval Run",
        "status": "PASSED",
        "score": 1.0,
        "createdAt": "2026-08-11T12:00:00Z",
        "updatedAt": "2026-08-11T12:00:00Z",
    }
    regression_json = {
        "previousScore": 0.95,
        "currentScore": 0.80,
        "delta": -0.15,
        "newlyFailing": [{"evalCaseId": "case_1"}],
        "newlyPassing": [],
    }

    respx.get(f"{BASE_URL}/api/v1/eval-cases").respond(
        status_code=200, json=[eval_case_json]
    )
    respx.post(f"{BASE_URL}/api/v1/eval-cases").respond(
        status_code=201, json=eval_case_json
    )
    respx.post(f"{BASE_URL}/api/v1/eval-cases/case_1/run").respond(
        status_code=200, json=eval_run_json
    )
    respx.get(f"{BASE_URL}/api/v1/eval-runs").respond(
        status_code=200, json=[eval_run_json]
    )
    respx.post(f"{BASE_URL}/api/v1/eval-runs").respond(
        status_code=201, json=eval_run_json
    )
    respx.post(f"{BASE_URL}/api/v1/eval-suites/run").respond(
        status_code=200, json=[eval_run_json]
    )
    respx.get(f"{BASE_URL}/api/v1/eval-runs/regression").respond(
        status_code=200, json=regression_json
    )

    async with AsyncGovernanceClient(api_key=API_KEY, base_url=BASE_URL) as client:
        # Cases
        cases = await client.list_eval_cases(task_contract_id="contract_1")
        assert len(cases) == 1
        assert isinstance(cases[0], EvalCase)
        assert cases[0].name == "Refund Happy Path"

        new_case = await client.create_eval_case(
            CreateEvalCaseInput(
                task_contract_id="contract_1",
                name="Refund Happy Path",
                input={"amount": 100},
            )
        )
        assert new_case.id == "case_1"

        run_from_case = await client.run_eval_case("case_1")
        assert isinstance(run_from_case, EvalRun)
        assert run_from_case.status == EvalRunStatus.PASSED

        # Runs
        runs = await client.list_eval_runs(project_id="proj_1")
        assert len(runs) == 1
        assert runs[0].score == 1.0

        created_run = await client.create_eval_run(
            CreateEvalRunInput(
                project_id="proj_1",
                name="Refund Eval Run",
                eval_case_id="case_1",
            )
        )
        assert created_run.id == "run_1"

        suite_runs = await client.run_eval_suite(task_contract_id="contract_1")
        assert len(suite_runs) == 1

        reg_report = await client.get_regression_report(contract_id="contract_1")
        assert isinstance(reg_report, RegressionReport)
        assert reg_report.delta == -0.15
        assert len(reg_report.newly_failing) == 1


@respx.mock
async def test_api_keys_lifecycle() -> None:
    api_key_json = {
        "id": "key_1",
        "organizationId": "org_1",
        "name": "CI Bot Key",
        "keyPrefix": "ar_live_123456",
        "scopes": ["agent_execution:write", "governance:read"],
        "createdAt": "2026-08-11T12:00:00Z",
        "updatedAt": "2026-08-11T12:00:00Z",
    }
    create_resp_json = {
        "apiKeyRecord": api_key_json,
        "rawKey": "ak_live_secret12345",
    }
    revoked_key_json = {**api_key_json, "revokedAt": "2026-08-11T13:00:00Z"}

    respx.get(f"{BASE_URL}/api/v1/api-keys").respond(
        status_code=200, json=[api_key_json]
    )
    respx.post(f"{BASE_URL}/api/v1/api-keys").respond(
        status_code=201, json=create_resp_json
    )
    respx.delete(f"{BASE_URL}/api/v1/api-keys/key_1").respond(
        status_code=200, json=revoked_key_json
    )

    async with AsyncGovernanceClient(api_key=API_KEY, base_url=BASE_URL) as client:
        keys = await client.list_api_keys()
        assert len(keys) == 1
        assert isinstance(keys[0], ApiKey)
        assert keys[0].name == "CI Bot Key"
        assert keys[0].scopes == [
            ApiKeyScope.AGENT_EXECUTION_WRITE,
            ApiKeyScope.GOVERNANCE_READ,
        ]

        created = await client.create_api_key(
            CreateApiKeyInput(
                name="CI Bot Key",
                scopes=[ApiKeyScope.AGENT_EXECUTION_WRITE],
            )
        )
        assert isinstance(created, CreateApiKeyResponse)
        assert created.raw_key == "ak_live_secret12345"
        assert created.api_key_record.id == "key_1"

        revoked = await client.revoke_api_key("key_1")
        assert isinstance(revoked, ApiKey)
        assert revoked.is_active is False


@respx.mock
async def test_approval_requests_and_mcp_servers() -> None:
    approval_json = {
        "id": "req_1",
        "organizationId": "org_1",
        "agentId": "agent_1",
        "requestedAction": "db:drop",
        "reason": "Dangerous migration",
        "capability": "db:drop",
        "status": "PENDING",
        "riskLevel": 90,
        "createdAt": "2026-08-11T12:00:00Z",
        "updatedAt": "2026-08-11T12:00:00Z",
    }
    reviewed_json = {**approval_json, "status": "APPROVED"}

    mcp_json = {
        "id": "mcp_1",
        "organizationId": "org_1",
        "name": "Filesystem MCP",
        "serverUrl": "http://localhost:8080/mcp",
        "transportType": "sse",
        "status": "ACTIVE",
        "createdAt": "2026-08-11T12:00:00Z",
        "updatedAt": "2026-08-11T12:00:00Z",
    }

    respx.get(f"{BASE_URL}/api/v1/approval-requests").respond(
        status_code=200, json=[approval_json]
    )
    respx.post(f"{BASE_URL}/api/v1/approval-requests/req_1/review").respond(
        status_code=200, json=reviewed_json
    )
    respx.get(f"{BASE_URL}/api/v1/mcp-servers").respond(
        status_code=200, json=[mcp_json]
    )

    async with AsyncGovernanceClient(api_key=API_KEY, base_url=BASE_URL) as client:
        # Approvals
        requests = await client.list_approval_requests()
        assert len(requests) == 1
        assert isinstance(requests[0], ApprovalRequest)
        assert requests[0].status == ApprovalStatus.PENDING

        reviewed = await client.review_approval_request(
            "req_1",
            ReviewApprovalRequestInput(status=ApprovalStatus.APPROVED),
        )
        assert reviewed.status == ApprovalStatus.APPROVED

        # MCP servers
        servers = await client.list_mcp_servers()
        assert len(servers) == 1
        assert isinstance(servers[0], McpServerRegistration)
        assert servers[0].name == "Filesystem MCP"


@respx.mock
def test_sync_evals_and_api_keys() -> None:
    api_key_json = {
        "id": "key_sync",
        "organizationId": "org_1",
        "name": "Sync Key",
        "keyPrefix": "ar_live_sync12",
        "scopes": ["audit:read"],
        "createdAt": "2026-08-11T12:00:00Z",
        "updatedAt": "2026-08-11T12:00:00Z",
    }
    mcp_json = {
        "id": "mcp_sync",
        "organizationId": "org_1",
        "name": "Sync MCP",
        "serverUrl": "http://localhost:8080/mcp",
        "transportType": "stdio",
        "status": "ACTIVE",
        "createdAt": "2026-08-11T12:00:00Z",
        "updatedAt": "2026-08-11T12:00:00Z",
    }

    respx.get(f"{BASE_URL}/api/v1/api-keys").respond(
        status_code=200, json=[api_key_json]
    )
    respx.get(f"{BASE_URL}/api/v1/mcp-servers").respond(
        status_code=200, json=[mcp_json]
    )

    with GovernanceClient(api_key=API_KEY, base_url=BASE_URL) as client:
        keys = client.list_api_keys()
        assert len(keys) == 1
        assert keys[0].id == "key_sync"

        servers = client.list_mcp_servers()
        assert len(servers) == 1
        assert servers[0].id == "mcp_sync"
