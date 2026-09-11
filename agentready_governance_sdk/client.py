"""Async client for AgentReady Governance API."""

import asyncio
import uuid
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
from agentready_governance_sdk.exceptions import (
    ApprovalRejectedError,
    ApprovalTimeoutError,
)
from agentready_governance_sdk.models.api_keys import (
    ApiKey,
    CreateApiKeyInput,
    CreateApiKeyResponse,
)
from agentready_governance_sdk.models.audit import AuditLogEntry
from agentready_governance_sdk.models.common import (
    ApprovalStatus,
    ExecutionStatus,
)
from agentready_governance_sdk.models.contracts import (
    CreateTaskContractInput,
    PatchTaskContractInput,
    TaskContract,
)
from agentready_governance_sdk.models.evals import (
    CreateEvalCaseInput,
    CreateEvalRunInput,
    EvalCase,
    EvalRun,
    RegressionReport,
    RunEvalSuiteInput,
)
from agentready_governance_sdk.models.executions import (
    AgentExecution,
    CreateExecutionInput,
    UpdateExecutionInput,
)
from agentready_governance_sdk.models.governance import (
    ApprovalGate,
    ApprovalRequest,
    FeatureFlag,
    McpServerRegistration,
    ReviewApprovalRequestInput,
    UpsertAgentFeatureFlagInput,
    UpsertApprovalGateInput,
)
from agentready_governance_sdk.models.traces import (
    CreateToolCallTraceInput,
    ReportToolCallResultInput,
    ToolCallCheckResult,
    ToolCallResultResponse,
    ToolCallTrace,
    UpdateToolCallTraceInput,
)


