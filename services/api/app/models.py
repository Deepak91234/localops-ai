from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from urllib.parse import parse_qsl, unquote, urlsplit
from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator


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
    read_knowledge = "read_knowledge"
    read_policy = "read_policy"
    analyze_invoices = "analyze_invoices"
    draft_support_reply = "draft_support_reply"
    inspect_permissions = "inspect_permissions"
    measure_scheduler = "measure_scheduler"


class AgentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=2, max_length=60)
    role: Literal["hr", "finance", "support", "custom"]
    purpose: str = Field(min_length=8, max_length=500)
    tools: list[Permission] = Field(min_length=1, max_length=3)
    source: str = Field(default="", max_length=200)
    source_ids: list[str] = Field(default_factory=list, max_length=100)


class Agent(BaseModel):
    id: str
    name: str
    role: str
    purpose: str
    tools: list[str]
    source: str
    source_ids: list[str] = Field(default_factory=list)
    status: AgentStatus = AgentStatus.idle
    enabled: bool = True
    created_at: str | None = None
    last_activity_at: str | None = None


class AgentControl(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["pause", "resume"]


class SourceAccess(BaseModel):
    model_config = ConfigDict(extra="forbid")
    shared: bool = False
    agent_ids: list[str] = Field(default_factory=list, max_length=100)


class SourceLink(SourceAccess):
    name: str = Field(min_length=1, max_length=120)
    url: str = Field(min_length=8, max_length=2000)
    kind: Literal["url", "api"] = "url"
    description: str = Field(default="", max_length=2000)
    refresh_minutes: int = Field(default=0, ge=0, le=10080)
    api_token: SecretStr | None = None

    @model_validator(mode="after")
    def credential_boundary(self):
        parsed = urlsplit(self.url)
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Embedded URL credentials are refused; use the optional API Bearer token field.")
        if any(key.lower() in {"token", "access_token", "api_key", "apikey", "password", "secret", "authorization"} for key, _ in parse_qsl(parsed.query)):
            raise ValueError("Credentials in URL query parameters are refused; use the optional API Bearer token field.")
        if self.api_token is not None:
            value = self.api_token.get_secret_value()
            if self.kind != "api":
                raise ValueError("Bearer credentials are allowed only for read-only API sources.")
            if not value or len(value) > 4096 or any(not 33 <= ord(character) <= 126 for character in value):
                raise ValueError("Bearer token must be at most 4096 ASCII characters without whitespace.")
            if parsed.scheme != "https":
                raise ValueError("Authenticated API sources require HTTPS.")
            if value in unquote(self.url):
                raise ValueError("The API token must be supplied only in its dedicated credential field.")
        return self


class AgentSources(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_ids: list[str] = Field(default_factory=list, max_length=100)


class AssistantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt: str = Field(min_length=3, max_length=4000)
    source_ids: list[str] | None = Field(default=None, max_length=100)
    history: list["ConversationMessage"] = Field(default_factory=list, max_length=6)


class ConversationMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


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
    source_ids: list[str] = Field(default_factory=list)
    history: list[ConversationMessage] = Field(default_factory=list)


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
