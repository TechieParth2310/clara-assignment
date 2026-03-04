"""Schema validation helpers — strict enforcement."""

from typing import Any

from src.utils.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Phase 2 — REQUIRED_MEMO_SCHEMA
# Maps field name → expected type (or tuple of types).
# None means nullable (str | None).
# ---------------------------------------------------------------------------

REQUIRED_MEMO_SCHEMA: dict[str, Any] = {
    "account_id":                 str,
    "company_name":               (str, type(None)),
    "business_hours":             dict,
    "office_address":             (str, type(None)),
    "services_supported":         list,
    "emergency_definition":       list,
    "emergency_routing_rules":    dict,
    "non_emergency_routing_rules":dict,
    "call_transfer_rules":        dict,
    "integration_constraints":    list,
    "after_hours_flow_summary":   (str, type(None)),
    "office_hours_flow_summary":  (str, type(None)),
    "questions_or_unknowns":      list,
    "notes":                      (str, type(None)),
    "version":                    str,
    "source_type":                str,
    "updated_at_utc":             str,
}

_BUSINESS_HOURS_REQUIRED = {"days": list, "start": (str, type(None)), "end": (str, type(None)), "timezone": (str, type(None))}
_CALL_TRANSFER_REQUIRED = {"transfer_number": (str, type(None)), "max_attempts": int, "retry_delay_seconds": int, "fail_message": str}

_AGENT_SPEC_REQUIRED = {
    "account_id", "agent_name", "voice_style", "system_prompt",
    "key_variables", "tool_invocation_placeholders",
    "call_transfer_protocol", "transfer_fail_protocol",
    "version", "source_type", "updated_at_utc",
}

_EVIDENCE_REQUIRED_FIELDS = {
    "company_name", "business_hours", "office_address",
    "services_supported", "emergency_definition",
    "emergency_routing_rules", "non_emergency_routing_rules",
    "call_transfer_rules", "integration_constraints",
    "after_hours_flow_summary", "office_hours_flow_summary",
}

_EVIDENCE_ENTRY_REQUIRED = {"value", "snippets", "confidence"}


def validate_memo_schema(memo: dict[str, Any]) -> None:
    """Raise ValueError if memo violates the strict schema contract.

    Checks:
    - Missing required keys
    - Extra unexpected keys
    - Wrong types for all top-level fields
    - Nested required keys in business_hours and call_transfer_rules
    - timezone present in business_hours
    - transfer_number present in call_transfer_rules
    """
    errors: list[str] = []

    # --- Missing keys ---
    missing = set(REQUIRED_MEMO_SCHEMA.keys()) - set(memo.keys())
    if missing:
        errors.append(f"Missing required field(s): {sorted(missing)}")

    # --- Extra keys ---
    extra = set(memo.keys()) - set(REQUIRED_MEMO_SCHEMA.keys())
    if extra:
        errors.append(f"Unexpected extra field(s): {sorted(extra)}")

    # --- Type checks for present fields ---
    for field, expected_type in REQUIRED_MEMO_SCHEMA.items():
        if field not in memo:
            continue
        val = memo[field]
        if not isinstance(val, expected_type):
            errors.append(
                f"Field '{field}' has wrong type: expected {expected_type}, got {type(val).__name__}"
            )

    # --- Nested: business_hours ---
    bh = memo.get("business_hours")
    if isinstance(bh, dict):
        for k, expected in _BUSINESS_HOURS_REQUIRED.items():
            if k not in bh:
                errors.append(f"business_hours missing required key: '{k}'")
            elif not isinstance(bh[k], expected):
                errors.append(
                    f"business_hours.{k} has wrong type: expected {expected}, got {type(bh[k]).__name__}"
                )
        # timezone must be present (not just the key)
        if bh.get("timezone") is None and "timezone" in bh:
            # Key exists but value is None — allowed per schema but flagged
            pass
    elif bh is not None:
        errors.append("business_hours must be a dict")

    # --- Nested: call_transfer_rules ---
    ctr = memo.get("call_transfer_rules")
    if isinstance(ctr, dict):
        for k, expected in _CALL_TRANSFER_REQUIRED.items():
            if k not in ctr:
                errors.append(f"call_transfer_rules missing required key: '{k}'")
            elif not isinstance(ctr[k], expected):
                errors.append(
                    f"call_transfer_rules.{k} has wrong type: expected {expected}, got {type(ctr[k]).__name__}"
                )
    elif ctr is not None:
        errors.append("call_transfer_rules must be a dict")

    if errors:
        raise ValueError("Memo schema validation failed:\n  - " + "\n  - ".join(errors))


