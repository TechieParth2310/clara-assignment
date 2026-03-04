"""Text processing utilities."""

import re
from pathlib import Path


def derive_account_id(path: Path) -> str:
    """
    Derive a stable account_id from a transcript filename.

    Examples
    --------
    acme_001_demo.txt      -> acme_001
    globex_onboarding.txt  -> globex
    springfield.txt        -> springfield
    """
    stem = path.stem
    for suffix in ("_demo", "_onboarding"):
        if stem.endswith(suffix):
            return stem[: -len(suffix)]
    return stem


def extract_field(text: str, pattern: str, default: str = "") -> str:
    """Return the first captured group from *pattern* or *default* if not found."""
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else default


def normalise_whitespace(text: str) -> str:
    """Collapse runs of whitespace / blank lines into single spaces."""
    return re.sub(r"\s+", " ", text).strip()
