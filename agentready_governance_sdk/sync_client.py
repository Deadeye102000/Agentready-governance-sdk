"""Synchronous client for AgentReady Governance API."""

import asyncio
from types import TracebackType
from typing import Any

from agentready_governance_sdk._constants import (
    DEFAULT_BASE_URL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
)
from agentready_governance_sdk.client import AsyncGovernanceClient
from agentready_governance_sdk.models.audit import AuditLogEntry
from agentready_governance_sdk.models.common import ExecutionStatus, FeatureFlagState
from agentready_governance_sdk.models.executions import (
    AgentExecution,
    CreateExecutionInput,
    UpdateExecutionInput,
)
from agentready_governance_sdk.models.governance import (
    ApprovalGate,
    FeatureFlag,
    UpsertAgentFeatureFlagInput,
    UpsertApprovalGateInput,
)
from agentready_governance_sdk.models.traces import (
    CreateToolCallTraceInput,
    ToolCallTrace,
    UpdateToolCallTraceInput,
)


class GovernanceClient:
    """Synchronous wrapper for interacting with the AgentReady Governance API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        self._async_client = AsyncGovernanceClient(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )

    def _run(self, coro: Any) -> Any:
        """Helper to run coroutines synchronously via asyncio.run()."""
        return asyncio.run(coro)

    def close(self) -> None:
        """Close the underlying client resources."""
        self._run(self._async_client.close())

    def __enter__(self) -> "GovernanceClient":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    # --- Feature Flags ---

    def list_feature_flags(self, agent_id: str | None = None) -> list[FeatureFlag]:
        """List feature flags for the organization, optionally filtered by agent_id."""
        return self._run(self._async_client.list_feature_flags(agent_id=agent_id))

    def upsert_feature_flag(
        self, input: UpsertAgentFeatureFlagInput | dict[str, Any]
    ) -> FeatureFlag:
        """Create or update an agent feature flag."""
        return self._run(self._async_client.upsert_feature_flag(input=input))

    def toggle_feature_flag(
        self,
        capability: str,
        state: FeatureFlagState | str,
        agent_id: str | None = None,
    ) -> FeatureFlag:
        """Toggle an agent feature flag state."""
        return self._run(
            self._async_client.toggle_feature_flag(
                capability=capability, state=state, agent_id=agent_id
            )
        )

    # --- Approval Gates ---

    def list_approval_gates(self) -> list[ApprovalGate]:
        """List approval gates for the organization."""
        return self._run(self._async_client.list_approval_gates())

    def upsert_approval_gate(
        self, input: UpsertApprovalGateInput | dict[str, Any]
    ) -> ApprovalGate:
        """Create or update an approval gate."""
        return self._run(self._async_client.upsert_approval_gate(input=input))

    # --- Agent Executions ---

    def create_execution(
        self, input: CreateExecutionInput | dict[str, Any]
    ) -> AgentExecution:
        """Create a new agent execution."""
        return self._run(self._async_client.create_execution(input=input))

    def get_execution(self, execution_id: str) -> AgentExecution:
        """Fetch an agent execution by ID."""
        return self._run(self._async_client.get_execution(execution_id=execution_id))

    def list_executions(
        self,
        project_id: str | None = None,
        status: ExecutionStatus | str | None = None,
    ) -> list[AgentExecution]:
        """List agent executions for the organization."""
        return self._run(
            self._async_client.list_executions(project_id=project_id, status=status)
        )

    def update_execution(
        self, execution_id: str, input: UpdateExecutionInput | dict[str, Any]
    ) -> AgentExecution:
        """Update an existing agent execution status or output."""
        return self._run(
            self._async_client.update_execution(execution_id=execution_id, input=input)
        )

    def wait_for_approval(
        self,
        execution_id: str,
        poll_interval: float = 2.0,
        timeout: float = 300.0,
    ) -> AgentExecution:
        """Poll GET /executions/:id until approved, rejected, or timed out."""
        return self._run(
            self._async_client.wait_for_approval(
                execution_id=execution_id,
                poll_interval=poll_interval,
                timeout=timeout,
            )
        )

    # --- Tool Call Traces ---

    def record_tool_call(
        self,
        input: CreateToolCallTraceInput | dict[str, Any],
    ) -> ToolCallTrace:
        """Record a tool call trace synchronously (always blocks)."""
        result = self._run(
            self._async_client.record_tool_call(input=input, fire_and_forget=False)
        )
        assert isinstance(result, ToolCallTrace)
        return result

    def update_tool_call(
        self, trace_id: str, input: UpdateToolCallTraceInput | dict[str, Any]
    ) -> ToolCallTrace:
        """Update an existing tool call trace."""
        return self._run(
            self._async_client.update_tool_call(trace_id=trace_id, input=input)
        )

    # --- Audit Logs & Observability ---

    def list_audit_logs(self, limit: int = 50) -> list[AuditLogEntry]:
        """List recent audit log entries for the organization."""
        return self._run(self._async_client.list_audit_logs(limit=limit))

    def get_dashboard(self) -> dict[str, Any]:
        """Get observability dashboard metrics for the organization."""
        return self._run(self._async_client.get_dashboard())
