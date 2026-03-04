"""Post-processing: normalize memo dicts, anti-hallucination, safe merge, and evidence builder."""

from typing import Any

from src.extract.schema import Evidence, EvidenceEntry, MEMO_EVIDENCE_FIELDS
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Fields whose correct empty value is [] (list)
_LIST_FIELDS = {
    "services_supported",
    "emergency_definition",
    "integration_constraints",
    "questions_or_unknowns",
}

# Fields whose correct empty value is {} (dict)
_DICT_FIELDS = {
    "emergency_routing_rules",
    "non_emergency_routing_rules",
}

# Nullable scalar fields (str | None)
_SCALAR_NULLABLE = {
    "company_name",
    "office_address",
    "after_hours_flow_summary",
    "office_hours_flow_summary",
    "notes",
}

_BH_SUBKEYS = ("days", "start", "end", "timezone")
_CTR_SUBKEYS = ("transfer_number", "max_attempts", "retry_delay_seconds", "fail_message")

_CTR_DEFAULTS = {
    "transfer_number": None,
    "max_attempts": 1,
    "retry_delay_seconds": 0,
    "fail_message": "I was unable to connect you. Let me take a message and arrange a callback.",
}

_BH_DEFAULTS = {
    "days": [],
    "start": None,
    "end": None,
    "timezone": None,
}

# Generic values that should NEVER appear — anti-hallucination blocklist
_GENERIC_BLOCKLIST = [
    "sales", "support", "billing", "dispatch",
    "life", "property", "urgent",
    "crm", "ticketing",
]


def normalize_memo(memo: dict[str, Any]) -> dict[str, Any]:
    """Enforce types, fill missing keys, clean questions_or_unknowns.

    Also strips any keys not in the required schema (e.g. 'evidence' returned
    by the LLM inside the memo payload) so that validate_memo_schema never sees
    unexpected extra fields.

    Returns a new dict (does not mutate input).
    """
    m = dict(memo)

    # Strip non-schema keys (e.g. 'evidence' embedded by LLM response)
    from src.utils.validate import REQUIRED_MEMO_SCHEMA
    for extra_key in list(m.keys()):
        if extra_key not in REQUIRED_MEMO_SCHEMA:
            m.pop(extra_key)

    # --- business_hours ---
    bh = m.get("business_hours")
    if not isinstance(bh, dict):
        bh = {}
    bh_clean: dict[str, Any] = {}
    bh_clean["days"] = bh.get("days") if isinstance(bh.get("days"), list) else []
    bh_clean["start"] = _str_or_none(bh.get("start"))
    bh_clean["end"] = _str_or_none(bh.get("end"))
    bh_clean["timezone"] = _str_or_none(bh.get("timezone"))
    m["business_hours"] = bh_clean

    # --- call_transfer_rules ---
    ctr = m.get("call_transfer_rules")
    if not isinstance(ctr, dict):
        ctr = {}
    ctr_clean: dict[str, Any] = {}
    ctr_clean["transfer_number"] = _str_or_none(ctr.get("transfer_number"))
    # Coerce booleans before int() to avoid bool-subclass issues from LLM output
    _ma = ctr.get("max_attempts")
    ctr_clean["max_attempts"] = int(_ma) if isinstance(_ma, (int, float, bool)) else 1
    _rd = ctr.get("retry_delay_seconds")
    ctr_clean["retry_delay_seconds"] = int(_rd) if isinstance(_rd, (int, float, bool)) else 0
    ctr_clean["fail_message"] = (
        ctr.get("fail_message")
        or "I was unable to connect you. Let me take a message and arrange a callback."
    )
    m["call_transfer_rules"] = ctr_clean

    # --- routing dicts ---
    for f in _DICT_FIELDS:
        v = m.get(f)
        m[f] = v if isinstance(v, dict) else {}

    # --- lists ---
    for f in _LIST_FIELDS:
        v = m.get(f)
        m[f] = v if isinstance(v, list) else []

    # --- nullable scalars ---
    for f in _SCALAR_NULLABLE:
        m[f] = _str_or_none(m.get(f))

    # --- clean questions_or_unknowns ---
    m["questions_or_unknowns"] = _clean_unknowns(m)

    return m


# ---------------------------------------------------------------------------
# Phase 3 — Anti-hallucination enforcement
# ---------------------------------------------------------------------------

