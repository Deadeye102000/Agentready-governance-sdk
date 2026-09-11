"""Tool call trace models for AgentReady SDK."""

from datetime import datetime
from typing import Any

from pydantic import Field

from agentready_governance_sdk.models.base import BaseApiModel
from agentready_governance_sdk.models.common import ToolCallDecision, ToolCallStatus


class ToolCallTrace(BaseApiModel):
    """Tool call trace entity."""

    id: str
    organization_id: str
    execution_id: str
    agent_id: str
    tool_name: str
    status: ToolCallStatus = ToolCallStatus.PENDING
    input: dict[str, Any] = Field(default_factory=dict)
    output: Any | None = None
    error: str | None = None
    latency_ms: int | None = None
    approval_request_id: str | None = None
    started_at: datetime
    completed_at: datetime | None = None


class CreateToolCallTraceInput(BaseApiModel):
    """Input for creating a tool call trace."""

    execution_id: str
    agent_id: str
    tool_name: str
    status: ToolCallStatus = ToolCallStatus.PENDING
    input: dict[str, Any] = Field(default_factory=dict)
    output: Any | None = None
    error: str | None = None
    latency_ms: int | None = None
    approval_request_id: str | None = None


class UpdateToolCallTraceInput(BaseApiModel):
    """Input for updating a tool call trace."""

    status: ToolCallStatus
    output: Any | None = None
    error: str | None = None
    latency_ms: int | None = None


class CheckToolCallInput(BaseApiModel):
    """Input for the pre-flight tool-call governance check.

    ``idempotency_key`` is always sent as a non-null string. The
    ``check_tool_call`` client method auto-generates a UUID when the caller
    does not supply one.
    """

    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str


class ToolCallCheckResult(BaseApiModel):
    """Decision returned by the pre-flight tool-call governance check."""

    decision: ToolCallDecision | str
    reason: str
    tool_call_trace_id: str
    approval_request_id: str | None = None
    execution_status: str
    consecutive_blocks: int


class ReportToolCallResultInput(BaseApiModel):
    """Input for reporting the outcome of a completed tool call."""

    status: ToolCallStatus | str
    output: Any | None = None
    error: str | None = None
    latency_ms: int | None = None
    is_final_action: bool | None = None


class ToolCallResultResponse(BaseApiModel):
    """Response from the report-tool-call-result endpoint."""

    tool_call_trace_id: str
    status: str
    execution_id: str
    execution_status: str
    completed_at: datetime
