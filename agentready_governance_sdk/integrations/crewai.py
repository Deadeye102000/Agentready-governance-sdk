"""CrewAI integration adapter and tool guards for AgentReady governance."""

from __future__ import annotations

import asyncio
import functools
import inspect
import time
from typing import Any, TypeVar

from agentready_governance_sdk.context import (
    get_current_client,
    get_current_execution_id,
)
from agentready_governance_sdk.decorators import _extract_arguments, _resolve_decision
from agentready_governance_sdk.exceptions import (
    AgentReadyError,
    ApprovalRequiredError,
    ToolBlockedError,
)
from agentready_governance_sdk.sync_client import get_default_client

try:
    from crewai.tools import BaseTool

    HAS_CREWAI = True
except ImportError:
    # Graceful fallback placeholder class
    class BaseTool:  # type: ignore[no-redef]
        """Placeholder when crewai is not installed."""

        name: str = ""
        description: str = ""

        def _run(self, *args: Any, **kwargs: Any) -> Any:
            raise NotImplementedError

        async def _arun(self, *args: Any, **kwargs: Any) -> Any:
            raise NotImplementedError

    HAS_CREWAI = False

T = TypeVar("T")


def _run_preflight(
    tool_name: str,
    arguments: dict[str, Any],
    execution_id: str | None,
    client: Any | None,
    raise_on_blocked: bool,
    wait_for_approval: bool,
    poll_interval: float,
    timeout: float,
) -> tuple[str | None, str]:
    target_exec_id = execution_id or get_current_execution_id()
    if not target_exec_id:
        raise AgentReadyError(
            f"execution_id must be provided to AgentReadyCrewAITool for '{tool_name}' "
            "or set via context (e.g. 'with agentready_execution(...)')."
        )

    target_client = client or get_current_client() or get_default_client()
    check_fn = getattr(target_client, "check_tool_call")
    if inspect.iscoroutinefunction(check_fn):
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
        trace_id = check_result.get("tool_call_trace_id") or check_result.get("traceId")

    if decision in ("BLOCKED", "BLOCK"):
        reason = getattr(check_result, "reason", "Tool execution blocked by policy")
        risk_score = getattr(check_result, "risk_score", None)
        if raise_on_blocked:
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

        if not wait_for_approval:
            raise ApprovalRequiredError(
                approval_request_id=approval_req_id,
                tool_name=tool_name,
                execution_id=target_exec_id,
            )

        wait_fn = getattr(target_client, "wait_for_approval")
        if inspect.iscoroutinefunction(wait_fn):
            asyncio.run(
                wait_fn(target_exec_id, poll_interval=poll_interval, timeout=timeout)
            )
        else:
            wait_fn(target_exec_id, poll_interval=poll_interval, timeout=timeout)

    return trace_id, target_exec_id


