"""Tool call trace models for AgentReady SDK."""

from datetime import datetime
from typing import Any

from pydantic import Field

from agentready_governance_sdk.models.base import BaseApiModel
from agentready_governance_sdk.models.common import ToolCallStatus


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
