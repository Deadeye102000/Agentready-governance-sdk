"""Agent execution models for AgentReady SDK."""

from datetime import datetime
from typing import Any

from pydantic import Field

from agentready_governance_sdk.models.base import BaseApiModel
from agentready_governance_sdk.models.common import ExecutionStatus


class AgentExecution(BaseApiModel):
    """Agent execution entity."""

    id: str
    organization_id: str
    project_id: str
    agent_id: str
    task_id: str | None = None
    contract_id: str | None = None
    status: ExecutionStatus = ExecutionStatus.QUEUED
    objective: str
    input: dict[str, Any] = Field(default_factory=dict)
    output: Any | None = None
    risk_score: int = 0
    max_attempts: int = 1
    attempt_count: int = 0
    timeout_ms: int | None = None
    timed_out_at: datetime | None = None
    failure_reason: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class CreateExecutionInput(BaseApiModel):
    """Input for creating an agent execution."""

    project_id: str
    agent_id: str
    objective: str
    task_id: str | None = None
    contract_id: str | None = None
    input: dict[str, Any] = Field(default_factory=dict)
    risk_score: int = 0
    timeout_ms: int | None = None
    max_attempts: int = 1
    metadata: dict[str, Any] | None = None


class UpdateExecutionInput(BaseApiModel):
    """Input for updating an agent execution."""

    status: ExecutionStatus
    output: Any | None = None
    completed_at: datetime | None = None
