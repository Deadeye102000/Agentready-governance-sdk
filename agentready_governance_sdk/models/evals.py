"""Evaluation run and case models for AgentReady SDK."""

from datetime import datetime
from typing import Any

from pydantic import Field

from agentready_governance_sdk.models.base import BaseApiModel
from agentready_governance_sdk.models.common import EvalRunStatus


class EvalCase(BaseApiModel):
    """An evaluation case linked to a task contract."""

    id: str
    organization_id: str
    task_contract_id: str
    name: str
    input: dict[str, Any] = Field(default_factory=dict)
    expected_status: str | None = None
    expected_tools: list[str] = Field(default_factory=list)
    success_criteria: str | None = None
    created_at: datetime
    updated_at: datetime


class CreateEvalCaseInput(BaseApiModel):
    """Input for creating an eval case."""

    task_contract_id: str
    name: str
    input: dict[str, Any] = Field(default_factory=dict)
    expected_status: str | None = None
    expected_tools: list[str] = Field(default_factory=list)
    success_criteria: str | None = None


class EvalRun(BaseApiModel):
    """An evaluation run record."""

    id: str
    organization_id: str
    project_id: str
    execution_id: str | None = None
    contract_id: str | None = None
    agent_id: str | None = None
    eval_case_id: str | None = None
    name: str
    status: EvalRunStatus = EvalRunStatus.QUEUED
    score: float | None = None
    trajectory_score: float | None = None
    threshold: float = 0.8
    checks: list[dict[str, Any]] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)
    violations: list[str] | None = None
    failure_reason: str | None = None
    duration: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class CreateEvalRunInput(BaseApiModel):
    """Input for creating an eval run."""

    project_id: str
    name: str
    execution_id: str | None = None
    contract_id: str | None = None
    agent_id: str | None = None
    eval_case_id: str | None = None
    threshold: float = 0.8


class RegressionReport(BaseApiModel):
    """Regression delta report comparing the latest two eval suites."""

    previous_score: float | None = None
    current_score: float | None = None
    delta: float | None = None
    previous_pass_rate: float | None = None
    current_pass_rate: float | None = None
    pass_rate_change: float | None = None
    newly_failing: list[dict[str, str]] = Field(default_factory=list)
    newly_passing: list[dict[str, str]] = Field(default_factory=list)


class RunEvalSuiteInput(BaseApiModel):
    """Input for triggering an eval suite run."""

    task_contract_id: str | None = None
    project_id: str | None = None
