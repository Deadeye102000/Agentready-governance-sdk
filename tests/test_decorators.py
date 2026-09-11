"""Tests for @guard_tool decorator and context management."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from agentready_governance_sdk.context import (
    agentready_execution,
    get_current_agent_id,
    get_current_delegation_chain,
    get_current_execution_id,
    set_current_execution,
)
from agentready_governance_sdk.decorators import guard_tool
from agentready_governance_sdk.exceptions import (
    AgentReadyError,
    ApprovalRequiredError,
    ToolBlockedError,
)
from agentready_governance_sdk.models.common import ToolCallDecision
from agentready_governance_sdk.models.traces import ToolCallCheckResult


def _mock_allow_result(trace_id: str = "trace-123") -> ToolCallCheckResult:
    return ToolCallCheckResult(
        decision=ToolCallDecision.ALLOW,
        reason="Allowed by default contract",
        tool_call_trace_id=trace_id,
        execution_status="RUNNING",
        consecutive_blocks=0,
    )


def _mock_block_result(
    reason: str = "Forbidden tool", trace_id: str = "trace-blk"
) -> ToolCallCheckResult:
    return ToolCallCheckResult(
        decision=ToolCallDecision.BLOCK,
        reason=reason,
        tool_call_trace_id=trace_id,
        execution_status="RUNNING",
        consecutive_blocks=1,
    )


def _mock_approval_result(
    request_id: str = "req-appr-999", trace_id: str = "trace-appr"
) -> ToolCallCheckResult:
    return ToolCallCheckResult(
        decision=ToolCallDecision.WAIT_FOR_APPROVAL,
        reason="Requires human approval",
        tool_call_trace_id=trace_id,
        approval_request_id=request_id,
        execution_status="WAITING_FOR_APPROVAL",
        consecutive_blocks=0,
    )


def test_contextvars_management():
    assert get_current_execution_id() is None
    assert get_current_agent_id() is None
    assert get_current_delegation_chain() == []

    with agentready_execution("exec-100", "supervisor"):
        assert get_current_execution_id() == "exec-100"
        assert get_current_agent_id() == "supervisor"
        assert get_current_delegation_chain() == ["supervisor"]

        with agentready_execution("exec-100", "researcher"):
            assert get_current_agent_id() == "researcher"
            assert get_current_delegation_chain() == ["supervisor", "researcher"]

        assert get_current_agent_id() == "supervisor"
        assert get_current_delegation_chain() == ["supervisor"]

    assert get_current_execution_id() is None
    assert get_current_agent_id() is None
    assert get_current_delegation_chain() == []


@pytest.mark.asyncio
async def test_async_contextvars_management():
    async with agentready_execution("exec-async", "agent-a"):
        assert get_current_execution_id() == "exec-async"
        assert get_current_agent_id() == "agent-a"
        assert get_current_delegation_chain() == ["agent-a"]


def test_set_current_execution_explicit():
    tokens = set_current_execution("exec-exp", "agent-x", delegation_chain=["a", "b"])
    try:
        assert get_current_execution_id() == "exec-exp"
        assert get_current_agent_id() == "agent-x"
        assert get_current_delegation_chain() == ["a", "b"]
    finally:
        tok_exec, tok_agent, tok_chain, _ = tokens
        from agentready_governance_sdk.context import (
            _CURRENT_AGENT_ID,
            _CURRENT_DELEGATION_CHAIN,
            _CURRENT_EXECUTION_ID,
        )

        _CURRENT_EXECUTION_ID.reset(tok_exec)
        _CURRENT_AGENT_ID.reset(tok_agent)
        _CURRENT_DELEGATION_CHAIN.reset(tok_chain)


def test_guard_tool_sync_allowed():
    mock_client = MagicMock()
    mock_client.check_tool_call.return_value = _mock_allow_result("tr-sync-1")

    @guard_tool(tool_name="calculator", client=mock_client)
    def add(a: int, b: int) -> int:
        return a + b

    with agentready_execution("exec-calc", "math-bot"):
        res = add(2, 3)

    assert res == 5
    mock_client.check_tool_call.assert_called_once_with(
        execution_id="exec-calc",
        tool_name="calculator",
        arguments={"a": 2, "b": 3},
    )
    mock_client.report_tool_result.assert_called_once()
    trace_id, report_payload = mock_client.report_tool_result.call_args[0]
    assert trace_id == "tr-sync-1"
    assert report_payload["status"] == "SUCCEEDED"
    assert report_payload["output"] == 5
    assert "latencyMs" in report_payload


def test_guard_tool_sync_blocked_raise():
    mock_client = MagicMock()
    mock_client.check_tool_call.return_value = _mock_block_result("Bash disabled")

    @guard_tool(tool_name="bash", client=mock_client)
    def run_bash(cmd: str) -> str:
        return "done"

    with pytest.raises(ToolBlockedError) as exc_info:
        run_bash("rm -rf /", execution_id="exec-sec")

    assert "Bash disabled" in str(exc_info.value)
    assert exc_info.value.tool_name == "bash"
    assert exc_info.value.reason == "Bash disabled"
    mock_client.report_tool_result.assert_not_called()


def test_guard_tool_sync_blocked_no_raise():
    mock_client = MagicMock()
    mock_client.check_tool_call.return_value = _mock_block_result("Write restricted")

    @guard_tool(
        tool_name="file_write",
        client=mock_client,
        raise_on_blocked=False,
        execution_id="exec-sec",
    )
    def write_file(path: str) -> str:
        return "written"

    res = write_file("/etc/passwd")
    assert res == {
        "status": "BLOCKED",
        "reason": "Write restricted",
        "tool_name": "file_write",
    }


def test_guard_tool_sync_approval_required():
    mock_client = MagicMock()
    mock_client.check_tool_call.return_value = _mock_approval_result("appr-1234")

    @guard_tool(tool_name="deploy", client=mock_client, wait_for_approval=False)
    def deploy_app(env: str) -> str:
        return f"deployed to {env}"

    with agentready_execution("exec-deploy", "deployer"):
        with pytest.raises(ApprovalRequiredError) as exc_info:
            deploy_app("production")

    assert exc_info.value.approval_request_id == "appr-1234"
    assert exc_info.value.tool_name == "deploy"
    assert exc_info.value.execution_id == "exec-deploy"


def test_guard_tool_sync_wait_for_approval_approved():
    mock_client = MagicMock()
    mock_client.check_tool_call.return_value = _mock_approval_result(
        "appr-555", "tr-appr-wait"
    )
    mock_client.wait_for_approval.return_value = MagicMock(status="SUCCEEDED")

    @guard_tool(tool_name="deploy", client=mock_client, wait_for_approval=True)
    def deploy_app(env: str) -> str:
        return f"deployed to {env}"

    res = deploy_app("prod", execution_id="exec-wait")
    assert res == "deployed to prod"
    mock_client.wait_for_approval.assert_called_once_with(
        "exec-wait", poll_interval=2.0, timeout=300.0
    )
    mock_client.report_tool_result.assert_called_once()


def test_guard_tool_sync_exception_reporting():
    mock_client = MagicMock()
    mock_client.check_tool_call.return_value = _mock_allow_result("tr-fail-1")

    @guard_tool(client=mock_client, execution_id="exec-err")
    def flaky_tool():
        raise ValueError("Something broke!")

    with pytest.raises(ValueError, match="Something broke!"):
        flaky_tool()

    mock_client.report_tool_result.assert_called_once()
    trace_id, payload = mock_client.report_tool_result.call_args[0]
    assert trace_id == "tr-fail-1"
    assert payload["status"] == "FAILED"
    assert "Something broke!" in payload["error"]


def test_guard_tool_missing_execution_id():
    mock_client = MagicMock()

    @guard_tool(client=mock_client)
    def orphan_tool():
        return "ok"

    with pytest.raises(AgentReadyError, match="execution_id must be provided"):
        orphan_tool()


@pytest.mark.asyncio
async def test_guard_tool_async_allowed():
    mock_client = MagicMock()
    mock_client.check_tool_call = AsyncMock(
        return_value=_mock_allow_result("tr-async-1")
    )
    mock_client.report_tool_result = AsyncMock()

    @guard_tool(tool_name="fetch_url", client=mock_client)
    async def fetch_url(url: str) -> str:
        await asyncio.sleep(0.01)
        return f"content of {url}"

    with agentready_execution("exec-async-1", "web-agent"):
        res = await fetch_url("https://example.com")

    assert res == "content of https://example.com"
    mock_client.check_tool_call.assert_awaited_once_with(
        execution_id="exec-async-1",
        tool_name="fetch_url",
        arguments={"url": "https://example.com"},
    )
    mock_client.report_tool_result.assert_awaited_once()
    trace_id, payload = mock_client.report_tool_result.call_args[0]
    assert trace_id == "tr-async-1"
    assert payload["status"] == "SUCCEEDED"
    assert payload["latencyMs"] >= 10


@pytest.mark.asyncio
async def test_guard_tool_async_blocked():
    mock_client = MagicMock()
    mock_client.check_tool_call = AsyncMock(
        return_value=_mock_block_result("Domain blacklisted")
    )

    @guard_tool(client=mock_client, execution_id="exec-blk")
    async def curl(domain: str) -> str:
        return "response"

    with pytest.raises(ToolBlockedError, match="Domain blacklisted"):
        await curl("bad.com")


@pytest.mark.asyncio
async def test_guard_tool_async_approval_required():
    mock_client = MagicMock()
    mock_client.check_tool_call = AsyncMock(
        return_value=_mock_approval_result("appr-async-9")
    )

    @guard_tool(client=mock_client, execution_id="exec-appr")
    async def delete_db(db_name: str) -> str:
        return "deleted"

    with pytest.raises(ApprovalRequiredError) as exc_info:
        await delete_db("users")

    assert exc_info.value.approval_request_id == "appr-async-9"


@pytest.mark.asyncio
async def test_guard_tool_async_exception_reporting():
    mock_client = MagicMock()
    mock_client.check_tool_call = AsyncMock(
        return_value=_mock_allow_result("tr-async-fail")
    )
    mock_client.report_tool_result = AsyncMock()

    @guard_tool(client=mock_client, execution_id="exec-err")
    async def failing_async():
        raise RuntimeError("Async disaster")

    with pytest.raises(RuntimeError, match="Async disaster"):
        await failing_async()

    mock_client.report_tool_result.assert_awaited_once()
    _, payload = mock_client.report_tool_result.call_args[0]
    assert payload["status"] == "FAILED"
    assert "Async disaster" in payload["error"]