async def _run_preflight_async(
    tool_name: str,
    arguments: dict[str, Any],
    execution_id: str | None,
    client: Any | None,
    raise_on_blocked: bool,
    wait_for_approval: bool,
    poll_interval: float,
    timeout: float,
) -> tuple[str | None, str]:
    target_exec_id = execution_id or get_current_execution_id()
    if not target_exec_id:
        raise AgentReadyError(
            f"execution_id must be provided to AgentReadyCrewAITool for '{tool_name}' "
            "or set via context (e.g. 'with agentready_execution(...)')."
        )

    target_client = client or get_current_client() or get_default_client()
    check_fn = getattr(target_client, "check_tool_call")
    if inspect.iscoroutinefunction(check_fn):
        check_result = await check_fn(
            execution_id=target_exec_id,
            tool_name=tool_name,
            arguments=arguments,
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
        trace_id = check_result.get("tool_call_trace_id") or check_result.get("traceId")

    if decision in ("BLOCKED", "BLOCK"):
        reason = getattr(check_result, "reason", "Tool execution blocked by policy")
        risk_score = getattr(check_result, "risk_score", None)
        if raise_on_blocked:
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

        if not wait_for_approval:
            raise ApprovalRequiredError(
                approval_request_id=approval_req_id,
                tool_name=tool_name,
                execution_id=target_exec_id,
            )

        wait_fn = getattr(target_client, "wait_for_approval")
        if inspect.iscoroutinefunction(wait_fn):
            await wait_fn(target_exec_id, poll_interval=poll_interval, timeout=timeout)
        else:
            wait_fn(target_exec_id, poll_interval=poll_interval, timeout=timeout)

    return trace_id, target_exec_id


def _run_postflight(
    trace_id: str | None,
    client: Any | None,
    output: Any,
    error: BaseException | None,
    latency_ms: int,
) -> None:
    if not trace_id:
        return
    target_client = client or get_current_client() or get_default_client()
    report_fn = getattr(
        target_client,
        "report_tool_result",
        getattr(target_client, "report_tool_call_result", None),
    )
    if not report_fn:
        return

    if error is not None:
        payload = {
            "status": "FAILED",
            "error": str(error),
            "latencyMs": latency_ms,
        }
    else:
        payload = {
            "status": "SUCCEEDED",
            "output": output,
            "latencyMs": latency_ms,
        }

    try:
        if inspect.iscoroutinefunction(report_fn):
            asyncio.run(report_fn(trace_id, payload))
        else:
            report_fn(trace_id, payload)
    except Exception:
        pass


async def _run_postflight_async(
    trace_id: str | None,
    client: Any | None,
    output: Any,
    error: BaseException | None,
    latency_ms: int,
) -> None:
    if not trace_id:
        return
    target_client = client or get_current_client() or get_default_client()
    report_fn = getattr(
        target_client,
        "report_tool_result",
        getattr(target_client, "report_tool_call_result", None),
    )
    if not report_fn:
        return

    if error is not None:
        payload = {
            "status": "FAILED",
            "error": str(error),
            "latencyMs": latency_ms,
        }
    else:
        payload = {
            "status": "SUCCEEDED",
            "output": output,
            "latencyMs": latency_ms,
        }

    try:
        if inspect.iscoroutinefunction(report_fn):
            await report_fn(trace_id, payload)
        else:
            report_fn(trace_id, payload)
    except Exception:
        pass


class AgentReadyCrewAITool:
    """Helper, wrapper, and mixin for CrewAI BaseTool governance.

    Can wrap existing CrewAI tools or be used as a decorator/wrapper.
    """

    def __new__(
        cls,
        tool: Any = None,
        *,
        execution_id: str | None = None,
        client: Any | None = None,
        raise_on_blocked: bool = True,
        wait_for_approval: bool = False,
        poll_interval: float = 2.0,
        timeout: float = 300.0,
        **kwargs: Any,
    ) -> Any:
        if tool is not None:
            # Used as wrapper: AgentReadyCrewAITool(original_tool, ...)
            return cls.wrap(
                tool,
                execution_id=execution_id,
                client=client,
                raise_on_blocked=raise_on_blocked,
                wait_for_approval=wait_for_approval,
                poll_interval=poll_interval,
                timeout=timeout,
            )
        instance = super().__new__(cls)
        return instance

    @classmethod
    def wrap(
        cls,
        tool: Any,
        *,
        execution_id: str | None = None,
        client: Any | None = None,
        raise_on_blocked: bool = True,
        wait_for_approval: bool = False,
        poll_interval: float = 2.0,
        timeout: float = 300.0,
    ) -> Any:
        """Wrap an existing CrewAI tool instance to intercept _run and _arun."""
        original_run = getattr(tool, "_run", None)
        original_arun = getattr(tool, "_arun", None)
        tool_name = getattr(tool, "name", getattr(tool, "__name__", "crewai_tool"))

        if original_run:

            @functools.wraps(original_run)
            def guarded_run(*args: Any, **kwargs: Any) -> Any:
                arguments = _extract_arguments(original_run, args, kwargs)
                trace_id, _ = _run_preflight(
                    tool_name=tool_name,
                    arguments=arguments,
                    execution_id=execution_id,
                    client=client,
                    raise_on_blocked=raise_on_blocked,
                    wait_for_approval=wait_for_approval,
                    poll_interval=poll_interval,
                    timeout=timeout,
                )
                start_time = time.perf_counter()
                try:
                    result = original_run(*args, **kwargs)
                    latency_ms = int((time.perf_counter() - start_time) * 1000)
                    _run_postflight(trace_id, client, result, None, latency_ms)
                    return result
                except BaseException as err:
                    latency_ms = int((time.perf_counter() - start_time) * 1000)
                    _run_postflight(trace_id, client, None, err, latency_ms)
                    raise

            object.__setattr__(tool, "_run", guarded_run)

        if original_arun:

            @functools.wraps(original_arun)
            async def guarded_arun(*args: Any, **kwargs: Any) -> Any:
                arguments = _extract_arguments(original_arun, args, kwargs)
                trace_id, _ = await _run_preflight_async(
                    tool_name=tool_name,
                    arguments=arguments,
                    execution_id=execution_id,
                    client=client,
                    raise_on_blocked=raise_on_blocked,
                    wait_for_approval=wait_for_approval,
                    poll_interval=poll_interval,
                    timeout=timeout,
                )
                start_time = time.perf_counter()
                try:
                    result = await original_arun(*args, **kwargs)
                    latency_ms = int((time.perf_counter() - start_time) * 1000)
                    await _run_postflight_async(
                        trace_id, client, result, None, latency_ms
                    )
                    return result
                except BaseException as err:
                    latency_ms = int((time.perf_counter() - start_time) * 1000)
                    await _run_postflight_async(trace_id, client, None, err, latency_ms)
                    raise

            object.__setattr__(tool, "_arun", guarded_arun)

        return tool


def guard_crew_tool(
    func_or_tool: Any = None,
    *,
    execution_id: str | None = None,
    tool_name: str | None = None,
    client: Any | None = None,
    raise_on_blocked: bool = True,
    wait_for_approval: bool = False,
    poll_interval: float = 2.0,
    timeout: float = 300.0,
) -> Any:
    """Decorator to guard CrewAI tools or functions annotated with CrewAI's ``@tool``.

    Can be applied either directly to a function or to a tool object
    produced by CrewAI's ``@tool``.
    """

    def decorator(target: Any) -> Any:
        # If target is already a CrewAI Tool object with _run method
        if hasattr(target, "_run") and not inspect.isfunction(target):
            return AgentReadyCrewAITool.wrap(
                target,
                execution_id=execution_id,
                client=client,
                raise_on_blocked=raise_on_blocked,
                wait_for_approval=wait_for_approval,
                poll_interval=poll_interval,
                timeout=timeout,
            )

        resolved_name = tool_name or getattr(target, "__name__", "crewai_tool")
        is_async = inspect.iscoroutinefunction(target)

        if is_async:

            @functools.wraps(target)
            async def async_guarded(*args: Any, **kwargs: Any) -> Any:
                arguments = _extract_arguments(target, args, kwargs)
                trace_id, _ = await _run_preflight_async(
                    tool_name=resolved_name,
                    arguments=arguments,
                    execution_id=execution_id,
                    client=client,
                    raise_on_blocked=raise_on_blocked,
                    wait_for_approval=wait_for_approval,
                    poll_interval=poll_interval,
                    timeout=timeout,
                )
                start_time = time.perf_counter()
                try:
                    result = await target(*args, **kwargs)
                    latency_ms = int((time.perf_counter() - start_time) * 1000)
                    await _run_postflight_async(
                        trace_id, client, result, None, latency_ms
                    )
                    return result
                except BaseException as err:
                    latency_ms = int((time.perf_counter() - start_time) * 1000)
                    await _run_postflight_async(trace_id, client, None, err, latency_ms)
                    raise

            return async_guarded

        else:

            @functools.wraps(target)
            def sync_guarded(*args: Any, **kwargs: Any) -> Any:
                arguments = _extract_arguments(target, args, kwargs)
                trace_id, _ = _run_preflight(
                    tool_name=resolved_name,
                    arguments=arguments,
                    execution_id=execution_id,
                    client=client,
                    raise_on_blocked=raise_on_blocked,
                    wait_for_approval=wait_for_approval,
                    poll_interval=poll_interval,
                    timeout=timeout,
                )
                start_time = time.perf_counter()
                try:
                    result = target(*args, **kwargs)
                    latency_ms = int((time.perf_counter() - start_time) * 1000)
                    _run_postflight(trace_id, client, result, None, latency_ms)
                    return result
                except BaseException as err:
                    latency_ms = int((time.perf_counter() - start_time) * 1000)
                    _run_postflight(trace_id, client, None, err, latency_ms)
                    raise

            return sync_guarded

    if func_or_tool is not None:
        return decorator(func_or_tool)
    return decorator
