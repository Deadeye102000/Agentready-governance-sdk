"""Audit log models for AgentReady SDK."""

from datetime import datetime
from typing import Any

from pydantic import Field

from agentready_governance_sdk.models.base import BaseApiModel
from agentready_governance_sdk.models.common import ActorType


class AuditLogEntry(BaseApiModel):
    """Audit log entry entity."""

    id: str
    organization_id: str
    actor_type: ActorType
    actor_user_id: str | None = None
    actor_agent_id: str | None = None
    action: str
    target_type: str
    target_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
