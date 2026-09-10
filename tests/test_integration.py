"""Live-backend integration tests for AgentReady SDK.

Runs the full governance lifecycle and contract schema validation against a live
running AgentReady API instance:
1. Create execution in project
2. Check tool-call pre-flight (ALLOW/BLOCK)
3. Report tool-call execution result
4. Fetch task contract and validate canonical TrajectoryPolicy schema fields
5. Evaluate compliant and adversarial trajectories against the live contract policy

These tests are gated behind the ``integration`` pytest marker and will skip if
the live server is unreachable or if AGENTREADY_INTEGRATION_API_KEY is not set.
No hardcoded credentials or fallback keys are permitted in test code.
"""

import os
from typing import AsyncGenerator

import httpx
import pytest

from agentready_governance_sdk.client import AsyncGovernanceClient
from agentready_governance_sdk.evaluator import evaluate_trajectory_traces
from agentready_governance_sdk.models.common import ToolCallStatus
from agentready_governance_sdk.models.contracts import TrajectoryMode
from agentready_governance_sdk.models.executions import CreateExecutionInput
from agentready_governance_sdk.models.traces import ReportToolCallResultInput

INTEGRATION_URL = os.environ.get("AGENTREADY_INTEGRATION_URL", "http://localhost:3001")
INTEGRATION_API_KEY = os.environ.get("AGENTREADY_INTEGRATION_API_KEY")


def _is_live_server_running() -> bool:
    """Check if the AgentReady API server is reachable."""
    try:
        resp = httpx.get(f"{INTEGRATION_URL}/health", timeout=2.0)
        return resp.status_code == 200
    except Exception:
        return False


def _check_integration_prerequisites() -> None:
    """Ensure integration environment requirements are met or skip with instructions."""
    if not INTEGRATION_API_KEY:
        pytest.skip(
            "Integration tests require AGENTREADY_INTEGRATION_API_KEY environment "
            "variable to be set. Set a valid API key (e.g. export "
            "AGENTREADY_INTEGRATION_API_KEY='<key>') to run against a live server."
        )
    if not _is_live_server_running():
        pytest.skip(
            f"Live AgentReady server at {INTEGRATION_URL} is unreachable. "
            "Ensure the API service is running and healthy."
        )


@pytest.fixture
async def live_client() -> AsyncGenerator[AsyncGovernanceClient, None]:
    """Yield an authenticated client connected to the live test server."""
    _check_integration_prerequisites()
    assert INTEGRATION_API_KEY is not None
    async with AsyncGovernanceClient(
        api_key=INTEGRATION_API_KEY,
        base_url=INTEGRATION_URL,
    ) as client:
        yield client


@pytest.mark.integration
async def test_live_tool_call_lifecycle(live_client: AsyncGovernanceClient) -> None:
    """Verify complete tool-call lifecycle against the live backend."""
    # 1. Create execution
    execution = await live_client.create_execution(
        CreateExecutionInput(
            project_id="demo-project",
            agent_id="demo-agent-identity",
            objective="Integration test execution run",
        )
    )
    assert execution.id is not None
    assert execution.status is not None

    # 2. Check tool call
    check_res = await live_client.check_tool_call(
        execution_id=execution.id,
        tool_name="knowledge.search",
        arguments={"query": "onboarding steps"},
    )
    assert check_res.tool_call_trace_id is not None
    assert check_res.decision is not None

    # 3. Report tool call result
    report_res = await live_client.report_tool_call_result(
        trace_id=check_res.tool_call_trace_id,
        input=ReportToolCallResultInput(
            status=ToolCallStatus.SUCCEEDED,
            output={"results": ["step 1", "step 2"]},
            is_final_action=True,
        ),
    )
    assert report_res.execution_status is not None


@pytest.mark.integration
async def test_live_contract_canonical_schema_and_trajectory(
    live_client: AsyncGovernanceClient,
) -> None:
    """Fetch live contract, validate canonical schema, and evaluate trajectories."""
    # 1. Fetch the fintech refund governance contract
    contract = await live_client.get_task_contract("contract_fintech_refund_v1")
    assert contract.id == "contract_fintech_refund_v1"
    assert contract.name == "Customer Support Refund Governance"
    assert contract.trajectory_policy is not None

    policy = contract.trajectory_policy

    # 2. Assert resolved canonical schema types and exact field values
    assert isinstance(policy.mode, TrajectoryMode)
    assert policy.mode == TrajectoryMode.STRICT_SEQUENCE
    assert policy.max_tool_calls == 4
    assert set(policy.forbidden_tools) == {
        "delete_customer_record",
        "drop_database",
        "export_all_credentials",
    }
    assert len(policy.expected_steps) == 3

    step0 = policy.expected_steps[0]
    assert step0.tool == "get_transaction"
    assert step0.required is True

    step1 = policy.expected_steps[1]
    assert step1.tool == "check_refund_eligibility"
    assert step1.required is True

    step2 = policy.expected_steps[2]
    assert step2.tool == "issue_refund"
    assert step2.required is True
    assert step2.expected_gate_status == "REQUIRE_APPROVAL"

    # 3. Offline evaluation: Golden path trajectory conforming to policy
    golden_traces = [
        {"tool_name": "get_transaction", "step_index": 0},
        {"tool_name": "check_refund_eligibility", "step_index": 1},
        {
            "tool_name": "issue_refund",
            "step_index": 2,
            "gate_status": "REQUIRE_APPROVAL",
        },
    ]
    golden_result = evaluate_trajectory_traces(golden_traces, policy)
    assert golden_result.passed is True
    assert golden_result.score == 1.0
    assert golden_result.matched_steps == 3
    assert golden_result.total_expected == 3
    assert len(golden_result.violations) == 0

    # 4. Offline evaluation: Adversarial trajectory triggering forbidden tool violation
    adversarial_traces = [
        {"tool_name": "get_transaction", "step_index": 0},
        {"tool_name": "delete_customer_record", "step_index": 1},
    ]
    adversarial_result = evaluate_trajectory_traces(adversarial_traces, policy)
    assert adversarial_result.passed is False
    assert any(
        "delete_customer_record" in violation
        for violation in adversarial_result.violations
    )