_HALLUCINATION_CHECK_FIELDS = ("services_supported", "emergency_definition", "integration_constraints")


def strip_unsupported_fields(memo: dict[str, Any], transcript_text: str) -> dict[str, Any]:
    """Remove values from hallucination-prone fields that have no transcript support.

    For services_supported, emergency_definition, integration_constraints:
    - Check each item against transcript_text (case-insensitive substring match)
    - If item not found → remove it, log warning, add to questions_or_unknowns
    - Returns a new dict (does not mutate input).
    """
    m = dict(memo)
    transcript_lower = transcript_text.lower()
    unknowns = list(m.get("questions_or_unknowns") or [])

    for field in _HALLUCINATION_CHECK_FIELDS:
        items = m.get(field)
        if not isinstance(items, list) or not items:
            continue

        verified: list[str] = []
        for item in items:
            item_str = str(item).strip()
            if not item_str:
                continue
            # Check if the item (or its lowercase form) appears in the transcript
            if item_str.lower() in transcript_lower:
                verified.append(item_str)
            else:
                logger.warning(
                    "ANTI-HALLUCINATION: stripped '%s' from '%s' — not found in transcript",
                    item_str, field,
                )
                note = f"{field}: '{item_str}' not supported by transcript"
                if note not in unknowns:
                    unknowns.append(note)

        m[field] = verified

    m["questions_or_unknowns"] = unknowns
    return m


# ---------------------------------------------------------------------------
# Phase 4 — Safe merge engine
# ---------------------------------------------------------------------------

