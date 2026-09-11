"""Unit tests for LangChain and LangGraph integration."""

import uuid
from unittest.mock import MagicMock, patch

import pytest

import agentready_governance_sdk.integrations.langchain as lc_mod
from agentready_governance_sdk.context import agentready_execution
from agentready_governance_sdk.exceptions import (
    ApprovalRequiredError,
    ToolBlockedError,
)
from agentready_governance_sdk.integrations.langchain import (
    AgentReadyCallbackHandler,
)
from agentready_governance_sdk.models.common import ToolCallDecision
from agentready_governance_sdk.models.traces import ToolCallCheckResult


def _mock_allow(trace_id: str = "tr-lc-1") -> ToolCallCheckResult:
    return ToolCallCheckResult(
        decision=ToolCallDecision.ALLOW,
        reason="Allowed",
        tool_call_trace_id=trace_id,
        execution_status="RUNNING",
        consecutive_blocks=0,
    )


def _mock_block(reason: str = "SQL write restricted") -> ToolCallCheckResult:
    return ToolCallCheckResult(
        decision=ToolCallDecision.BLOCK,
        reason=reason,
        tool_call_trace_id="tr-lc-blk",
        execution_status="RUNNING",
        consecutive_blocks=1,
    )


def _mock_approval(req_id: str = "appr-req-lc") -> ToolCallCheckResult:
    return ToolCallCheckResult(
        decision=ToolCallDecision.WAIT_FOR_APPROVAL,
        reason="Sensitive action requires approval",
        tool_call_trace_id="tr-lc-appr",
        approval_request_id=req_id,
        execution_status="WAITING_FOR_APPROVAL",
        consecutive_blocks=0,
    )


def test_langchain_not_installed_error():
    with patch.object(lc_mod, "HAS_LANGCHAIN", False):
        with pytest.raises(ImportError, match="langchain-core is not installed"):
            AgentReadyCallbackHandler(execution_id="exec-1")


@pytest.fixture(autouse=True)
def enable_langchain(monkeypatch):
    monkeypatch.setattr(lc_mod, "HAS_LANGCHAIN", True)


def test_on_tool_start_and_end_allowed():
    mock_client = MagicMock()
    mock_client.check_tool_call.return_value = _mock_allow("tr-lc-100")

    handler = AgentReadyCallbackHandler(client=mock_client)
    run_id = uuid.uuid4()
    serialized = {"name": "web_search", "description": "search web"}

    with agentready_execution("exec-lc-1", "react_agent"):
        handler.on_tool_start(
            serialized=serialized,
            input_str='{"query": "quantum computing"}',
            run_id=run_id,
        )

    mock_client.check_tool_call.assert_called_once_with(
        execution_id="exec-lc-1",
        tool_name="web_search",
        arguments={"query": "quantum computing"},
    )

    # Simulate tool completion
    handler.on_tool_end(output={"results": ["article1", "article2"]}, run_id=run_id)

    mock_client.report_tool_result.assert_called_once()
    trace_id, payload = mock_client.report_tool_result.call_args[0]
    assert trace_id == "tr-lc-100"
    assert payload["status"] == "SUCCEEDED"
    assert payload["output"] == {"results": ["article1", "article2"]}
    assert "latencyMs" in payload


def test_on_tool_start_blocked():
    mock_client = MagicMock()
    mock_client.check_tool_call.return_value = _mock_block("DROP TABLE forbidden")

    handler = AgentReadyCallbackHandler(client=mock_client, execution_id="exec-sql-sec")
    serialized = {"name": "sql_query"}

    with pytest.raises(ToolBlockedError) as exc_info:
        handler.on_tool_start(
            serialized=serialized,
            input_str="DROP TABLE users;",
            run_id=uuid.uuid4(),
        )

    assert "DROP TABLE forbidden" in str(exc_info.value)
    assert exc_info.value.tool_name == "sql_query"
    mock_client.report_tool_result.assert_not_called()


def test_on_tool_start_approval_required():
    mock_client = MagicMock()
    mock_client.check_tool_call.return_value = _mock_approval("appr-req-lc-55")

    handler = AgentReadyCallbackHandler(
        client=mock_client, execution_id="exec-appr", wait_for_approval=False
    )
    serialized = {"name": "transfer_funds"}

    with pytest.raises(ApprovalRequiredError) as exc_info:
        handler.on_tool_start(
            serialized=serialized,
            input_str='{"amount": 1000000}',
            run_id=uuid.uuid4(),
        )

    assert exc_info.value.approval_request_id == "appr-req-lc-55"
    assert exc_info.value.tool_name == "transfer_funds"
    assert exc_info.value.execution_id == "exec-appr"


def test_on_tool_start_wait_for_approval():
    mock_client = MagicMock()
    mock_client.check_tool_call.return_value = _mock_approval("appr-wait-1")
    mock_client.wait_for_approval.return_value = MagicMock()

    handler = AgentReadyCallbackHandler(
        client=mock_client, execution_id="exec-wait", wait_for_approval=True
    )
    serialized = {"name": "reboot_server"}
    run_id = uuid.uuid4()

    handler.on_tool_start(
        serialized=serialized,
        input_str="now",
        run_id=run_id,
    )

    mock_client.wait_for_approval.assert_called_once_with(
        "exec-wait", poll_interval=2.0, timeout=300.0
    )

    handler.on_tool_end("Server restarted", run_id=run_id)
    mock_client.report_tool_result.assert_called_once()


def test_on_tool_error_reporting():
    mock_client = MagicMock()
    mock_client.check_tool_call.return_value = _mock_allow("tr-err-1")

    handler = AgentReadyCallbackHandler(client=mock_client, execution_id="exec-err")
    run_id = uuid.uuid4()

    handler.on_tool_start(
        serialized={"name": "api_call"},
        input_str="https://api.internal/data",
        run_id=run_id,
    )

    handler.on_tool_error(
        error=ConnectionResetError("Connection reset by peer"), run_id=run_id
    )

    mock_client.report_tool_result.assert_called_once()
    trace_id, payload = mock_client.report_tool_result.call_args[0]
    assert trace_id == "tr-err-1"
    assert payload["status"] == "FAILED"
    assert "Connection reset by peer" in payload["error"]


def test_execution_id_resolution_from_metadata():
    mock_client = MagicMock()
    mock_client.check_tool_call.return_value = _mock_allow("tr-meta-1")

    handler = AgentReadyCallbackHandler(client=mock_client)
    handler.on_tool_start(
        serialized={"name": "calculator"},
        input_str="2 + 2",
        metadata={"execution_id": "exec-via-meta"},
        run_id=uuid.uuid4(),
    )

    mock_client.check_tool_call.assert_called_once_with(
        execution_id="exec-via-meta",
        tool_name="calculator",
        arguments={"input": "2 + 2"},
    )
