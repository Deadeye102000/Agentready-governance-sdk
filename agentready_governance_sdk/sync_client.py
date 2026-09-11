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
from agentready_governance_sdk.models.api_keys import (
    ApiKey,
    CreateApiKeyInput,
    CreateApiKeyResponse,
)
from agentready_governance_sdk.models.audit import AuditLogEntry
from agentready_governance_sdk.models.common import ApprovalStatus, ExecutionStatus
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
        agent_id: str | None = None,
    ) -> FeatureFlag:
        """Toggle a feature flag between ENABLED and DISABLED.

        The backend determines the new state by flipping the current value.
        Use :meth:`upsert_feature_flag` to set a specific end-state.
        """
        return self._run(
            self._async_client.toggle_feature_flag(
                capability=capability, agent_id=agent_id
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

    # --- Approval Requests ---

    def list_approval_requests(
        self, status: ApprovalStatus | str | None = None
    ) -> list[ApprovalRequest]:
        """List approval requests, optionally filtered by status."""
        return self._run(self._async_client.list_approval_requests(status=status))

    def review_approval_request(
        self,
        request_id: str,
        input: ReviewApprovalRequestInput | dict[str, Any],
    ) -> ApprovalRequest:
        """Approve or reject an approval request."""
        return self._run(
            self._async_client.review_approval_request(
                request_id=request_id, input=input
            )
        )

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

    # --- Tool Call Governance ---

    def check_tool_call(
        self,
        execution_id: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> ToolCallCheckResult:
        """Pre-flight governance check for a tool call (synchronous).

        A UUID is auto-generated for ``idempotency_key`` when not supplied.
        """
        return self._run(
            self._async_client.check_tool_call(
                execution_id=execution_id,
                tool_name=tool_name,
                arguments=arguments,
                idempotency_key=idempotency_key,
            )
        )

    def report_tool_call_result(
        self,
        trace_id: str,
        input: ReportToolCallResultInput | dict[str, Any],
    ) -> ToolCallResultResponse:
        """Report the outcome of a completed tool call."""
        return self._run(
            self._async_client.report_tool_call_result(trace_id=trace_id, input=input)
        )

    def report_tool_result(
        self,
        trace_id: str,
        input: ReportToolCallResultInput | dict[str, Any],
    ) -> ToolCallResultResponse:
        """Alias for :meth:`report_tool_call_result`."""
        return self.report_tool_call_result(trace_id=trace_id, input=input)

    def list_tool_call_traces(
        self,
        execution_id: str | None = None,
        page: int = 1,
        limit: int = 50,
    ) -> list[ToolCallTrace]:
        """List tool call traces, optionally filtered by execution."""
        return self._run(
            self._async_client.list_tool_call_traces(
                execution_id=execution_id, page=page, limit=limit
            )
        )

    # --- Tool Call Traces (raw) ---

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

    # --- Task Contracts ---

    def list_task_contracts(self, project_id: str | None = None) -> list[TaskContract]:
        """List task contracts, optionally filtered by project."""
        return self._run(self._async_client.list_task_contracts(project_id=project_id))

    def get_task_contract(self, contract_id: str) -> TaskContract:
        """Fetch a task contract by ID."""
        return self._run(self._async_client.get_task_contract(contract_id=contract_id))

    def create_task_contract(
        self, input: CreateTaskContractInput | dict[str, Any]
    ) -> TaskContract:
        """Create a new task contract."""
        return self._run(self._async_client.create_task_contract(input=input))

    def patch_task_contract(
        self,
        contract_id: str,
        input: PatchTaskContractInput | dict[str, Any],
    ) -> TaskContract:
        """Partially update a task contract."""
        return self._run(
            self._async_client.patch_task_contract(contract_id=contract_id, input=input)
        )

    # --- Eval Cases ---

    def list_eval_cases(self, task_contract_id: str | None = None) -> list[EvalCase]:
        """List eval cases, optionally filtered by task contract."""
        return self._run(
            self._async_client.list_eval_cases(task_contract_id=task_contract_id)
        )

    def create_eval_case(self, input: CreateEvalCaseInput | dict[str, Any]) -> EvalCase:
        """Create a new eval case."""
        return self._run(self._async_client.create_eval_case(input=input))

    def run_eval_case(self, case_id: str) -> EvalRun:
        """Trigger a single eval case run."""
        return self._run(self._async_client.run_eval_case(case_id=case_id))

    # --- Eval Runs ---

    def list_eval_runs(
        self,
        project_id: str | None = None,
        execution_id: str | None = None,
        eval_case_id: str | None = None,
    ) -> list[EvalRun]:
        """List eval runs with optional filters."""
        return self._run(
            self._async_client.list_eval_runs(
                project_id=project_id,
                execution_id=execution_id,
                eval_case_id=eval_case_id,
            )
        )

    def create_eval_run(self, input: CreateEvalRunInput | dict[str, Any]) -> EvalRun:
        """Create an eval run record."""
        return self._run(self._async_client.create_eval_run(input=input))

    def run_eval_suite(
        self,
        input: RunEvalSuiteInput | dict[str, Any] | None = None,
        task_contract_id: str | None = None,
        project_id: str | None = None,
    ) -> list[EvalRun]:
        """Run all eval cases in a suite and return the resulting EvalRuns."""
        return self._run(
            self._async_client.run_eval_suite(
                input=input,
                task_contract_id=task_contract_id,
                project_id=project_id,
            )
        )

    def get_regression_report(self, contract_id: str | None = None) -> RegressionReport:
        """Get the regression delta report for the latest two eval suite runs."""
        return self._run(
            self._async_client.get_regression_report(contract_id=contract_id)
        )

    # --- API Keys ---

    def list_api_keys(self) -> list[ApiKey]:
        """List machine API keys for the organization."""
        return self._run(self._async_client.list_api_keys())

    def create_api_key(
        self,
        input: CreateApiKeyInput | dict[str, Any],
    ) -> CreateApiKeyResponse:
        """Create a new machine API key.

        The ``raw_key`` in the response is returned **only once**.
        """
        return self._run(self._async_client.create_api_key(input=input))

    def revoke_api_key(self, key_id: str) -> ApiKey:
        """Revoke a machine API key by ID."""
        return self._run(self._async_client.revoke_api_key(key_id=key_id))

    # --- MCP Servers ---

    def list_mcp_servers(self) -> list[McpServerRegistration]:
        """List registered MCP servers for the organization."""
        return self._run(self._async_client.list_mcp_servers())

    # --- Audit Logs & Observability ---

    def list_audit_logs(self, limit: int = 50) -> list[AuditLogEntry]:
        """List recent audit log entries for the organization."""
        return self._run(self._async_client.list_audit_logs(limit=limit))

    def get_dashboard(self) -> dict[str, Any]:
        """Get observability dashboard metrics for the organization."""
        return self._run(self._async_client.get_dashboard())


AgentReadyClient = GovernanceClient

_DEFAULT_SYNC_CLIENT: GovernanceClient | None = None


def get_default_client() -> GovernanceClient:
    """Return or initialize the default GovernanceClient singleton."""
    global _DEFAULT_SYNC_CLIENT
    if _DEFAULT_SYNC_CLIENT is None:
        _DEFAULT_SYNC_CLIENT = GovernanceClient()
    return _DEFAULT_SYNC_CLIENT


def set_default_client(client: GovernanceClient | None) -> None:
    """Set or clear the default GovernanceClient singleton."""
    global _DEFAULT_SYNC_CLIENT
    _DEFAULT_SYNC_CLIENT = client
