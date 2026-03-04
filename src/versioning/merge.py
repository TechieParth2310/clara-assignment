"""Merge v1 memo with v2 updates extracted from an onboarding transcript.

Uses deep_merge_strict for null-safe recursive merging.
"""

from pathlib import Path
from typing import Any

from src.extract import rules_fallback
from src.extract.normalize import deep_merge_strict


def merge_memos(
    v1_memo: dict[str, Any],
    onboarding_text: str,
    source_path: Path,
) -> dict[str, Any]:
    """Return a new memo dict that is v1 with non-empty v2 fields applied on top.

    Uses deep_merge_strict to ensure no null overwrites.
    """
    from datetime import datetime, timezone

    memo_v2, _, _ = rules_fallback.extract(
        onboarding_text, source_path, version="v2", source_type="onboarding"
    )
    updates = memo_v2.to_dict()

    # Phase 4 — use deep_merge_strict for null-safe recursive merging
    merged = deep_merge_strict(v1_memo, updates)

    # Ensure metadata is set correctly
    merged["version"] = "v2"
    merged["source_type"] = "onboarding"
    merged["updated_at_utc"] = datetime.now(timezone.utc).isoformat()

    # Union questions_or_unknowns (dedup)
    new_q = [q for q in (updates.get("questions_or_unknowns") or []) if isinstance(q, str)]
    existing_q = [q for q in (merged.get("questions_or_unknowns") or []) if isinstance(q, str)]
    merged["questions_or_unknowns"] = list(dict.fromkeys(existing_q + new_q))

    return merged
