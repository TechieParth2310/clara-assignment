"""Thin HTTP client for the local Ollama /api/chat endpoint."""

import json
import urllib.error
import urllib.request
from typing import Any

from src.utils.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_HOST = "http://127.0.0.1:11434"
_TIMEOUT = 120  # seconds — generous for first-token latency on a cold model


def chat(
    prompt: str,
    model: str,
    host: str = _DEFAULT_HOST,
    temperature: float = 0.1,
    num_predict: int = 1024,
) -> str:
    """
    Send *prompt* to Ollama and return the assistant's text response.

    Raises RuntimeError with a user-friendly message if Ollama is unreachable
    or returns a non-200 status.
    """
    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
        },
    }

    url = f"{host.rstrip('/')}/api/chat"
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            raw = resp.read().decode()
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Cannot reach Ollama at {host}. "
            "Make sure `ollama serve` is running. "
            f"Original error: {exc.reason}"
        ) from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Unexpected Ollama response (not JSON): {raw[:200]}") from exc

    message = data.get("message") or {}
    content = message.get("content", "")
    if not content:
        raise RuntimeError(f"Ollama returned an empty response. Full payload: {raw[:300]}")

    logger.debug("Ollama (%s) responded with %d chars", model, len(content))
    return content
