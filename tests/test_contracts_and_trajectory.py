"""Tests for TaskContract models and API client methods."""

import respx

from agentready_governance_sdk.client import AsyncGovernanceClient
from agentready_governance_sdk.models.contracts import (
    CreateTaskContractInput,
    ExpectedStep,
    PatchTaskContractInput,
    TaskContract,
    TrajectoryMode,
    TrajectoryPolicy,
)
from agentready_governance_sdk.sync_client import GovernanceClient

BASE_URL = "http://localhost:3001"
API_KEY = "test-key"

SAMPLE_CONTRACT_JSON = {
    "id": "contract_1",
    "organizationId": "org_1",
    "projectId": "proj_1",
    "name": "Data Export Policy",
    "objective": "Safely export reports",
    "version": 1,
    "inputs": {"reportType": "csv"},
    "successCriteria": ["report_generated"],
    "allowedTools": ["query_db", "format_csv", "upload_s3"],
    "requiredApprovals": ["upload_s3"],
    "evalSpec": {"minScore": 0.9},
    "trajectoryPolicy": {
        "mode": "STRICT_SEQUENCE",
        "expectedSteps": [
            {"tool": "query_db", "required": True},
            {"tool": "format_csv", "required": True},
            {
                "tool": "upload_s3",
                "required": True,
                "expectedGateStatus": "REQUIRE_APPROVAL",
            },
        ],
        "forbiddenTools": ["drop_table"],
        "maxToolCalls": 10,
    },
    "createdAt": "2026-08-11T12:00:00Z",
    "updatedAt": "2026-08-11T12:00:00Z",
}


def test_task_contract_model_roundtrip() -> None:
    contract = TaskContract.model_validate(SAMPLE_CONTRACT_JSON)
    assert contract.id == "contract_1"
    assert contract.organization_id == "org_1"
    assert contract.project_id == "proj_1"
    assert contract.name == "Data Export Policy"
    assert contract.version == 1
    assert contract.allowed_tools == ["query_db", "format_csv", "upload_s3"]
    assert contract.required_approvals == ["upload_s3"]
    assert contract.trajectory_policy is not None
    assert contract.trajectory_policy.mode == TrajectoryMode.STRICT_SEQUENCE
    assert len(contract.trajectory_policy.expected_steps) == 3
    assert contract.trajectory_policy.forbidden_tools == ["drop_table"]
    assert contract.trajectory_policy.max_tool_calls == 10

    # Dump and check alias preservation
    dumped = contract.model_dump(by_alias=True, mode="json")
    assert dumped["organizationId"] == "org_1"
    assert dumped["projectId"] == "proj_1"
    assert dumped["trajectoryPolicy"]["expectedSteps"][0]["tool"] == "query_db"


@respx.mock
async def test_async_task_contract_crud() -> None:
    respx.get(f"{BASE_URL}/api/v1/task-contracts").respond(
        status_code=200, json=[SAMPLE_CONTRACT_JSON]
    )
    respx.get(f"{BASE_URL}/api/v1/task-contracts/contract_1").respond(
        status_code=200, json=SAMPLE_CONTRACT_JSON
    )
    respx.post(f"{BASE_URL}/api/v1/task-contracts").respond(
        status_code=201, json=SAMPLE_CONTRACT_JSON
    )
    respx.patch(f"{BASE_URL}/api/v1/task-contracts/contract_1").respond(
        status_code=200, json=SAMPLE_CONTRACT_JSON
    )

    async with AsyncGovernanceClient(api_key=API_KEY, base_url=BASE_URL) as client:
        # List
        contracts = await client.list_task_contracts(project_id="proj_1")
        assert len(contracts) == 1
        assert contracts[0].name == "Data Export Policy"

        # Get
        contract = await client.get_task_contract("contract_1")
        assert contract.id == "contract_1"

        # Create
        create_inp = CreateTaskContractInput(
            project_id="proj_1",
            name="Data Export Policy",
            objective="Safely export reports",
            allowed_tools=["query_db"],
            trajectory_policy=TrajectoryPolicy(
                mode=TrajectoryMode.STRICT_SEQUENCE,
                expected_steps=[ExpectedStep(tool="query_db")],
            ),
        )
        created = await client.create_task_contract(create_inp)
        assert created.id == "contract_1"

        # Patch
        patch_inp = PatchTaskContractInput(name="Updated Export Policy")
        patched = await client.patch_task_contract("contract_1", patch_inp)
        assert patched.id == "contract_1"


@respx.mock
def test_sync_task_contract_crud() -> None:
    respx.get(f"{BASE_URL}/api/v1/task-contracts").respond(
        status_code=200, json=[SAMPLE_CONTRACT_JSON]
    )
    respx.get(f"{BASE_URL}/api/v1/task-contracts/contract_1").respond(
        status_code=200, json=SAMPLE_CONTRACT_JSON
    )
    respx.post(f"{BASE_URL}/api/v1/task-contracts").respond(
        status_code=201, json=SAMPLE_CONTRACT_JSON
    )
    respx.patch(f"{BASE_URL}/api/v1/task-contracts/contract_1").respond(
        status_code=200, json=SAMPLE_CONTRACT_JSON
    )

    with GovernanceClient(api_key=API_KEY, base_url=BASE_URL) as client:
        contracts = client.list_task_contracts()
        assert len(contracts) == 1

        contract = client.get_task_contract("contract_1")
        assert contract.id == "contract_1"

        created = client.create_task_contract(
            {"projectId": "proj_1", "name": "Policy", "objective": "Obj"}
        )
        assert created.id == "contract_1"

        patched = client.patch_task_contract("contract_1", {"name": "New Name"})
        assert patched.id == "contract_1"
