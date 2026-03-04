"""Generate a human-readable changes.md comparing v1 and v2 memos.

Phase 9 — Changelog Hardening:
- Shows only fields that actually changed
- Shows nested diffs clearly (sub-fields within dicts)
- Never logs null → null overwrites
- Includes confidence delta if changed
- Does not show unchanged nested subfields
"""

from pathlib import Path
from typing import Any

from src.utils.io import write_text


_TRACKED_FIELDS = [
    "company_name",
    "business_hours",
    "office_address",
    "services_supported",
    "emergency_definition",
    "emergency_routing_rules",
    "non_emergency_routing_rules",
    "call_transfer_rules",
    "integration_constraints",
    "after_hours_flow_summary",
    "office_hours_flow_summary",
    "notes",
    "questions_or_unknowns",
]


def write_changelog(
    v1: dict[str, Any],
    v2: dict[str, Any],
    output_path: Path,
    v1_evidence: dict[str, Any] | None = None,
    v2_evidence: dict[str, Any] | None = None,
) -> None:
    """Write a hardened changelog comparing v1 and v2 memos.

    Args:
        v1: v1 memo dict.
        v2: v2 memo dict.
        output_path: Path to write changes.md.
        v1_evidence: Optional v1 evidence dict for confidence delta.
        v2_evidence: Optional v2 evidence dict for confidence delta.
    """
    lines: list[str] = [
        "# Changelog",
        "",
        f"**Account:** {v2.get('account_id', 'unknown')}",
        f"**Updated:** {v2.get('updated_at_utc', '')}",
        "",
        "## Changes from v1 → v2",
        "",
    ]

    found_any = False

    for field in _TRACKED_FIELDS:
        old_val = v1.get(field)
        new_val = v2.get(field)

        if old_val == new_val:
            continue

        # Never log null → null overwrites
        if _is_empty(old_val) and _is_empty(new_val):
            continue

        label = field.replace("_", " ").title()

        if isinstance(old_val, dict) and isinstance(new_val, dict):
            # Nested diff — show only changed sub-fields
            nested_lines = _nested_diff(old_val, new_val, label)
            if nested_lines:
                found_any = True
                lines.extend(nested_lines)
        elif _is_empty(old_val) and not _is_empty(new_val):
            found_any = True
            conf_str = _confidence_delta_str(field, v1_evidence, v2_evidence)
            lines.append(f"- **Added** `{label}`: {_fmt(new_val)}{conf_str}")
        elif not _is_empty(old_val) and _is_empty(new_val):
            found_any = True
            lines.append(f"- **Removed** `{label}` (was: {_fmt(old_val)})")
        else:
            found_any = True
            conf_str = _confidence_delta_str(field, v1_evidence, v2_evidence)
            lines.append(f"- **Updated** `{label}`: {_fmt(old_val)} → {_fmt(new_val)}{conf_str}")

    if not found_any:
        lines.append("_No changes detected between v1 and v2._")

    lines.append("")
    write_text(output_path, "\n".join(lines))


def _nested_diff(old: dict, new: dict, parent_label: str) -> list[str]:
    """Generate diff lines for nested dict changes, showing only changed sub-fields."""
    lines: list[str] = []
    all_keys = sorted(set(list(old.keys()) + list(new.keys())))

    for key in all_keys:
        old_v = old.get(key)
        new_v = new.get(key)

        if old_v == new_v:
            continue

        # Skip null → null
        if _is_empty(old_v) and _is_empty(new_v):
            continue

        sub_label = key.replace("_", " ").title()

        if _is_empty(old_v) and not _is_empty(new_v):
            lines.append(f"- **Added** `{parent_label}.{sub_label}`: {_fmt(new_v)}")
        elif not _is_empty(old_v) and _is_empty(new_v):
            lines.append(f"- **Removed** `{parent_label}.{sub_label}` (was: {_fmt(old_v)})")
        else:
            lines.append(f"- **Updated** `{parent_label}.{sub_label}`: {_fmt(old_v)} → {_fmt(new_v)}")

    return lines


def _confidence_delta_str(
    field: str,
    v1_evidence: dict[str, Any] | None,
    v2_evidence: dict[str, Any] | None,
) -> str:
    """Return a confidence delta string if both evidence dicts are available."""
    if v1_evidence is None or v2_evidence is None:
        return ""

    v1_fields = v1_evidence.get("fields", {})
    v2_fields = v2_evidence.get("fields", {})

    v1_conf = (v1_fields.get(field) or {}).get("confidence", 0.0)
    v2_conf = (v2_fields.get(field) or {}).get("confidence", 0.0)

    if v1_conf != v2_conf:
        delta = v2_conf - v1_conf
        sign = "+" if delta > 0 else ""
        return f" *(confidence: {v1_conf:.1f} → {v2_conf:.1f}, {sign}{delta:.1f})*"

    return ""


def _is_empty(val: Any) -> bool:
    """Return True if val is None, empty string, empty list, or empty dict."""
    if val is None:
        return True
    if isinstance(val, (str, list, dict)):
        return not val
    return False


def _fmt(value: Any) -> str:
    """Format a value for changelog display."""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) if value else "*(empty)*"
    if isinstance(value, dict):
        return str(value) if value else "*(empty)*"
    return str(value) if value else "*(empty)*"
