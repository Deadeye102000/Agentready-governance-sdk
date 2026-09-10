"""Task contract and trajectory policy models for AgentReady SDK."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field

from agentready_governance_sdk.models.base import BaseApiModel


class TrajectoryMode(str, Enum):
    """Matching mode for trajectory evaluation (mirrors TypeScript evaluator.ts)."""

    STRICT_SEQUENCE = "STRICT_SEQUENCE"
    SUBSEQUENCE = "SUBSEQUENCE"
    UNORDERED = "UNORDERED"


class ExpectedStep(BaseApiModel):
    """A single expected step in a trajectory policy.

    Field names match the TypeScript ``ExpectedStep`` interface exactly so that
    the shared JSON fixture file (``tests/fixtures/trajectory_eval_cases.json``)
    is valid input for both evaluators without translation.
    """

    tool: str
    required: bool = True
    expected_gate_status: str | None = None
    expected_args: dict[str, Any] | None = None


class TrajectoryPolicy(BaseApiModel):
    """Trajectory policy attached to a task contract.

    Field names mirror ``TrajectoryPolicy`` in
    ``packages/agent-contracts/src/evaluator.ts``.
    """

    mode: TrajectoryMode = TrajectoryMode.STRICT_SEQUENCE
    expected_steps: list[ExpectedStep] = Field(default_factory=list)
    forbidden_tools: list[str] = Field(default_factory=list)
    max_tool_calls: int | None = None


class TrajectoryEvaluationResult(BaseApiModel):
    """Result of evaluating a trace against a trajectory policy.

    Field names mirror ``TrajectoryEvaluation`` in
    ``packages/agent-contracts/src/evaluator.ts``.
    """

    passed: bool
    score: float  # 0.0–1.0, rounded to 2 dp
    matched_steps: int
    total_expected: int
    violations: list[str]


class TaskContract(BaseApiModel):
    """Task contract entity."""

    id: str
    organization_id: str
    project_id: str
    task_id: str | None = None
    agent_id: str | None = None
    name: str
    version: int = 1
    objective: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    success_criteria: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    required_approvals: list[str] = Field(default_factory=list)
    eval_spec: dict[str, Any] = Field(default_factory=dict)
    trajectory_policy: TrajectoryPolicy | None = None
    created_at: datetime
    updated_at: datetime


class CreateTaskContractInput(BaseApiModel):
    """Input for creating a new task contract."""

    project_id: str
    name: str
    objective: str
    task_id: str | None = None
    agent_id: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    success_criteria: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    required_approvals: list[str] = Field(default_factory=list)
    eval_spec: dict[str, Any] = Field(default_factory=dict)
    trajectory_policy: TrajectoryPolicy | dict[str, Any] | None = None


class PatchTaskContractInput(BaseApiModel):
    """Input for partially updating a task contract."""

    name: str | None = None
    objective: str | None = None
    inputs: dict[str, Any] | None = None
    success_criteria: list[str] | None = None
    allowed_tools: list[str] | None = None
    required_approvals: list[str] | None = None
    eval_spec: dict[str, Any] | None = None
    trajectory_policy: TrajectoryPolicy | dict[str, Any] | None = None
