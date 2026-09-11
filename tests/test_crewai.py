"""Unit tests for CrewAI integration."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from agentready_governance_sdk.context import agentready_execution
from agentready_governance_sdk.exceptions import (
    ApprovalRequiredError,
    ToolBlockedError,
)
from agentready_governance_sdk.integrations.crewai import (
    AgentReadyCrewAITool,
    BaseTool,
    guard_crew_tool,
)
from agentready_governance_sdk.models.common import ToolCallDecision
from agentready_governance_sdk.models.traces import ToolCallCheckResult


def _mock_allow(trace_id: str = "tr-crew-1") -> ToolCallCheckResult:
    return ToolCallCheckResult(
        decision=ToolCallDecision.ALLOW,
        reason="Allowed by contract",
        tool_call_trace_id=trace_id,
        execution_status="RUNNING",
        consecutive_blocks=0,
    )


def _mock_block(reason: str = "Command execution forbidden") -> ToolCallCheckResult:
    return ToolCallCheckResult(
        decision=ToolCallDecision.BLOCK,
        reason=reason,
        tool_call_trace_id="tr-crew-blk",
        execution_status="RUNNING",
        consecutive_blocks=1,
    )


def _mock_approval(req_id: str = "appr-req-crew") -> ToolCallCheckResult:
    return ToolCallCheckResult(
        decision=ToolCallDecision.WAIT_FOR_APPROVAL,
        reason="Requires approval",
        tool_call_trace_id="tr-crew-appr",
        approval_request_id=req_id,
        execution_status="WAITING_FOR_APPROVAL",
        consecutive_blocks=0,
    )


class MockCrewTool(BaseTool):
    name: str = "mock_crew_tool"
    description: str = "A mock tool simulating a CrewAI tool"

    def _run(self, text: str) -> str:
        return f"Echo: {text}"

    async def _arun(self, text: str) -> str:
        return f"Async Echo: {text}"


class FailingCrewTool(BaseTool):
    name: str = "failing_crew_tool"

    def _run(self) -> None:
        raise RuntimeError("Crew tool failed catastrophically")


def test_crewai_tool_wrap_allowed():
    mock_client = MagicMock()
    mock_client.check_tool_call.return_value = _mock_allow("tr-crew-10")

    original_tool = MockCrewTool()
    guarded_tool = AgentReadyCrewAITool(
        original_tool, execution_id="exec-crew-1", client=mock_client
    )

    result = guarded_tool._run("Hello CrewAI")
    assert result == "Echo: Hello CrewAI"

    mock_client.check_tool_call.assert_called_once_with(
        execution_id="exec-crew-1",
        tool_name="mock_crew_tool",
        arguments={"text": "Hello CrewAI"},
    )
    mock_client.report_tool_result.assert_called_once()
    trace_id, payload = mock_client.report_tool_result.call_args[0]
    assert trace_id == "tr-crew-10"
    assert payload["status"] == "SUCCEEDED"
    assert payload["output"] == "Echo: Hello CrewAI"
    assert "latencyMs" in payload


def test_crewai_tool_wrap_blocked():
    mock_client = MagicMock()
    mock_client.check_tool_call.return_value = _mock_block("File delete blocked")

    original_tool = MockCrewTool()
    guarded_tool = AgentReadyCrewAITool(
        original_tool, execution_id="exec-blk", client=mock_client
    )

    with pytest.raises(ToolBlockedError) as exc_info:
        guarded_tool._run("delete /etc")

    assert "File delete blocked" in str(exc_info.value)
    assert exc_info.value.tool_name == "mock_crew_tool"
    mock_client.report_tool_result.assert_not_called()


def test_crewai_tool_wrap_approval_required():
    mock_client = MagicMock()
    mock_client.check_tool_call.return_value = _mock_approval("appr-crew-1")

    original_tool = MockCrewTool()
    guarded_tool = AgentReadyCrewAITool(
        original_tool,
        execution_id="exec-appr",
        client=mock_client,
        wait_for_approval=False,
    )

    with pytest.raises(ApprovalRequiredError) as exc_info:
        guarded_tool._run("transfer funds")

    assert exc_info.value.approval_request_id == "appr-crew-1"
    assert exc_info.value.tool_name == "mock_crew_tool"


def test_crewai_tool_wrap_failure_reporting():
    mock_client = MagicMock()
    mock_client.check_tool_call.return_value = _mock_allow("tr-fail-crew")

    tool = FailingCrewTool()
    guarded = AgentReadyCrewAITool(tool, execution_id="exec-err", client=mock_client)

    with pytest.raises(RuntimeError, match="Crew tool failed catastrophically"):
        guarded._run()

    mock_client.report_tool_result.assert_called_once()
    trace_id, payload = mock_client.report_tool_result.call_args[0]
    assert trace_id == "tr-fail-crew"
    assert payload["status"] == "FAILED"
    assert "Crew tool failed catastrophically" in payload["error"]


@pytest.mark.asyncio
async def test_crewai_tool_async_arun():
    mock_client = MagicMock()
    mock_client.check_tool_call = AsyncMock(return_value=_mock_allow("tr-crew-async"))
    mock_client.report_tool_result = AsyncMock()

    original_tool = MockCrewTool()
    guarded = AgentReadyCrewAITool(
        original_tool, execution_id="exec-async-crew", client=mock_client
    )

    result = await guarded._arun("Async test")
    assert result == "Async Echo: Async test"

    mock_client.check_tool_call.assert_awaited_once()
    mock_client.report_tool_result.assert_awaited_once()
    trace_id, payload = mock_client.report_tool_result.call_args[0]
    assert trace_id == "tr-crew-async"
    assert payload["status"] == "SUCCEEDED"


def test_guard_crew_tool_decorator_on_tool_object():
    mock_client = MagicMock()
    mock_client.check_tool_call.return_value = _mock_allow("tr-dec-tool")

    original_tool = MockCrewTool()
    guarded = guard_crew_tool(
        original_tool, execution_id="exec-dec", client=mock_client
    )

    res = guarded._run("Testing decorator")
    assert res == "Echo: Testing decorator"
    mock_client.report_tool_result.assert_called_once()


def test_guard_crew_tool_decorator_on_function():
    mock_client = MagicMock()
    mock_client.check_tool_call.return_value = _mock_allow("tr-fn-tool")

    @guard_crew_tool(tool_name="summarize", client=mock_client)
    def summarize(text: str) -> str:
        return f"Summary: {text[:5]}"

    with agentready_execution("exec-ctx", "crew_agent"):
        res = summarize("abcdefg")

    assert res == "Summary: abcde"
    mock_client.check_tool_call.assert_called_once_with(
        execution_id="exec-ctx",
        tool_name="summarize",
        arguments={"text": "abcdefg"},
    )
    mock_client.report_tool_result.assert_called_once()


@pytest.mark.asyncio
async def test_guard_crew_tool_decorator_async_function():
    mock_client = MagicMock()
    mock_client.check_tool_call = AsyncMock(return_value=_mock_allow("tr-async-fn"))
    mock_client.report_tool_result = AsyncMock()

    @guard_crew_tool(tool_name="async_search", client=mock_client)
    async def async_search(q: str) -> str:
        return f"Found: {q}"

    with agentready_execution("exec-async-dec", "researcher"):
        res = await async_search("ai governance")

    assert res == "Found: ai governance"
    mock_client.check_tool_call.assert_awaited_once()
    mock_client.report_tool_result.assert_awaited_once()
