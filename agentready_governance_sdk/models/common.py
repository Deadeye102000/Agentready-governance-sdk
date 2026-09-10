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
    AWAITING_APPROVAL = "AWAITING_APPROVAL"


class ToolCallDecision(str, Enum):
    """Decision returned by the pre-flight tool-call check."""

    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    WAIT_FOR_APPROVAL = "WAIT_FOR_APPROVAL"


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


class EvalRunStatus(str, Enum):
    """Status of an evaluation run."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    ERRORED = "ERRORED"


# Machine API key scopes assignable via the API
# (mirrors backend ASSIGNABLE_API_KEY_SCOPES)
class ApiKeyScope(str, Enum):
    """Scope that can be assigned to a machine API key."""

    AGENT_EXECUTION_WRITE = "agent_execution:write"
    AGENT_EXECUTION_READ = "agent_execution:read"
    GOVERNANCE_WRITE = "governance:write"
    GOVERNANCE_READ = "governance:read"
    EVAL_WRITE = "eval:write"
    EVAL_READ = "eval:read"
    AUDIT_READ = "audit:read"
    API_KEY_WRITE = "api_key:write"
    API_KEY_READ = "api_key:read"
