"""Orchestrates extraction for demo and onboarding transcripts."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.extract import rules_fallback
from src.extract.normalize import (
    normalize_memo,
    build_evidence_from_memo,
    deep_merge_strict,
    strip_unsupported_fields,
)
from src.extract.schema import (
    AccountMemo, AgentSpec, Evidence,
    BusinessHours, CallTransferRules, MEMO_EVIDENCE_FIELDS,
)
from src.generate.agent_prompt import (
    build_system_prompt, build_agent_name, build_key_variables,
    build_tool_invocation_placeholders,
)
from src.utils.io import read_text, read_json, write_json, write_text, ensure_dir
from src.utils.logging import get_logger
from src.utils.text import derive_account_id
from src.utils.validate import validate_memo_schema, validate_agent_spec, validate_evidence, validate_evidence_alignment
from src.versioning.changelog import write_changelog

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def process_transcript(
    path: Path,
    output_root: Path,
    mode: str,
    model: str = "llama3.2:3b",
    version: str = "v1",
    source_type: str = "demo",
    account_id: str | None = None,
    prev_memo_dict: dict[str, Any] | None = None,
    prev_evidence_dict: dict[str, Any] | None = None,
) -> str:
    """Unified processor for any transcript version.

    For v1 (demo): prev_memo_dict and prev_evidence_dict are None.
    For v2+ (onboarding): prev_memo_dict is the prior version's memo.

    Returns account_id.
    """
    text = read_text(path)
    if account_id is None:
        account_id = derive_account_id(path)

    now = datetime.now(timezone.utc).isoformat()

    if mode == "ollama":
        memo_dict, raw_snippets = _ollama_extract_dict(text, path, version, source_type, model, account_id)
    else:
        memo_obj, _, raw_snippets = rules_fallback.extract(text, path, version=version, source_type=source_type)
        memo_dict = memo_obj.to_dict()

    # Normalize
    memo_dict = normalize_memo(memo_dict)

    # Phase 3 — Anti-hallucination: strip unsupported values
    memo_dict = strip_unsupported_fields(memo_dict, text)

    # Phase 4 — Safe merge for versions > v1
    if prev_memo_dict is not None:
        memo_dict = deep_merge_strict(prev_memo_dict, memo_dict)
        # Ensure metadata is updated
        memo_dict["version"] = version
        memo_dict["source_type"] = source_type
        memo_dict["updated_at_utc"] = now

    # Ensure account_id and timestamps are set
    memo_dict["account_id"] = account_id
    if not memo_dict.get("updated_at_utc"):
        memo_dict["updated_at_utc"] = now

    # Re-normalize after merge
    memo_dict = normalize_memo(memo_dict)

    # Phase 2 — Strict schema validation
    validate_memo_schema(memo_dict)

    # Phase 5 — Build evidence from memo + transcript
    evidence = build_evidence_from_memo(memo_dict, text)

    # Phase 6 — Post-run integrity check
    validate_evidence_alignment(memo_dict, evidence.to_dict())
    validate_evidence(evidence.to_dict())

    # Build agent spec
    spec = _spec_from_memo_dict(memo_dict, version, source_type, now)
    validate_agent_spec(spec.to_dict())

    # Phase 7 — Idempotency guard
    memo_obj = _memo_from_dict(memo_dict)
    if _is_unchanged(memo_obj, output_root, version):
        logger.info("UNCHANGED — skipping write for %s %s", account_id, version)
        return account_id

    # Write outputs
    _write_version_outputs(memo_obj, spec, evidence, output_root, version)
    logger.info("Wrote %s outputs for %s", version, account_id)

    # Write changelog for v2+
    if prev_memo_dict is not None:
        changes_path = output_root / "accounts" / account_id / "changes.md"
        write_changelog(prev_memo_dict, memo_dict, changes_path)
        logger.info("Wrote changelog for %s", account_id)

    return account_id


# Backward-compat wrappers (keep old interface working)

def process_demo_transcript(
    path: Path, output_root: Path, mode: str, model: str = "llama3.2:3b"
) -> str:
    """Process a v1 demo transcript. Backward-compatible wrapper."""
    return process_transcript(path, output_root, mode, model, version="v1", source_type="demo")


def process_onboarding_transcript(
    path: Path, output_root: Path, mode: str, model: str = "llama3.2:3b"
) -> str:
    """Process a v2 onboarding transcript. Backward-compatible wrapper."""
    account_id = derive_account_id(path)
    v1_dir = output_root / "accounts" / account_id / "v1"
    v1_memo_dict = read_json(v1_dir / "memo.json")
    v1_evidence_dict = read_json(v1_dir / "evidence.json")

    return process_transcript(
        path, output_root, mode, model,
        version="v2",
        source_type="onboarding",
        account_id=account_id,
        prev_memo_dict=v1_memo_dict,
        prev_evidence_dict=v1_evidence_dict,
    )


# ---------------------------------------------------------------------------
# Ollama extraction
# ---------------------------------------------------------------------------

def _ollama_extract_dict(
    text: str,
    source_path: Path,
    version: str,
    source_type: str,
    model: str,
    account_id: str,
) -> tuple[dict[str, Any], dict[str, tuple[Any, list[str], float]]]:
    """Extract memo dict and raw snippets via Ollama LLM."""
    from src.extract.ollama_client import chat
    from src.extract.prompt import build_extraction_prompt, parse_json_safely

    prompt = build_extraction_prompt(text, account_id, source_type)

    logger.info("Calling Ollama (%s) for %s %s", model, account_id, version)
    raw = chat(prompt, model=model)
    data = parse_json_safely(raw)

    now = datetime.now(timezone.utc).isoformat()
    data["account_id"] = account_id
    data["version"] = version
    data["source_type"] = source_type
    data["updated_at_utc"] = now

    raw_snippets = _raw_snippets_from_llm(data)
    return data, raw_snippets


def _raw_snippets_from_llm(
    data: dict[str, Any],
) -> dict[str, tuple[Any, list[str], float]]:
    """Extract raw snippets map from LLM evidence block.

    Returns: field_name -> (value, snippets, confidence)
    Only fields with confidence > 0 are included.
    """
    raw_ev = data.get("evidence") or {}
    result: dict[str, tuple[Any, list[str], float]] = {}

    for field_name in MEMO_EVIDENCE_FIELDS:
        entry = raw_ev.get(field_name)
        if not isinstance(entry, dict):
            continue
        snippets = [s for s in (entry.get("snippets") or []) if isinstance(s, str)]
        confidence = float(entry.get("confidence") or 0.0)
        if confidence > 0.0 or snippets:
            result[field_name] = (entry.get("value"), snippets, confidence)

    return result


# ---------------------------------------------------------------------------
# Object builders
# ---------------------------------------------------------------------------

def _spec_from_memo_dict(
    memo_dict: dict[str, Any],
    version: str,
    source_type: str,
    now: str,
) -> AgentSpec:
    """Build an AgentSpec from a normalized memo dict."""
    company = memo_dict.get("company_name")
    ctr = memo_dict.get("call_transfer_rules") or {}
    transfer_number = ctr.get("transfer_number") or ""
    fail_message = ctr.get("fail_message") or (
        "I was unable to connect you. Let me take a message and arrange a callback."
    )
    max_attempts = ctr.get("max_attempts") or 1

    system_prompt = build_system_prompt(memo_dict)
    key_variables = build_key_variables(memo_dict)

    transfer_protocol = (
        f"Announce hold, attempt transfer to {transfer_number} (max {max_attempts} attempt(s)), "
        "introduce caller on connect."
        if transfer_number else
        f"Announce hold, route to appropriate team (max {max_attempts} attempt(s)), "
        "introduce caller on connect."
    )

    return AgentSpec(
        account_id=memo_dict.get("account_id") or "",
        agent_name=build_agent_name(company),
        voice_style="friendly_professional",
        system_prompt=system_prompt,
        key_variables=key_variables,
        tool_invocation_placeholders=build_tool_invocation_placeholders(),
        call_transfer_protocol=transfer_protocol,
        transfer_fail_protocol=fail_message,
        version=version,
        source_type=source_type,
        updated_at_utc=now,
    )


def _memo_from_dict(d: dict[str, Any]) -> AccountMemo:
    """Reconstruct an AccountMemo dataclass from a normalized dict."""
    bh_raw = d.get("business_hours") or {}
    bh = BusinessHours(
        days=_coerce_list(bh_raw.get("days")),
        start=_str_or_none(bh_raw.get("start")),
        end=_str_or_none(bh_raw.get("end")),
        timezone=_str_or_none(bh_raw.get("timezone")),
    )
    ctr_raw = d.get("call_transfer_rules") or {}
    ctr = CallTransferRules(
        transfer_number=_str_or_none(ctr_raw.get("transfer_number")),
        max_attempts=int(ctr_raw.get("max_attempts") or 1),
        retry_delay_seconds=int(ctr_raw.get("retry_delay_seconds") or 0),
        fail_message=ctr_raw.get("fail_message") or (
            "I was unable to connect you. Let me take a message and arrange a callback."
        ),
    )
    return AccountMemo(
        account_id=d["account_id"],
        company_name=d.get("company_name"),
        business_hours=bh,
        office_address=d.get("office_address"),
        services_supported=_coerce_list(d.get("services_supported")),
        emergency_definition=_coerce_list(d.get("emergency_definition")),
        emergency_routing_rules=d.get("emergency_routing_rules") or {},
        non_emergency_routing_rules=d.get("non_emergency_routing_rules") or {},
        call_transfer_rules=ctr,
        integration_constraints=_coerce_list(d.get("integration_constraints")),
        after_hours_flow_summary=d.get("after_hours_flow_summary"),
        office_hours_flow_summary=d.get("office_hours_flow_summary"),
        questions_or_unknowns=_coerce_list(d.get("questions_or_unknowns")),
        notes=d.get("notes"),
        version=d.get("version", "v1"),
        source_type=d.get("source_type", "demo"),
        updated_at_utc=d.get("updated_at_utc", ""),
    )


# ---------------------------------------------------------------------------
# Phase 7 — Idempotency guard
# ---------------------------------------------------------------------------

def _hash_memo(memo: AccountMemo) -> str:
    """Compute SHA256 hash of memo content (sorted keys, excluding updated_at_utc).

    updated_at_utc changes every run so it is excluded from the content hash
    to allow the idempotency guard to correctly detect unchanged content.
    """
    d = memo.to_dict()
    d.pop("updated_at_utc", None)
    canonical = json.dumps(d, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _is_unchanged(memo: AccountMemo, output_root: Path, version: str) -> bool:
    """Return True if existing memo on disk matches the new memo exactly (excluding timestamp)."""
    existing_path = output_root / "accounts" / memo.account_id / version / "memo.json"
    if not existing_path.exists():
        return False
    try:
        existing_data = read_json(existing_path)
        existing_data.pop("updated_at_utc", None)
        existing_canonical = json.dumps(existing_data, sort_keys=True, default=str)
        existing_hash = hashlib.sha256(existing_canonical.encode("utf-8")).hexdigest()
        new_hash = _hash_memo(memo)
        return existing_hash == new_hash
    except Exception:
        return False


# ---------------------------------------------------------------------------
# File writer
# ---------------------------------------------------------------------------

def _write_version_outputs(
    memo: AccountMemo,
    spec: AgentSpec,
    evidence: Evidence,
    output_root: Path,
    version: str,
) -> None:
    """Write memo, agent_spec, evidence, and system_prompt files."""
    base = output_root / "accounts" / memo.account_id / version
    ensure_dir(base)
    write_json(base / "memo.json", memo.to_dict())
    write_json(base / "agent_spec.json", spec.to_dict())
    write_json(base / "evidence.json", evidence.to_dict())
    write_text(base / "system_prompt.txt", spec.system_prompt)


# ---------------------------------------------------------------------------
# Coercion helpers
# ---------------------------------------------------------------------------

def _str_or_none(v: Any) -> str | None:
    """Coerce to str or None."""
    if isinstance(v, str):
        s = v.strip()
        return s if s else None
    return None


def _coerce_list(v: Any) -> list:
    """Coerce to list."""
    if isinstance(v, list):
        return v
    if v is None:
        return []
    return [str(v)]
