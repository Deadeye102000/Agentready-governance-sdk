# AgentReady Governance SDK

Official Python client library for the **AgentReady Governance Platform**.

The `agentready-governance-sdk` enables any Python AI agent framework (LangGraph, AutoGen, LlamaIndex, or custom agent loops) to integrate directly into enterprise governance controls—including real-time policy evaluation, human-in-the-loop (HITL) approval gates, capability feature flags, audit logging, and high-throughput tool call tracing—without writing custom security infrastructure.

---

## ⚡ Key Features

- **Dual Async/Sync Clients**: Choice between `AsyncGovernanceClient` (built on `httpx.AsyncClient`) and `GovernanceClient` (synchronous wrapper) with identical API signatures.
- **Typed Pydantic V2 Models**: Strictly validated domain entities with automatic `snake_case` Python attribute mapping and `camelCase` JSON serialization.
- **Human-In-The-Loop Workflow**: Built-in state machine (`wait_for_approval`) for handling gated execution approval polling, automated timeout management, and rejection detection.
- **Non-Blocking Tool Call Tracing**: High-throughput `record_tool_call` with `fire_and_forget=True` default to log agent tool execution traces in background tasks without blocking agent execution loops.
- **Resilient Transport**: Automatic retry policies using `tenacity` for transient network failures (429 Rate Limits and 500 Internal Server Errors), with support for HTTP `Retry-After` headers.

---

## 📦 Installation

Install via `pip`:

```bash
pip install agentready-governance-sdk
```

Or using `poetry`:

```bash
poetry add agentready-governance-sdk
```

---

## 🚀 Quickstart

### Asynchronous Client (`AsyncGovernanceClient`)

The standard workflow involves declaring an execution objective, waiting for governance gate approvals if required, and recording tool call traces:

```python
import asyncio
from agentready_governance_sdk import (
    AsyncGovernanceClient,
    CreateExecutionInput,
    CreateToolCallTraceInput,
    ExecutionStatus,
    ToolCallStatus,
)

async def main():
    async with AsyncGovernanceClient(api_key="agt_secret_key_123") as client:
        # 1. Register an agent execution request
        execution = await client.create_execution(
            CreateExecutionInput(
                project_id="proj_compliance",
                agent_id="agent_sre_bot",
                objective="Execute production database schema migration",
                risk_score=85,
            )
        )
        print(f"Execution initialized: {execution.id} (Status: {execution.status})")

        # 2. If gated by policy, wait for manual human approval
        if execution.status == ExecutionStatus.WAITING_FOR_APPROVAL:
            print("Execution requires human approval. Polling for decision...")
            execution = await client.wait_for_approval(
                execution_id=execution.id,
                poll_interval=2.0,
                timeout=300.0,
            )

        print(f"Execution approved and running: {execution.status}")

        # 3. Record tool call traces (non-blocking fire-and-forget by default)
        await client.record_tool_call(
            CreateToolCallTraceInput(
                execution_id=execution.id,
                agent_id="agent_sre_bot",
                tool_name="db_migrate",
                status=ToolCallStatus.SUCCEEDED,
                input={"target_version": "2.4.0"},
                latency_ms=145,
            ),
            fire_and_forget=True,
        )

        # 4. Mark execution complete
        await client.update_execution(
            execution.id,
            {"status": ExecutionStatus.SUCCEEDED, "output": {"migrated": True}},
        )

if __name__ == "__main__":
    asyncio.run(main())
```

---

### Synchronous Client (`GovernanceClient`)

For traditional synchronous agent runtime loops, use `GovernanceClient`:

