"""File I/O helpers."""

import json
from pathlib import Path
from typing import Any


def ensure_dir(path: Path) -> Path:
    """Create directory (and parents) if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_text(path: Path) -> str:
    """Read a text file and return its contents."""
    return path.read_text(encoding="utf-8")


def write_json(path: Path, data: Any, indent: int = 2) -> None:
    """Serialise *data* to a JSON file, creating parent directories as needed."""
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, indent=indent, default=str), encoding="utf-8")


def read_json(path: Path) -> Any:
    """Deserialise JSON from *path*."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, content: str) -> None:
    """Write *content* to *path*, creating parent directories as needed."""
    ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8")