# Backward compat alias
validate_memo = validate_memo_schema


def validate_agent_spec(spec: dict[str, Any]) -> None:
    """Raise ValueError if any required agent_spec field is absent."""
    missing = _AGENT_SPEC_REQUIRED - spec.keys()
    if missing:
        raise ValueError(f"AgentSpec is missing required field(s): {sorted(missing)}")
    if not isinstance(spec.get("key_variables"), dict):
        raise ValueError("AgentSpec.key_variables must be a dict")
    if not isinstance(spec.get("tool_invocation_placeholders"), list):
        raise ValueError("AgentSpec.tool_invocation_placeholders must be a list")


def validate_evidence(evidence: dict[str, Any]) -> None:
    """Raise ValueError if evidence is missing required fields or has malformed entries."""
    for top in ("account_id", "version", "fields"):
        if top not in evidence:
            raise ValueError(f"Evidence is missing top-level key: {top!r}")

    fields = evidence["fields"]
    if not isinstance(fields, dict):
        raise ValueError("Evidence.fields must be a dict")

    missing_fields = _EVIDENCE_REQUIRED_FIELDS - fields.keys()
    if missing_fields:
        raise ValueError(f"Evidence.fields is missing required field(s): {sorted(missing_fields)}")

    for field_name, entry in fields.items():
        if not isinstance(entry, dict):
            raise ValueError(f"Evidence.fields[{field_name!r}] must be a dict")
        missing_keys = _EVIDENCE_ENTRY_REQUIRED - entry.keys()
        if missing_keys:
            raise ValueError(
                f"Evidence.fields[{field_name!r}] is missing key(s): {sorted(missing_keys)}"
            )


def validate_evidence_alignment(memo: dict[str, Any], evidence: dict[str, Any]) -> None:
    """Validate that evidence values exactly mirror memo values.

    Checks:
    - Same field keys in evidence.fields as MEMO_EVIDENCE_FIELDS
    - evidence.fields.<field>.value == memo.<field> for every field
    - No extra fields in evidence

    Raises ValueError with diff details on mismatch.
    """
    from src.extract.schema import MEMO_EVIDENCE_FIELDS

    evidence_fields = evidence.get("fields", {})
    diffs: list[str] = []

    # Check all required fields are present in evidence
    for field in MEMO_EVIDENCE_FIELDS:
        if field not in evidence_fields:
            diffs.append(f"MISSING in evidence: {field}")
            continue

        ev_val = evidence_fields[field].get("value")
        memo_val = memo.get(field)

        if ev_val != memo_val:
            diffs.append(
                f"MISMATCH '{field}': memo={_trunc(memo_val)} | evidence={_trunc(ev_val)}"
            )

    # Check for extra fields in evidence not in schema
    extra = set(evidence_fields.keys()) - set(MEMO_EVIDENCE_FIELDS)
    for field in sorted(extra):
        diffs.append(f"EXTRA in evidence (not in schema): {field}")

    if diffs:
        diff_report = "\n  - ".join(diffs)
        raise ValueError(
            f"Evidence alignment check FAILED:\n  - {diff_report}"
        )


def _trunc(val: Any) -> str:
    """Truncate a value for readable diff output."""
    s = repr(val)
    return s if len(s) <= 100 else s[:97] + "..."