```python
from agentready_governance_sdk import GovernanceClient, ExecutionStatus

with GovernanceClient(api_key="agt_secret_key_123") as client:
    # Check feature flags before executing restricted action
    flags = client.list_feature_flags(agent_id="agent_sre_bot")
    print(f"Active feature flags: {len(flags)}")

    execution = client.create_execution(
        {
            "projectId": "proj_compliance",
            "agentId": "agent_sre_bot",
            "objective": "Inspect audit logs",
        }
    )

    if execution.status == ExecutionStatus.WAITING_FOR_APPROVAL:
        execution = client.wait_for_approval(execution.id, timeout=60.0)

    # Sync tool recording always blocks and returns the ToolCallTrace
    trace = client.record_tool_call(
        {
            "executionId": execution.id,
            "agentId": "agent_sre_bot",
            "toolName": "fetch_logs",
            "status": "SUCCEEDED",
        }
    )
    print(f"Trace recorded: {trace.id}")
```

---

## ⚡ Non-Blocking Tool Tracing (`fire_and_forget`)

Agent tool tracing can generate high throughput during multi-step reasoning loops. By default, `record_tool_call(..., fire_and_forget=True)` dispatches the HTTP `POST` request to an internal background `asyncio.Task` and returns `None` instantly.

```python
# Returns None immediately — request completes in background
await client.record_tool_call(trace_input, fire_and_forget=True)

# Awaits response HTTP status and returns parsed ToolCallTrace
trace = await client.record_tool_call(trace_input, fire_and_forget=False)
```

The client tracks pending background tasks and guarantees their completion when calling `await client.close()` or exiting an `async with` block.

---

## 🛡 Exception Hierarchy

All SDK exceptions inherit from `AgentReadyError`. API response errors inherit from `AgentReadyAPIError` and include `status_code`, `code`, `message`, and structured `details`.

| Exception Class | Base Class | HTTP Status | Error Code | Description |
| :--- | :--- | :---: | :--- | :--- |
| `AgentReadyError` | `Exception` | - | - | Base class for all SDK exceptions |
| `AgentReadyAPIError` | `AgentReadyError` | `4xx` / `5xx` | Variable | Base class for HTTP API response errors |
| `ValidationError` | `AgentReadyAPIError` | `400` | `VALIDATION_ERROR` | Request payload or parameter validation failed |
| `AuthenticationError` | `AgentReadyAPIError` | `401` | `UNAUTHENTICATED` | Missing or invalid API key credential |
| `PermissionDeniedError` | `AgentReadyAPIError` | `403` | `PERMISSION_DENIED` | Tenant mismatch or insufficient user/agent role |
| `InsufficientScopeError` | `PermissionDeniedError` | `403` | `INSUFFICIENT_SCOPE` | API key lacks required scope for action |
| `ApprovalRequiredError` | `AgentReadyAPIError` | `403` | `APPROVAL_REQUIRED` | Capability gated by policy requiring human approval |
| `NotFoundError` | `AgentReadyAPIError` | `404` | `NOT_FOUND` | Requested entity (execution, gate, flag) not found |
| `ConflictError` | `AgentReadyAPIError` | `409` | `CONFLICT` | Entity conflict (e.g. duplicate gate capability) |
| `PayloadTooLargeError` | `AgentReadyAPIError` | `413` | `PAYLOAD_TOO_LARGE` | Request payload exceeds maximum server byte size |
| `RateLimitError` | `AgentReadyAPIError` | `429` | `RATE_LIMIT_EXCEEDED` | Request limit reached (carries `retry_after` if header present) |
| `InternalServerError` | `AgentReadyAPIError` | `500` | `INTERNAL_SERVER_ERROR` | Unexpected server-side failure |
| `ApprovalTimeoutError` | `AgentReadyError` | - | - | SDK control flow exception when `wait_for_approval` times out |
| `ApprovalRejectedError` | `AgentReadyError` | - | - | SDK control flow exception when execution status is `FAILED` or `CANCELLED` |

---

## ⚙️ Client Configuration Options

Both `AsyncGovernanceClient` and `GovernanceClient` accept the following optional parameters:

```python
client = AsyncGovernanceClient(
    api_key="agt_secret_key_123",
    base_url="http://localhost:3001",  # Governance API server endpoint
    timeout=30.0,                       # Timeout per HTTP request in seconds
    max_retries=3,                      # Retry attempts for transient 429/500 errors
)
```

---

## 🧪 License

MIT License. See `LICENSE` for details.
