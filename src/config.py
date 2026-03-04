"""Runtime configuration loaded from environment / .env file."""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional; environment variables still work without it


class Config:
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()
    extraction_mode: str = os.getenv("EXTRACTION_MODE", "rules")
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3")

    # Resolved at import time; overridable via CLI flags
    input_root: Path = Path("data")
    output_root: Path = Path("outputs")


config = Config()
