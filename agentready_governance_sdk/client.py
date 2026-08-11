"""Asynchronous client for AgentReady Governance API."""

import asyncio
from enum import Enum
from types import TracebackType
from typing import Any

import httpx

from agentready_governance_sdk._constants import (
    DEFAULT_BASE_URL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
)
from agentready_governance_sdk._transport import (
    _raise_for_status,
    get_async_retry_policy,
)
from agentready_governance_sdk._version import __version__
from agentready_governance_sdk.exceptions import (
    ApprovalRejectedError,
    ApprovalTimeoutError,
)
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


class AsyncGovernanceClient:
    """Asynchronous client for interacting with the AgentReady Governance API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._background_tasks: set[asyncio.Task[Any]] = set()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": f"AgentReady-Governance-SDK/{__version__}",
        }

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=self.timeout,
        )

    async def close(self) -> None:
        """Close the underlying HTTP client and await any pending background tasks."""
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncGovernanceClient":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    def _build_url(self, path: str) -> str:
        clean_path = path.lstrip("/")
        if self.base_url.endswith("/api/v1") and clean_path.startswith("api/v1/"):
            clean_path = clean_path[7:]
        elif not self.base_url.endswith("/api/v1") and not clean_path.startswith(
            "api/v1/"
        ):
            clean_path = f"api/v1/{clean_path}"
        return f"/{clean_path}"

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
    ) -> httpx.Response:
        url = self._build_url(path)
        retrier = get_async_retry_policy(max_retries=self.max_retries)

        async def _execute() -> httpx.Response:
            response = await self._client.request(
                method=method,
                url=url,
                params=params,
                json=json,
            )
            _raise_for_status(response)
            return response

        return await retrier(_execute)

    # --- Feature Flags ---

    async def list_feature_flags(
        self, agent_id: str | None = None
    ) -> list[FeatureFlag]:
        """List feature flags for the organization, optionally filtered by agent_id."""
        params = {"agentId": agent_id} if agent_id else None
        response = await self._request("GET", "/api/v1/feature-flags", params=params)
        data = response.json()
        return [FeatureFlag.model_validate(item) for item in data]

    async def upsert_feature_flag(
        self, input: UpsertAgentFeatureFlagInput | dict[str, Any]
    ) -> FeatureFlag:
        """Create or update an agent feature flag."""
        if isinstance(input, UpsertAgentFeatureFlagInput):
            payload = input.model_dump(by_alias=True, mode="json", exclude_none=True)
        else:
            payload = input

        response = await self._request("PUT", "/api/v1/feature-flags", json=payload)
        return FeatureFlag.model_validate(response.json())

    async def toggle_feature_flag(
        self,
        capability: str,
        state: FeatureFlagState | str,
        agent_id: str | None = None,
    ) -> FeatureFlag:
        """Toggle an agent feature flag state."""
        state_str = state.value if isinstance(state, Enum) else str(state)
        payload: dict[str, Any] = {
            "capability": capability,
            "state": state_str,
        }
        if agent_id is not None:
            payload["agentId"] = agent_id

        response = await self._request(
            "POST", "/api/v1/feature-flags/toggle", json=payload
        )
        return FeatureFlag.model_validate(response.json())

    # --- Approval Gates ---

    async def list_approval_gates(self) -> list[ApprovalGate]:
        """List approval gates for the organization."""
        response = await self._request("GET", "/api/v1/approval-gates")
        data = response.json()
        return [ApprovalGate.model_validate(item) for item in data]

    async def upsert_approval_gate(
        self, input: UpsertApprovalGateInput | dict[str, Any]
    ) -> ApprovalGate:
        """Create or update an approval gate."""
        if isinstance(input, UpsertApprovalGateInput):
            payload = input.model_dump(by_alias=True, mode="json", exclude_none=True)
        else:
            payload = input

        response = await self._request("PUT", "/api/v1/approval-gates", json=payload)
        return ApprovalGate.model_validate(response.json())

    # --- Agent Executions ---

    async def create_execution(
        self, input: CreateExecutionInput | dict[str, Any]
    ) -> AgentExecution:
        """Create a new agent execution."""
        if isinstance(input, CreateExecutionInput):
            payload = input.model_dump(by_alias=True, mode="json", exclude_none=True)
        else:
            payload = input

        response = await self._request("POST", "/api/v1/executions", json=payload)
        return AgentExecution.model_validate(response.json())

    async def get_execution(self, execution_id: str) -> AgentExecution:
        """Fetch an agent execution by ID."""
        response = await self._request("GET", f"/api/v1/executions/{execution_id}")
        return AgentExecution.model_validate(response.json())

    async def list_executions(
        self,
        project_id: str | None = None,
        status: ExecutionStatus | str | None = None,
    ) -> list[AgentExecution]:
        """List agent executions for the organization."""
        params: dict[str, Any] = {}
        if project_id is not None:
            params["projectId"] = project_id
        if status is not None:
            params["status"] = status.value if isinstance(status, Enum) else str(status)

        response = await self._request(
            "GET", "/api/v1/executions", params=params or None
        )
        data = response.json()
        return [AgentExecution.model_validate(item) for item in data]

    async def update_execution(
        self, execution_id: str, input: UpdateExecutionInput | dict[str, Any]
    ) -> AgentExecution:
        """Update an existing agent execution status or output."""
        if isinstance(input, UpdateExecutionInput):
            payload = input.model_dump(by_alias=True, mode="json", exclude_none=True)
        else:
            payload = input

        response = await self._request(
            "PATCH", f"/api/v1/executions/{execution_id}", json=payload
        )
        return AgentExecution.model_validate(response.json())

    async def wait_for_approval(
        self,
        execution_id: str,
        poll_interval: float = 2.0,
        timeout: float = 300.0,
    ) -> AgentExecution:
        """Poll GET /executions/:id until approved, rejected, cancelled, or timed out.

        - WAITING_FOR_APPROVAL / QUEUED: continues polling.
        - RUNNING / SUCCEEDED: returns the AgentExecution.
        - FAILED / CANCELLED: raises ApprovalRejectedError.
        - Timeout reached: raises ApprovalTimeoutError.
        """
        loop = asyncio.get_running_loop()
        start_time = loop.time()

        while True:
            execution = await self.get_execution(execution_id)

            if execution.status in (
                ExecutionStatus.RUNNING,
                ExecutionStatus.SUCCEEDED,
            ):
                return execution

            if execution.status in (
                ExecutionStatus.FAILED,
                ExecutionStatus.CANCELLED,
            ):
                raise ApprovalRejectedError(
                    f"Execution {execution_id} was rejected ({execution.status})"
                )

            elapsed = loop.time() - start_time
            if elapsed >= timeout:
                raise ApprovalTimeoutError(
                    f"Approval request {execution_id} timed out after {timeout}s"
                )

            await asyncio.sleep(poll_interval)

    # --- Tool Call Traces ---

    async def record_tool_call(
        self,
        input: CreateToolCallTraceInput | dict[str, Any],
        fire_and_forget: bool = True,
    ) -> ToolCallTrace | None:
        """Record a tool call trace asynchronously or fire-and-forget in background."""
        if isinstance(input, CreateToolCallTraceInput):
            payload = input.model_dump(by_alias=True, mode="json", exclude_none=True)
        else:
            payload = input

        if fire_and_forget:
            task = asyncio.create_task(
                self._request("POST", "/api/v1/tool-call-traces", json=payload)
            )
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
            return None

        response = await self._request("POST", "/api/v1/tool-call-traces", json=payload)
        return ToolCallTrace.model_validate(response.json())

    async def update_tool_call(
        self, trace_id: str, input: UpdateToolCallTraceInput | dict[str, Any]
    ) -> ToolCallTrace:
        """Update an existing tool call trace."""
        if isinstance(input, UpdateToolCallTraceInput):
            payload = input.model_dump(by_alias=True, mode="json", exclude_none=True)
        else:
            payload = input

        response = await self._request(
            "PATCH", f"/api/v1/tool-call-traces/{trace_id}", json=payload
        )
        return ToolCallTrace.model_validate(response.json())

    # --- Audit Logs & Observability ---

    async def list_audit_logs(self, limit: int = 50) -> list[AuditLogEntry]:
        """List recent audit log entries for the organization."""
        response = await self._request(
            "GET", "/api/v1/audit-logs", params={"limit": limit}
        )
        data = response.json()
        return [AuditLogEntry.model_validate(item) for item in data]

    async def get_dashboard(self) -> dict[str, Any]:
        """Get observability dashboard metrics for the organization."""
        response = await self._request("GET", "/api/v1/observability/dashboard")
        return response.json()
