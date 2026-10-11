from dataclasses import dataclass, field
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass
class Settings:
    data_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "demo_data")
    db_path: Path = field(default_factory=lambda: Path(os.getenv("LOCALOPS_DB_PATH", str(PROJECT_ROOT / "work" / "localops.sqlite3"))))
    llm_base_url: str = field(default_factory=lambda: os.getenv("LLM_BASE_URL", "http://127.0.0.1:11434/v1"))
    model_name: str = field(default_factory=lambda: os.getenv("MODEL_NAME", "nemotron3:33b"))
    llm_api_key: str = field(default_factory=lambda: os.getenv("LLM_API_KEY", ""))
    llm_timeout: float = field(default_factory=lambda: float(os.getenv("LLM_TIMEOUT_SECONDS", "180")))
    max_tokens: int = field(default_factory=lambda: int(os.getenv("LLM_MAX_TOKENS", "900")))
