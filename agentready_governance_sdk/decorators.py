"""Universal tool guard decorator for AgentReady governance."""

from __future__ import annotations

import functools
import inspect
import time
from typing import Any, Callable, TypeVar, cast

from agentready_governance_sdk.client import get_default_async_client
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

F = TypeVar("F", bound=Callable[..., Any])


def _resolve_decision(check_result: Any) -> str:
    """Normalize decision string from CheckToolCallResult or dictionary."""
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


def _extract_arguments(
    fn: Callable[..., Any], args: tuple[Any, ...], kwargs: dict[str, Any]
) -> dict[str, Any]:
    """Extract tool arguments mapping names to values using function signature."""
    try:
        sig = inspect.signature(fn)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        # Exclude self or cls if method
        params = list(sig.parameters.values())
        arguments = dict(bound.arguments)
        if params and params[0].name in ("self", "cls") and params[0].name in arguments:
            arguments.pop(params[0].name)
        return arguments
    except (TypeError, ValueError):
        arguments = dict(kwargs)
        for i, arg in enumerate(args):
            arguments[f"arg_{i}"] = arg
        return arguments


def guard_tool(
    func: F | None = None,
    *,
    tool_name: str | None = None,
    execution_id: str | None = None,
    client: Any | None = None,
    raise_on_blocked: bool = True,
    wait_for_approval: bool = False,
    poll_interval: float = 2.0,
    timeout: float = 300.0,
) -> Any:
    """Decorator to guard Python functions and async functions with AgentReady
    governance.


    Parameters:
        func: The function to decorate (when used as ``@guard_tool``).
        tool_name: Custom tool name (defaults to ``func.__name__``).
        execution_id: Execution ID for the tool call (or resolved from context/kwargs).
        client: Optional AgentReady client (defaults to context or global client).
        raise_on_blocked: If True, raises ``ToolBlockedError`` on block.
        wait_for_approval: If True, waits for approval via client polling.
        poll_interval: Seconds between approval poll attempts.
        timeout: Timeout in seconds when waiting for approval.
    """

    def decorator(fn: F) -> F:
        resolved_tool_name = tool_name or getattr(fn, "__name__", "unknown_tool")
        is_async = inspect.iscoroutinefunction(fn)

        if is_async:

            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                nonlocal client, execution_id

                # Resolve execution_id
                target_exec_id = (
                    execution_id
                    or kwargs.get("execution_id")
                    or get_current_execution_id()
                )
                if not target_exec_id:
                    raise AgentReadyError(
                        f"execution_id must be provided to @guard_tool for "
                        f"'{resolved_tool_name}' or set via context."
                    )

                # Filter kwargs if fn does not accept execution_id
                call_kwargs = dict(kwargs)
                sig = inspect.signature(fn)
                if (
                    "execution_id" in call_kwargs
                    and "execution_id" not in sig.parameters
                    and not any(
                        p.kind == inspect.Parameter.VAR_KEYWORD
                        for p in sig.parameters.values()
                    )
                ):
                    call_kwargs.pop("execution_id")

                tool_args = _extract_arguments(fn, args, kwargs)

                # Resolve client
                target_client = (
                    client or get_current_client() or get_default_async_client()
                )

                # Call check_tool_call
                check_fn = getattr(target_client, "check_tool_call")
                if inspect.iscoroutinefunction(check_fn):
                    check_result = await check_fn(
                        execution_id=target_exec_id,
                        tool_name=resolved_tool_name,
                        arguments=tool_args,
                    )
                else:
                    check_result = check_fn(
                        execution_id=target_exec_id,
                        tool_name=resolved_tool_name,
                        arguments=tool_args,
                    )

                decision = _resolve_decision(check_result)
                trace_id = getattr(check_result, "tool_call_trace_id", None)
                if trace_id is None and isinstance(check_result, dict):
                    trace_id = check_result.get(
                        "tool_call_trace_id"
                    ) or check_result.get("traceId")

                if decision in ("BLOCKED", "BLOCK"):
                    reason = getattr(
                        check_result, "reason", "Tool execution blocked by policy"
                    )
                    risk_score = getattr(check_result, "risk_score", None)
                    if raise_on_blocked:
                        raise ToolBlockedError(
                            reason=reason,
                            tool_name=resolved_tool_name,
                            risk_score=risk_score,
                        )
                    return {
                        "status": "BLOCKED",
                        "reason": reason,
                        "tool_name": resolved_tool_name,
                    }

                if decision in (
                    "WAIT_FOR_APPROVAL",
                    "AWAITING_APPROVAL",
                    "REQUIRE_APPROVAL",
                ):
                    approval_req_id = getattr(check_result, "approval_request_id", None)
                    if approval_req_id is None and isinstance(check_result, dict):
                        approval_req_id = check_result.get(
                            "approval_request_id"
                        ) or check_result.get("approvalRequestId")

                    if not wait_for_approval:
                        raise ApprovalRequiredError(
                            approval_request_id=approval_req_id,
                            tool_name=resolved_tool_name,
                            execution_id=target_exec_id,
                        )

                    # Poll for approval
                    wait_fn = getattr(target_client, "wait_for_approval")
                    if inspect.iscoroutinefunction(wait_fn):
                        await wait_fn(
                            target_exec_id, poll_interval=poll_interval, timeout=timeout
                        )
                    else:
                        wait_fn(
                            target_exec_id, poll_interval=poll_interval, timeout=timeout
                        )

                # Execute tool
                start_time = time.perf_counter()
                report_fn = getattr(
                    target_client,
                    "report_tool_result",
                    getattr(target_client, "report_tool_call_result", None),
                )

                try:
                    res = await fn(*args, **call_kwargs)
                    latency_ms = int((time.perf_counter() - start_time) * 1000)

                    if trace_id and report_fn:
                        payload = {
                            "status": "SUCCEEDED",
                            "output": res,
                            "latencyMs": latency_ms,
                        }
                        if inspect.iscoroutinefunction(report_fn):
                            await report_fn(trace_id, payload)
                        else:
                            report_fn(trace_id, payload)
                    return res
                except Exception as err:
                    latency_ms = int((time.perf_counter() - start_time) * 1000)
                    if trace_id and report_fn:
                        payload = {
                            "status": "FAILED",
                            "error": str(err),
                            "latencyMs": latency_ms,
                        }
                        try:
                            if inspect.iscoroutinefunction(report_fn):
                                await report_fn(trace_id, payload)
                            else:
                                report_fn(trace_id, payload)
                        except Exception:
                            pass
                    raise

            return cast(F, async_wrapper)

        else:

            @functools.wraps(fn)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                nonlocal client, execution_id

                # Resolve execution_id
                target_exec_id = (
                    execution_id
                    or kwargs.get("execution_id")
                    or get_current_execution_id()
                )
                if not target_exec_id:
                    raise AgentReadyError(
                        f"execution_id must be provided to @guard_tool for "
                        f"'{resolved_tool_name}' or set via context."
                    )

                # Filter kwargs if fn does not accept execution_id
                call_kwargs = dict(kwargs)
                sig = inspect.signature(fn)
                if (
                    "execution_id" in call_kwargs
                    and "execution_id" not in sig.parameters
                    and not any(
                        p.kind == inspect.Parameter.VAR_KEYWORD
                        for p in sig.parameters.values()
                    )
                ):
                    call_kwargs.pop("execution_id")

                tool_args = _extract_arguments(fn, args, kwargs)

                # Resolve client
                target_client = client or get_current_client() or get_default_client()

                check_fn = getattr(target_client, "check_tool_call")
                check_result = check_fn(
                    execution_id=target_exec_id,
                    tool_name=resolved_tool_name,
                    arguments=tool_args,
                )

                decision = _resolve_decision(check_result)
                trace_id = getattr(check_result, "tool_call_trace_id", None)
                if trace_id is None and isinstance(check_result, dict):
                    trace_id = check_result.get(
                        "tool_call_trace_id"
                    ) or check_result.get("traceId")

                if decision in ("BLOCKED", "BLOCK"):
                    reason = getattr(
                        check_result, "reason", "Tool execution blocked by policy"
                    )
                    risk_score = getattr(check_result, "risk_score", None)
                    if raise_on_blocked:
                        raise ToolBlockedError(
                            reason=reason,
                            tool_name=resolved_tool_name,
                            risk_score=risk_score,
                        )
                    return {
                        "status": "BLOCKED",
                        "reason": reason,
                        "tool_name": resolved_tool_name,
                    }

                if decision in (
                    "WAIT_FOR_APPROVAL",
                    "AWAITING_APPROVAL",
                    "REQUIRE_APPROVAL",
                ):
                    approval_req_id = getattr(check_result, "approval_request_id", None)
                    if approval_req_id is None and isinstance(check_result, dict):
                        approval_req_id = check_result.get(
                            "approval_request_id"
                        ) or check_result.get("approvalRequestId")

                    if not wait_for_approval:
                        raise ApprovalRequiredError(
                            approval_request_id=approval_req_id,
                            tool_name=resolved_tool_name,
                            execution_id=target_exec_id,
                        )

                    # Poll for approval
                    wait_fn = getattr(target_client, "wait_for_approval")
                    wait_fn(
                        target_exec_id, poll_interval=poll_interval, timeout=timeout
                    )

                # Execute tool
                start_time = time.perf_counter()
                report_fn = getattr(
                    target_client,
                    "report_tool_result",
                    getattr(target_client, "report_tool_call_result", None),
                )

                try:
                    res = fn(*args, **call_kwargs)
                    latency_ms = int((time.perf_counter() - start_time) * 1000)

                    if trace_id and report_fn:
                        payload = {
                            "status": "SUCCEEDED",
                            "output": res,
                            "latencyMs": latency_ms,
                        }
                        report_fn(trace_id, payload)
                    return res
                except Exception as err:
                    latency_ms = int((time.perf_counter() - start_time) * 1000)
                    if trace_id and report_fn:
                        payload = {
                            "status": "FAILED",
                            "error": str(err),
                            "latencyMs": latency_ms,
                        }
                        try:
                            report_fn(trace_id, payload)
                        except Exception:
                            pass
                    raise

            return cast(F, sync_wrapper)

    if func is not None:
        return decorator(func)
    return decorator
