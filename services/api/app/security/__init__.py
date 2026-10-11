from urllib.parse import urlparse
from ..agents import ROLE_SOURCES, ROLE_TOOLS
from ..models import AgentCreate, ToolCall


class PermissionDenied(ValueError):
    pass


def is_loopback_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and parsed.hostname in {"localhost", "127.0.0.1", "::1"} and parsed.username is None and parsed.password is None
    except ValueError:
        return False


def validate_configuration(config: AgentCreate):
    tools = {str(tool.value) for tool in config.tools}
    if not tools.issubset(ROLE_TOOLS[config.role]):
        raise PermissionDenied("This role cannot receive the requested tool permissions.")
    if config.source not in ROLE_SOURCES[config.role]:
        raise PermissionDenied("The selected local source does not match this agent role.")
    if len(tools) != len(config.tools):
        raise PermissionDenied("Tool permissions must be unique.")


def authorize_tool(agent: dict, call: ToolCall):
    """Deterministic authorization gate. No shell/network/code tool exists."""
    approved = ROLE_TOOLS.get(agent["role"], set())
    if call.name not in approved or call.name not in agent["tools"]:
        raise PermissionDenied(f"Tool '{call.name}' is blocked: it is absent from this agent's allowlist. Network export, payments, shell commands, and file deletion are prohibited.")
    if call.arguments:
        raise PermissionDenied("This workflow accepts no tool arguments; data sources are fixed by the validated agent configuration.")
    return True
