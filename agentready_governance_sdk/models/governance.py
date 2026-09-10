"""Governance models for AgentReady SDK."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field

from agentready_governance_sdk.models.base import BaseApiModel
from agentready_governance_sdk.models.common import (
    ApprovalGateMode,
    ApprovalStatus,
    FeatureFlagState,
)


class McpServerStatus(str, Enum):
    """Lifecycle status of a registered MCP server."""

    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class FeatureFlag(BaseApiModel):
    """Feature flag entity."""

    id: str
    organization_id: str
    agent_id: str | None = None
    capability: str
    state: FeatureFlagState
    description: str | None = None
    created_at: datetime
    updated_at: datetime


class UpsertAgentFeatureFlagInput(BaseApiModel):
    """Input for upserting an agent feature flag."""

    capability: str
    state: FeatureFlagState
    agent_id: str | None = None
    description: str | None = None


class ApprovalGate(BaseApiModel):
    """Approval gate entity."""

    id: str
    organization_id: str
    capability: str
    mode: ApprovalGateMode
    reason: str | None = None
    risk_level: int = 0
    enabled: bool = True
    created_at: datetime
    updated_at: datetime


class UpsertApprovalGateInput(BaseApiModel):
    """Input for upserting an approval gate."""

    capability: str
    mode: ApprovalGateMode
    reason: str | None = None
    risk_level: int = 0
    enabled: bool = True


class ApprovalRequest(BaseApiModel):
    """Approval request entity."""

    id: str
    organization_id: str
    agent_id: str
    requested_action: str
    reason: str
    payload: dict[str, Any] = Field(default_factory=dict)
    status: ApprovalStatus = ApprovalStatus.PENDING
    expires_at: datetime | None = None
    reviewed_by_user_id: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ReviewApprovalRequestInput(BaseApiModel):
    """Input for reviewing an approval request."""

    status: ApprovalStatus
    note: str | None = None


class McpServerRegistration(BaseApiModel):
    """Registered MCP (Machine Control Protocol) server entity."""

    id: str
    organization_id: str
    name: str
    base_url: str | None = None
    status: McpServerStatus = McpServerStatus.PLANNED
    capabilities: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
