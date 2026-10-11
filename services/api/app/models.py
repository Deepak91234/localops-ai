from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AgentStatus(str, Enum):
    idle = "idle"
    queued = "queued"
    running = "running"
    completed = "completed"
    error = "error"
    paused = "paused"
    blocked = "blocked"


class Permission(str, Enum):
    read_policy = "read_policy"
    analyze_invoices = "analyze_invoices"
    draft_support_reply = "draft_support_reply"
    inspect_permissions = "inspect_permissions"
    measure_scheduler = "measure_scheduler"


class AgentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=2, max_length=60)
    role: Literal["hr", "finance", "support"]
    purpose: str = Field(min_length=8, max_length=500)
    tools: list[Permission] = Field(min_length=1, max_length=3)
    source: Literal["handbook.txt", "invoices.csv", "support_tickets.json", "injection_policy.txt"]


class Agent(BaseModel):
    id: str
    name: str
    role: str
    purpose: str
    tools: list[str]
    source: str
    status: AgentStatus = AgentStatus.idle


class JobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    agent_id: str = Field(min_length=1, max_length=100)
    prompt: str = Field(min_length=3, max_length=4000)
    priority: Literal["standard", "urgent"] = "standard"


class Job(BaseModel):
    id: str
    agent_id: str
    type: str
    prompt: str
    priority: str
    status: AgentStatus
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)


class ActivityEvent(BaseModel):
    id: str
    type: str
    timestamp: str
    message: str
    agent_id: str | None = None
    job_id: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)


class OptimizationDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    policy: Literal["fifo", "priority"]
    approved: bool


class MetricSample(BaseModel):
    timestamp: str
    scope: Literal["device-level"] = "device-level"
    gpu_name: str | None = None
    gpu_utilization_percent: float | None = None
    gpu_memory_used_mb: float | None = None
    gpu_memory_total_mb: float | None = None
    temperature_c: float | None = None
    power_w: float | None = None
    available: bool
    note: str


class FinanceNarrative(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str = Field(min_length=10, max_length=1200)
    duplicate_invoice_ids: list[str]
    overdue_total: str
    deduplicated_overdue_total: str


class CompareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    include_narrative: bool = False


class SecurityDemoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    agent_id: str = "finance"


class ToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=80)
    arguments: dict[str, Any] = Field(default_factory=dict)
