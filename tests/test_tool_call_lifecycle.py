"""Tests for pre-flight tool-call check and reporting lifecycle."""

import json
import uuid

import pytest
import respx

from agentready_governance_sdk.client import AsyncGovernanceClient
from agentready_governance_sdk.exceptions import (
    ConcurrentToolCallDisallowedError,
    IdempotencyKeyMismatchError,
)
from agentready_governance_sdk.models.common import ToolCallDecision
from agentready_governance_sdk.models.traces import (
    ReportToolCallResultInput,
    ToolCallCheckResult,
    ToolCallResultResponse,
)
from agentready_governance_sdk.sync_client import GovernanceClient

BASE_URL = "http://localhost:3001"
API_KEY = "test-key"


@respx.mock
async def test_check_tool_call_allow() -> None:
    result_json = {
        "decision": "ALLOW",
        "reason": "Tool allowed by policy",
        "toolCallTraceId": "trace_123",
        "executionStatus": "RUNNING",
        "consecutiveBlocks": 0,
    }
    route = respx.post(f"{BASE_URL}/api/v1/executions/exec_1/tool-calls/check").respond(
        status_code=200, json=result_json
    )

    async with AsyncGovernanceClient(api_key=API_KEY, base_url=BASE_URL) as client:
        res = await client.check_tool_call(
            execution_id="exec_1",
            tool_name="web_search",
            arguments={"query": "python"},
        )
        assert isinstance(res, ToolCallCheckResult)
        assert res.decision == ToolCallDecision.ALLOW
        assert res.tool_call_trace_id == "trace_123"
        assert res.consecutive_blocks == 0

        # Assert an auto-generated idempotency key was sent
        payload = json.loads(route.calls.last.request.content)
        assert "idempotencyKey" in payload
        # Validate it's a valid UUID
        uuid_obj = uuid.UUID(payload["idempotencyKey"])
        assert str(uuid_obj) == payload["idempotencyKey"]


@respx.mock
async def test_check_tool_call_block_and_wait_for_approval() -> None:
    block_json = {
        "decision": "BLOCK",
        "reason": "Forbidden tool",
        "toolCallTraceId": "trace_block",
        "executionStatus": "RUNNING",
        "consecutiveBlocks": 1,
    }
    approval_json = {
        "decision": "WAIT_FOR_APPROVAL",
        "reason": "High risk action requires approval",
        "toolCallTraceId": "trace_approval",
        "approvalRequestId": "req_123",
        "executionStatus": "WAITING_FOR_APPROVAL",
        "consecutiveBlocks": 0,
    }
    respx.post(f"{BASE_URL}/api/v1/executions/exec_1/tool-calls/check").side_effect = [
        respx.MockResponse(status_code=200, json=block_json),
        respx.MockResponse(status_code=200, json=approval_json),
    ]

    async with AsyncGovernanceClient(api_key=API_KEY, base_url=BASE_URL) as client:
        res_block = await client.check_tool_call(
            execution_id="exec_1",
            tool_name="drop_db",
            idempotency_key="idemp_1",
        )
        assert res_block.decision == ToolCallDecision.BLOCK
        assert res_block.consecutive_blocks == 1

        res_approval = await client.check_tool_call(
            execution_id="exec_1",
            tool_name="deploy_prod",
            idempotency_key="idemp_2",
        )
        assert res_approval.decision == ToolCallDecision.WAIT_FOR_APPROVAL
        assert res_approval.approval_request_id == "req_123"


@respx.mock
async def test_check_tool_call_concurrent_disallowed_error() -> None:
    respx.post(f"{BASE_URL}/api/v1/executions/exec_1/tool-calls/check").respond(
        status_code=409,
        json={
            "error": {
                "code": "CONCURRENT_TOOL_CALL_DISALLOWED",
                "message": "Another tool call is currently in progress",
                "details": {},
            }
        },
    )

    async with AsyncGovernanceClient(api_key=API_KEY, base_url=BASE_URL) as client:
        with pytest.raises(ConcurrentToolCallDisallowedError) as exc_info:
            await client.check_tool_call(
                execution_id="exec_1",
                tool_name="heavy_job",
            )
        assert exc_info.value.code == "CONCURRENT_TOOL_CALL_DISALLOWED"
        assert exc_info.value.status_code == 409


@respx.mock
async def test_check_tool_call_idempotency_key_mismatch_error() -> None:
    respx.post(f"{BASE_URL}/api/v1/executions/exec_1/tool-calls/check").respond(
        status_code=409,
        json={
            "error": {
                "code": "IDEMPOTENCY_KEY_MISMATCH",
                "message": (
                    "Payload does not match original request for this idempotency key"
                ),
                "details": {},
            }
        },
    )

    async with AsyncGovernanceClient(api_key=API_KEY, base_url=BASE_URL) as client:
        with pytest.raises(IdempotencyKeyMismatchError) as exc_info:
            await client.check_tool_call(
                execution_id="exec_1",
                tool_name="tool_a",
                idempotency_key="reused_key",
            )
        assert exc_info.value.code == "IDEMPOTENCY_KEY_MISMATCH"
        assert exc_info.value.status_code == 409


@respx.mock
async def test_report_tool_call_result_success() -> None:
    report_json = {
        "toolCallTraceId": "trace_123",
        "status": "SUCCEEDED",
        "executionId": "exec_1",
        "executionStatus": "SUCCEEDED",
        "completedAt": "2026-08-11T12:00:00Z",
    }
    route = respx.post(f"{BASE_URL}/api/v1/tool-calls/trace_123/result").respond(
        status_code=200, json=report_json
    )

    async with AsyncGovernanceClient(api_key=API_KEY, base_url=BASE_URL) as client:
        inp = ReportToolCallResultInput(
            status="SUCCEEDED",
            output={"data": "done"},
            is_final_action=True,
        )
        res = await client.report_tool_call_result("trace_123", inp)
        assert isinstance(res, ToolCallResultResponse)
        assert res.status == "SUCCEEDED"
        assert res.execution_status == "SUCCEEDED"
        assert res.execution_id == "exec_1"

        payload = json.loads(route.calls.last.request.content)
        assert payload["status"] == "SUCCEEDED"
        assert payload["isFinalAction"] is True


@respx.mock
def test_sync_tool_call_lifecycle() -> None:
    check_json = {
        "decision": "ALLOW",
        "reason": "OK",
        "toolCallTraceId": "trace_sync",
        "executionStatus": "RUNNING",
        "consecutiveBlocks": 0,
    }
    report_json = {
        "toolCallTraceId": "trace_sync",
        "status": "SUCCEEDED",
        "executionId": "exec_1",
        "executionStatus": "RUNNING",
        "completedAt": "2026-08-11T12:00:00Z",
    }
    respx.post(f"{BASE_URL}/api/v1/executions/exec_1/tool-calls/check").respond(
        status_code=200, json=check_json
    )
    respx.post(f"{BASE_URL}/api/v1/tool-calls/trace_sync/result").respond(
        status_code=200, json=report_json
    )

    with GovernanceClient(api_key=API_KEY, base_url=BASE_URL) as client:
        check = client.check_tool_call(
            execution_id="exec_1",
            tool_name="search",
        )
        assert check.decision == ToolCallDecision.ALLOW
        assert check.tool_call_trace_id == "trace_sync"

        report = client.report_tool_call_result(
            trace_id="trace_sync",
            input={"status": "SUCCEEDED", "output": {"results": []}},
        )
        assert report.status == "SUCCEEDED"
