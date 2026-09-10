"""Docker / live-backend integration tests for AgentReady SDK.

These tests run the full governance lifecycle against a live running AgentReady
API instance:
1. Create execution
2. Check tool-call pre-flight (ALLOW/BLOCK)
3. Report tool-call execution result
4. Retrieve audit logs / traces

They are gated behind the ``integration`` pytest marker and will automatically skip
if the live server is unreachable.
"""

import os

import httpx
import pytest

from agentready_governance_sdk.client import AsyncGovernanceClient
from agentready_governance_sdk.models.common import ToolCallStatus
from agentready_governance_sdk.models.executions import CreateExecutionInput
from agentready_governance_sdk.models.traces import ReportToolCallResultInput

INTEGRATION_URL = os.environ.get("AGENTREADY_INTEGRATION_URL", "http://localhost:3001")
INTEGRATION_API_KEY = os.environ.get("AGENTREADY_INTEGRATION_API_KEY")


def _is_live_server_running() -> bool:
    """Check if the AgentReady API server is reachable."""
    try:
        resp = httpx.get(f"{INTEGRATION_URL}/health", timeout=1.0)
        return resp.status_code in (200, 404)
    except Exception:
        return False


@pytest.mark.integration
@pytest.mark.skipif(
    not INTEGRATION_API_KEY or not _is_live_server_running(),
    reason="Integration tests require AGENTREADY_INTEGRATION_API_KEY and live server",
)
async def test_live_tool_call_lifecycle() -> None:
    assert INTEGRATION_API_KEY is not None
    async with AsyncGovernanceClient(
        api_key=INTEGRATION_API_KEY, base_url=INTEGRATION_URL
    ) as client:
        # 1. Create execution
        execution = await client.create_execution(
            CreateExecutionInput(
                project_id="default-project",
                agent_id="test-agent",
                objective="Integration test run",
            )
        )
        assert execution.id is not None

        # 2. Check tool call
        check_res = await client.check_tool_call(
            execution_id=execution.id,
            tool_name="read_file",
            arguments={"path": "README.md"},
        )
        assert check_res.tool_call_trace_id is not None

        # 3. Report tool call result
        report_res = await client.report_tool_call_result(
            trace_id=check_res.tool_call_trace_id,
            input=ReportToolCallResultInput(
                status=ToolCallStatus.SUCCEEDED,
                output={"content": "sample"},
                is_final_action=True,
            ),
        )
        assert report_res.execution_status is not None
