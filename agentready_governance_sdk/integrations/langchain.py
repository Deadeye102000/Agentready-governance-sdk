"""LangChain and LangGraph integration callback handler for AgentReady governance."""

from __future__ import annotations

import asyncio
import inspect
import json
import time
from typing import Any

from agentready_governance_sdk.context import (
    get_current_client,
    get_current_execution_id,
)
from agentready_governance_sdk.exceptions import (
    AgentReadyError,
    ApprovalRequiredError,
    ToolBlockedError,
)
from agentready_governance_sdk.sync_client import get_default_client

try:
    from langchain_core.callbacks.base import BaseCallbackHandler

    HAS_LANGCHAIN = True
except ImportError:
    # Graceful fallback placeholder class
    class BaseCallbackHandler:  # type: ignore[no-redef]
        """Placeholder when langchain-core is not installed."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

    HAS_LANGCHAIN = False


def _resolve_decision(check_result: Any) -> str:
    decision = getattr(check_result, "decision", None)
    if decision is None:
        decision = getattr(check_result, "status", None)
    if decision is None and isinstance(check_result, dict):
        decision = (
            check_result.get("decision")
            or check_result.get("status")
            or check_result.get("mode")
        )
    if hasattr(decision, "value"):
        return str(decision.value).upper()
    return str(decision or "").upper()


class AgentReadyCallbackHandler(BaseCallbackHandler):
    """LangChain / LangGraph callback handler providing automated AgentReady governance.

    Intercepts tool calls in ``on_tool_start``, performs pre-flight checks,
    and logs audited results in ``on_tool_end`` and ``on_tool_error``.
    """

    def __init__(
        self,
        execution_id: str | None = None,
        client: Any | None = None,
        raise_on_blocked: bool = True,
        wait_for_approval: bool = False,
        poll_interval: float = 2.0,
        timeout: float = 300.0,
        **kwargs: Any,
    ) -> None:
        if not HAS_LANGCHAIN:
            raise ImportError(
                "langchain-core is not installed. Please install it using "
                "'pip install agentready-governance-sdk[langchain]' "
                "or 'pip install langchain-core'."
            )
        super().__init__(**kwargs)
        self.execution_id = execution_id
        self._client = client
        self.raise_on_blocked = raise_on_blocked
        self.wait_for_approval = wait_for_approval
        self.poll_interval = poll_interval
        self.timeout = timeout
        self._runs: dict[str, dict[str, Any]] = {}

    @property
    def client(self) -> Any:
        if self._client is not None:
            return self._client
        return get_current_client() or get_default_client()

    def _extract_arguments(
        self, input_str: str, inputs: dict[str, Any] | None
    ) -> dict[str, Any]:
        if inputs is not None and isinstance(inputs, dict):
            return inputs
        if isinstance(input_str, str):
            clean = input_str.strip()
            if clean.startswith("{") and clean.endswith("}"):
                try:
                    parsed = json.loads(clean)
                    if isinstance(parsed, dict):
                        return parsed
                except Exception:
                    pass
            return {"input": input_str}
        return {"input": input_str}

    def _resolve_tool_name(self, serialized: dict[str, Any]) -> str:
        tool_name = serialized.get("name")
        if not tool_name and "id" in serialized:
            id_val = serialized["id"]
            if isinstance(id_val, list) and id_val:
                tool_name = id_val[-1]
            elif isinstance(id_val, str):
                tool_name = id_val
        return tool_name or "unknown_tool"

    def _resolve_execution_id(
        self, metadata: dict[str, Any] | None, tool_name: str
    ) -> str:
        meta = metadata or {}
        target_exec_id = (
            self.execution_id or meta.get("execution_id") or get_current_execution_id()
        )
        if not target_exec_id:
            raise AgentReadyError(
                f"execution_id must be provided to AgentReadyCallbackHandler "
                f"for tool '{tool_name}' or set via context."
            )
        return target_exec_id

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: Any = None,
        parent_run_id: Any = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        inputs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Intercept tool call, validate against AgentReady governance control plane."""
        tool_name = self._resolve_tool_name(serialized)
        target_exec_id = self._resolve_execution_id(metadata, tool_name)
        arguments = self._extract_arguments(input_str, inputs)

        client = self.client
        check_fn = getattr(client, "check_tool_call")
        if inspect.iscoroutinefunction(check_fn):
            # In sync on_tool_start with async client
            try:
                asyncio.get_running_loop()
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    check_result = executor.submit(
                        asyncio.run,
                        check_fn(
                            execution_id=target_exec_id,
                            tool_name=tool_name,
                            arguments=arguments,
                        ),
                    ).result()
            except RuntimeError:
                check_result = asyncio.run(
                    check_fn(
                        execution_id=target_exec_id,
                        tool_name=tool_name,
                        arguments=arguments,
                    )
                )
        else:
            check_result = check_fn(
                execution_id=target_exec_id,
                tool_name=tool_name,
                arguments=arguments,
            )

        decision = _resolve_decision(check_result)
        trace_id = getattr(check_result, "tool_call_trace_id", None)
        if trace_id is None and isinstance(check_result, dict):
            trace_id = check_result.get("tool_call_trace_id") or check_result.get(
                "traceId"
            )

        if decision in ("BLOCKED", "BLOCK"):
            reason = getattr(check_result, "reason", "Tool execution blocked by policy")
            risk_score = getattr(check_result, "risk_score", None)
            if self.raise_on_blocked:
                raise ToolBlockedError(
                    reason=reason,
                    tool_name=tool_name,
                    risk_score=risk_score,
                )

        if decision in ("WAIT_FOR_APPROVAL", "AWAITING_APPROVAL", "REQUIRE_APPROVAL"):
            approval_req_id = getattr(check_result, "approval_request_id", None)
            if approval_req_id is None and isinstance(check_result, dict):
                approval_req_id = check_result.get(
                    "approval_request_id"
                ) or check_result.get("approvalRequestId")

            if not self.wait_for_approval:
                raise ApprovalRequiredError(
                    approval_request_id=approval_req_id,
                    tool_name=tool_name,
                    execution_id=target_exec_id,
                )

            # Wait for approval
            wait_fn = getattr(client, "wait_for_approval")
            if inspect.iscoroutinefunction(wait_fn):
                asyncio.run(
                    wait_fn(
                        target_exec_id,
                        poll_interval=self.poll_interval,
                        timeout=self.timeout,
                    )
                )
            else:
                wait_fn(
                    target_exec_id,
                    poll_interval=self.poll_interval,
                    timeout=self.timeout,
                )

        run_key = str(run_id) if run_id is not None else tool_name
        self._runs[run_key] = {
            "trace_id": trace_id,
            "start_time": time.perf_counter(),
            "tool_name": tool_name,
            "execution_id": target_exec_id,
        }

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: Any = None,
        parent_run_id: Any = None,
        **kwargs: Any,
    ) -> Any:
        """Report successful tool execution to AgentReady trace ledger."""
        run_key = str(run_id) if run_id is not None else None
        run_info = self._runs.pop(run_key, None) if run_key else None
        if not run_info and self._runs:
            run_key, run_info = self._runs.popitem()

        start_time = run_info.get("start_time") if run_info else None
        trace_id = run_info.get("trace_id") if run_info else None
        latency_ms = int((time.perf_counter() - start_time) * 1000) if start_time else 0

        if trace_id:
            report_fn = getattr(
                self.client,
                "report_tool_result",
                getattr(self.client, "report_tool_call_result", None),
            )
            if report_fn:
                payload = {
                    "status": "SUCCEEDED",
                    "output": output,
                    "latencyMs": latency_ms,
                }
                if inspect.iscoroutinefunction(report_fn):
                    try:
                        asyncio.run(report_fn(trace_id, payload))
                    except Exception:
                        pass
                else:
                    report_fn(trace_id, payload)

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: Any = None,
        parent_run_id: Any = None,
        **kwargs: Any,
    ) -> Any:
        """Report failed tool execution to AgentReady trace ledger."""
        run_key = str(run_id) if run_id is not None else None
        run_info = self._runs.pop(run_key, None) if run_key else None
        if not run_info and self._runs:
            run_key, run_info = self._runs.popitem()

        start_time = run_info.get("start_time") if run_info else None
        trace_id = run_info.get("trace_id") if run_info else None
        latency_ms = int((time.perf_counter() - start_time) * 1000) if start_time else 0

        if trace_id:
            report_fn = getattr(
                self.client,
                "report_tool_result",
                getattr(self.client, "report_tool_call_result", None),
            )
            if report_fn:
                payload = {
                    "status": "FAILED",
                    "error": str(error),
                    "latencyMs": latency_ms,
                }
                try:
                    if inspect.iscoroutinefunction(report_fn):
                        asyncio.run(report_fn(trace_id, payload))
                    else:
                        report_fn(trace_id, payload)
                except Exception:
                    pass