class AsyncGovernanceClient:
    """Async client for interacting with the AgentReady Governance API."""

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
        self._api_key = api_key
        self._base_url = self.base_url
        self._timeout = timeout
        self._max_retries = max_retries
        self._http_client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )
        self._background_tasks: set[asyncio.Task[Any]] = set()

    async def close(self) -> None:
        """Close the underlying HTTP client and await any pending background tasks."""
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        await self._http_client.aclose()

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
        return f"{self._base_url}{path}"

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json: Any = None,
    ) -> httpx.Response:
        retrier = get_async_retry_policy(max_retries=self._max_retries)

        async def _execute() -> httpx.Response:
            response = await self._http_client.request(
                method=method,
                url=self._build_url(path),
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
        agent_id: str | None = None,
    ) -> FeatureFlag:
        """Toggle a feature flag between ENABLED and DISABLED.

        The backend determines the new state by flipping the current value.
        Do **not** pass a desired ``state`` — use :meth:`upsert_feature_flag`
        if you need to set a specific end-state.
        """
        payload: dict[str, Any] = {"capability": capability}
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

    # --- Approval Requests ---

    async def list_approval_requests(
        self, status: ApprovalStatus | str | None = None
    ) -> list[ApprovalRequest]:
        """List approval requests, optionally filtered by status."""
        params: dict[str, Any] = {}
        if status is not None:
            params["status"] = status.value if isinstance(status, Enum) else str(status)
        response = await self._request(
            "GET", "/api/v1/approval-requests", params=params or None
        )
        return [ApprovalRequest.model_validate(item) for item in response.json()]

    async def review_approval_request(
        self,
        request_id: str,
        input: ReviewApprovalRequestInput | dict[str, Any],
    ) -> ApprovalRequest:
        """Approve or reject an approval request."""
        if isinstance(input, ReviewApprovalRequestInput):
            payload = input.model_dump(by_alias=True, mode="json", exclude_none=True)
        else:
            payload = input

        response = await self._request(
            "POST", f"/api/v1/approval-requests/{request_id}/review", json=payload
        )
        return ApprovalRequest.model_validate(response.json())

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

    # --- Tool Call Governance ---

    async def check_tool_call(
        self,
        execution_id: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> ToolCallCheckResult:
        """Pre-flight governance check for a tool call.

        Evaluates contracts, feature flags, and approval gates for the given
        tool and returns a decision of ``ALLOW``, ``BLOCK``, or
        ``WAIT_FOR_APPROVAL``.

        Args:
            execution_id: ID of the currently running agent execution.
            tool_name: Name of the tool being called.
            arguments: Tool arguments (used for argument-level approval matching).
            idempotency_key: Caller-supplied idempotency key. A UUID is
                auto-generated when not provided, ensuring every call is
                idempotent by default.

        Raises:
            ConcurrentToolCallDisallowedError: Another tool call is already
                PENDING for this execution. Complete it first.
            IdempotencyKeyMismatchError: The key was previously used with a
                different payload.
        """
        key = idempotency_key or str(uuid.uuid4())
        payload: dict[str, Any] = {
            "toolName": tool_name,
            "arguments": arguments or {},
            "idempotencyKey": key,
        }
        response = await self._request(
            "POST",
            f"/api/v1/executions/{execution_id}/tool-calls/check",
            json=payload,
        )
        return ToolCallCheckResult.model_validate(response.json())

    async def report_tool_call_result(
        self,
        trace_id: str,
        input: ReportToolCallResultInput | dict[str, Any],
    ) -> ToolCallResultResponse:
        """Report the outcome of a completed tool call.

        Args:
            trace_id: The ``tool_call_trace_id`` returned by :meth:`check_tool_call`.
            input: Result including status (SUCCEEDED/FAILED), output, error,
                latency, and whether this is the execution's final action.
        """
        if isinstance(input, ReportToolCallResultInput):
            payload = input.model_dump(by_alias=True, mode="json", exclude_none=True)
        else:
            payload = input

        response = await self._request(
            "POST", f"/api/v1/tool-calls/{trace_id}/result", json=payload
        )
        return ToolCallResultResponse.model_validate(response.json())

    async def report_tool_result(
        self,
        trace_id: str,
        input: ReportToolCallResultInput | dict[str, Any],
    ) -> ToolCallResultResponse:
        """Alias for :meth:`report_tool_call_result`."""
        return await self.report_tool_call_result(trace_id=trace_id, input=input)

    async def list_tool_call_traces(
        self,
        execution_id: str | None = None,
        page: int = 1,
        limit: int = 50,
    ) -> list[ToolCallTrace]:
        """List tool call traces, optionally filtered by execution."""
        params: dict[str, Any] = {"page": page, "limit": limit}
        if execution_id is not None:
            params["executionId"] = execution_id
        response = await self._request("GET", "/api/v1/tool-call-traces", params=params)
        return [ToolCallTrace.model_validate(item) for item in response.json()]

    # --- Tool Call Traces (raw record / update) ---

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

    # --- Task Contracts ---

    async def list_task_contracts(
        self, project_id: str | None = None
    ) -> list[TaskContract]:
        """List task contracts, optionally filtered by project."""
        params = {"projectId": project_id} if project_id else None
        response = await self._request("GET", "/api/v1/task-contracts", params=params)
        return [TaskContract.model_validate(item) for item in response.json()]

    async def get_task_contract(self, contract_id: str) -> TaskContract:
        """Fetch a task contract by ID."""
        response = await self._request("GET", f"/api/v1/task-contracts/{contract_id}")
        return TaskContract.model_validate(response.json())

    async def create_task_contract(
        self, input: CreateTaskContractInput | dict[str, Any]
    ) -> TaskContract:
        """Create a new task contract."""
        if isinstance(input, CreateTaskContractInput):
            payload = input.model_dump(by_alias=True, mode="json", exclude_none=True)
        else:
            payload = input

        response = await self._request("POST", "/api/v1/task-contracts", json=payload)
        return TaskContract.model_validate(response.json())

    async def patch_task_contract(
        self,
        contract_id: str,
        input: PatchTaskContractInput | dict[str, Any],
    ) -> TaskContract:
        """Partially update a task contract."""
        if isinstance(input, PatchTaskContractInput):
            payload = input.model_dump(by_alias=True, mode="json", exclude_none=True)
        else:
            payload = input

        response = await self._request(
            "PATCH", f"/api/v1/task-contracts/{contract_id}", json=payload
        )
        return TaskContract.model_validate(response.json())

    # --- Eval Cases ---

    async def list_eval_cases(
        self, task_contract_id: str | None = None
    ) -> list[EvalCase]:
        """List eval cases, optionally filtered by task contract."""
        params = {"taskContractId": task_contract_id} if task_contract_id else None
        response = await self._request("GET", "/api/v1/eval-cases", params=params)
        return [EvalCase.model_validate(item) for item in response.json()]

    async def create_eval_case(
        self, input: CreateEvalCaseInput | dict[str, Any]
    ) -> EvalCase:
        """Create a new eval case."""
        if isinstance(input, CreateEvalCaseInput):
            payload = input.model_dump(by_alias=True, mode="json", exclude_none=True)
        else:
            payload = input

        response = await self._request("POST", "/api/v1/eval-cases", json=payload)
        return EvalCase.model_validate(response.json())

    async def run_eval_case(self, case_id: str) -> EvalRun:
        """Trigger a single eval case run and return the resulting EvalRun."""
        response = await self._request("POST", f"/api/v1/eval-cases/{case_id}/run")
        return EvalRun.model_validate(response.json())

    # --- Eval Runs ---

    async def list_eval_runs(
        self,
        project_id: str | None = None,
        execution_id: str | None = None,
        eval_case_id: str | None = None,
    ) -> list[EvalRun]:
        """List eval runs with optional filters."""
        params: dict[str, Any] = {}
        if project_id is not None:
            params["projectId"] = project_id
        if execution_id is not None:
            params["executionId"] = execution_id
        if eval_case_id is not None:
            params["evalCaseId"] = eval_case_id

        response = await self._request(
            "GET", "/api/v1/eval-runs", params=params or None
        )
        return [EvalRun.model_validate(item) for item in response.json()]

    async def create_eval_run(
        self, input: CreateEvalRunInput | dict[str, Any]
    ) -> EvalRun:
        """Create an eval run record."""
        if isinstance(input, CreateEvalRunInput):
            payload = input.model_dump(by_alias=True, mode="json", exclude_none=True)
        else:
            payload = input

        response = await self._request("POST", "/api/v1/eval-runs", json=payload)
        return EvalRun.model_validate(response.json())

    async def run_eval_suite(
        self,
        input: RunEvalSuiteInput | dict[str, Any] | None = None,
        task_contract_id: str | None = None,
        project_id: str | None = None,
    ) -> list[EvalRun]:
        """Run all eval cases in a suite and return the resulting EvalRuns.

        You may pass a :class:`RunEvalSuiteInput` model, a dict, or use the
        ``task_contract_id`` / ``project_id`` convenience kwargs.
        """
        if input is not None:
            if isinstance(input, RunEvalSuiteInput):
                payload = input.model_dump(
                    by_alias=True, mode="json", exclude_none=True
                )
            else:
                payload = input
        else:
            payload = {}
            if task_contract_id is not None:
                payload["taskContractId"] = task_contract_id
            if project_id is not None:
                payload["projectId"] = project_id

        response = await self._request("POST", "/api/v1/eval-suites/run", json=payload)
        return [EvalRun.model_validate(item) for item in response.json()]

    async def get_regression_report(
        self, contract_id: str | None = None
    ) -> RegressionReport:
        """Get the regression delta report for the latest two eval suite runs."""
        params = {"contractId": contract_id} if contract_id else None
        response = await self._request(
            "GET", "/api/v1/eval-runs/regression", params=params
        )
        return RegressionReport.model_validate(response.json())

    # --- API Keys ---

    async def list_api_keys(self) -> list[ApiKey]:
        """List machine API keys for the organization."""
        response = await self._request("GET", "/api/v1/api-keys")
        return [ApiKey.model_validate(item) for item in response.json()]

    async def create_api_key(
        self,
        input: CreateApiKeyInput | dict[str, Any],
    ) -> CreateApiKeyResponse:
        """Create a new machine API key.

        The ``raw_key`` in the response is returned **only once**. Store it
        immediately — it cannot be retrieved again.
        """
        if isinstance(input, CreateApiKeyInput):
            payload = input.model_dump(by_alias=True, mode="json", exclude_none=True)
        else:
            payload = input

        response = await self._request("POST", "/api/v1/api-keys", json=payload)
        return CreateApiKeyResponse.model_validate(response.json())

    async def revoke_api_key(self, key_id: str) -> ApiKey:
        """Revoke a machine API key by ID."""
        response = await self._request("DELETE", f"/api/v1/api-keys/{key_id}")
        return ApiKey.model_validate(response.json())

    # --- MCP Servers ---

    async def list_mcp_servers(self) -> list[McpServerRegistration]:
        """List registered MCP servers for the organization."""
        response = await self._request("GET", "/api/v1/mcp-servers")
        return [McpServerRegistration.model_validate(item) for item in response.json()]

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


AsyncAgentReadyClient = AsyncGovernanceClient

_DEFAULT_ASYNC_CLIENT: AsyncGovernanceClient | None = None


def get_default_async_client() -> AsyncGovernanceClient:
    """Return or initialize the default AsyncGovernanceClient singleton."""
    global _DEFAULT_ASYNC_CLIENT
    if _DEFAULT_ASYNC_CLIENT is None:
        _DEFAULT_ASYNC_CLIENT = AsyncGovernanceClient()
    return _DEFAULT_ASYNC_CLIENT


def set_default_async_client(client: AsyncGovernanceClient | None) -> None:
    """Set or clear the default AsyncGovernanceClient singleton."""
    global _DEFAULT_ASYNC_CLIENT
    _DEFAULT_ASYNC_CLIENT = client
