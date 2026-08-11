"""Common enums used throughout the AgentReady Governance SDK."""

from enum import Enum


class ExecutionStatus(str, Enum):
    """Execution status of an agent execution task."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ToolCallStatus(str, Enum):
    """Status of a tool call trace."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class ApprovalGateMode(str, Enum):
    """Mode for approval gate evaluation."""

    AUTOMATIC = "AUTOMATIC"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    BLOCKED = "BLOCKED"


class FeatureFlagState(str, Enum):
    """State of an agent feature flag."""

    ENABLED = "ENABLED"
    DISABLED = "DISABLED"


class ApprovalStatus(str, Enum):
    """Status of an approval request."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class ActorType(str, Enum):
    """Type of actor in the governance system."""

    USER = "USER"
    AGENT = "AGENT"
    SYSTEM = "SYSTEM"
