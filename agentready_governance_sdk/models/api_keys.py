"""API key models for AgentReady SDK."""

from datetime import datetime

from agentready_governance_sdk.models.base import BaseApiModel


class ApiKey(BaseApiModel):
    """Machine API key entity (secret is never returned after creation)."""

    id: str
    organization_id: str
    agent_id: str | None = None
    name: str
    key_prefix: str
    scopes: list[str]
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @property
    def is_active(self) -> bool:
        """Return True if the key has not been revoked."""
        return self.revoked_at is None


class CreateApiKeyInput(BaseApiModel):
    """Input for creating a new machine API key."""

    name: str
    scopes: list[str] | None = None
    agent_id: str | None = None


class CreateApiKeyResponse(BaseApiModel):
    """Response from the create API key endpoint.

    ``raw_key`` is returned **only once** at creation time and must be stored
    immediately — it cannot be retrieved again.
    """

    raw_key: str
    api_key_record: ApiKey