def deep_merge_strict(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge *new* into *old* with null-protection.

    Rules:
    - Only overwrite if new value is not None, not "", not [], not {}.
    - Apply recursively for nested dicts.
    - Never remove keys.
    - Never allow null overwrite.
    - Preserve prior values unless explicitly changed.
    """
    merged = dict(old)
    for key in set(list(old.keys()) + list(new.keys())):
        old_val = old.get(key)
        new_val = new.get(key)

        # If key only in old, keep it
        if key not in new:
            continue

        # Both are dicts → recurse
        if isinstance(old_val, dict) and isinstance(new_val, dict):
            merged[key] = deep_merge_strict(old_val, new_val)
        elif _non_empty(new_val):
            merged[key] = new_val
        # else: keep old_val — never clobber with empty

    return merged


# Backward compat alias
merge_dicts_no_clobber = deep_merge_strict


# ---------------------------------------------------------------------------
# Phase 5 — Evidence builder (auto-sync from memo + transcript)
# ---------------------------------------------------------------------------

def build_evidence_from_memo(
    memo: dict[str, Any],
    transcript_text: str,
) -> Evidence:
    """Build a spec-compliant Evidence object whose field values mirror memo exactly.

    Evidence.fields must EXACTLY mirror memo required schema keys.
    Snippets extracted via simple substring matching from transcript.
    Confidence scoring:
    - exact phrase match → 0.9
    - partial match → 0.6
    - inferred → 0.3
    - missing → 0.0

    Raises ValueError if evidence value does not equal memo value.
    """
    account_id = memo.get("account_id", "")
    version = memo.get("version", "v1")
    fields: dict[str, EvidenceEntry] = {}

    for field_name in MEMO_EVIDENCE_FIELDS:
        memo_value = memo.get(field_name)

        # Extract snippets via substring matching
        snippets, confidence = _extract_snippets_and_confidence(
            field_name, memo_value, transcript_text
        )

        # If value is empty, force confidence=0
        if not _non_empty(memo_value):
            memo_value = _empty_for_field(field_name)
            snippets = []
            confidence = 0.0

        fields[field_name] = EvidenceEntry(
            value=memo_value,
            snippets=[s[:160] for s in snippets if isinstance(s, str)],
            confidence=confidence,
        )

    evidence = Evidence(account_id=account_id, version=version, fields=fields)

    # Self-check: values must match
    for field_name in MEMO_EVIDENCE_FIELDS:
        ev_val = fields[field_name].value
        memo_val = memo.get(field_name)
        if not _non_empty(memo_val):
            memo_val = _empty_for_field(field_name)
        if ev_val != memo_val:
            raise ValueError(
                f"Evidence self-check failed for '{field_name}': "
                f"evidence={ev_val!r} != memo={memo_val!r}"
            )

    return evidence


def _extract_snippets_and_confidence(
    field_name: str,
    value: Any,
    transcript_text: str,
) -> tuple[list[str], float]:
    """Extract supporting snippets from transcript for a given field value.

    Returns (snippets, confidence).
    """
    if not _non_empty(value):
        return [], 0.0

    transcript_lower = transcript_text.lower()
    search_terms: list[str] = []

    if isinstance(value, str):
        search_terms.append(value)
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                search_terms.append(item)
    elif isinstance(value, dict):
        for v in value.values():
            if isinstance(v, str) and v.strip():
                search_terms.append(v)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, str):
                        search_terms.append(item)

    if not search_terms:
        return [], 0.3  # Inferred (structured data present but no searchable terms)

    snippets: list[str] = []
    exact_count = 0
    partial_count = 0

    for term in search_terms:
        term_lower = term.strip().lower()
        if not term_lower:
            continue

        if term_lower in transcript_lower:
            # Find the surrounding context in the transcript
            idx = transcript_lower.index(term_lower)
            # Grab surrounding context (up to 160 chars)
            start = max(0, idx - 20)
            end = min(len(transcript_text), idx + len(term) + 20)
            snippet = transcript_text[start:end].strip()
            snippets.append(snippet)
            exact_count += 1
        else:
            # Try partial match — individual words
            words = term_lower.split()
            matched_words = [w for w in words if w in transcript_lower and len(w) > 3]
            if matched_words:
                partial_count += 1

    if exact_count > 0:
        return snippets, 0.9
    elif partial_count > 0:
        return snippets, 0.6
    else:
        return [], 0.0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _clean_unknowns(m: dict[str, Any]) -> list[str]:
    """Remove questions whose field is now populated; deduplicate; keep order."""
    existing: list[str] = m.get("questions_or_unknowns") or []
    cleaned: list[str] = []
    seen: set[str] = set()

    for entry in existing:
        if not isinstance(entry, str):
            continue
        field_key = entry.split(":")[0].strip()
        if _field_is_populated(m, field_key):
            continue
        if entry not in seen:
            seen.add(entry)
            cleaned.append(entry)

    _ensure_missing_questions(m, cleaned, seen)
    return cleaned


def _field_is_populated(m: dict[str, Any], field_key: str) -> bool:
    """Return True if the field referenced by field_key has a real value in m."""
    if "." in field_key:
        parent, child = field_key.split(".", 1)
        parent_val = m.get(parent)
        if not isinstance(parent_val, dict):
            return False
        return _non_empty(parent_val.get(child))
    return _non_empty(m.get(field_key))


def _ensure_missing_questions(
    m: dict[str, Any], cleaned: list[str], seen: set[str]
) -> None:
    """Add questions for every required field that is empty and not yet noted."""
    checks = [
        ("company_name", m.get("company_name")),
        ("business_hours.days", (m.get("business_hours") or {}).get("days")),
        ("business_hours.timezone", (m.get("business_hours") or {}).get("timezone")),
        ("office_address", m.get("office_address")),
        ("services_supported", m.get("services_supported")),
        ("emergency_definition", m.get("emergency_definition")),
        ("emergency_routing_rules", m.get("emergency_routing_rules")),
        ("non_emergency_routing_rules", m.get("non_emergency_routing_rules")),
        ("call_transfer_rules.transfer_number", (m.get("call_transfer_rules") or {}).get("transfer_number")),
        ("integration_constraints", m.get("integration_constraints")),
        ("after_hours_flow_summary", m.get("after_hours_flow_summary")),
        ("office_hours_flow_summary", m.get("office_hours_flow_summary")),
    ]
    for field_key, val in checks:
        if not _non_empty(val):
            entry = f"{field_key}: not found in transcript"
            if entry not in seen:
                seen.add(entry)
                cleaned.append(entry)


def _empty_for_field(field_name: str) -> Any:
    """Return the correct empty sentinel for a field type."""
    if field_name in _LIST_FIELDS:
        return []
    if field_name in _DICT_FIELDS or field_name in ("business_hours", "call_transfer_rules"):
        return {}
    return None


def _non_empty(v: Any) -> bool:
    """Return True if v is not None and not an empty container."""
    if v is None:
        return False
    if isinstance(v, (str, list, dict)):
        return bool(v)
    return True


def _str_or_none(v: Any) -> str | None:
    """Coerce to stripped str or None."""
    if isinstance(v, str):
        s = v.strip()
        return s if s else None
    return None
