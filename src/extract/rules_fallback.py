"""Deterministic rules-based transcript extractor.

This extractor never invents information. Fields it cannot confidently find
are left null/empty and recorded in questions_or_unknowns.
"""

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.extract.schema import (
    AccountMemo, AgentSpec,
    BusinessHours, CallTransferRules,
)
from src.generate.agent_prompt import (
    build_agent_name, build_system_prompt, build_key_variables,
    build_tool_invocation_placeholders,
)
from src.utils.text import derive_account_id, extract_field

# raw_snippets_map type: field_name -> (value, snippets, confidence)
RawSnippets = dict[str, tuple[Any, list[str], float]]


def extract(
    text: str,
    source_path: Path,
    version: str,
    source_type: str,
) -> tuple[AccountMemo, AgentSpec, RawSnippets]:
    now = datetime.now(timezone.utc).isoformat()
    account_id = _detect_account_id(text, source_path)

    company_name = extract_field(text, r"company(?:\s+name)?[:\s]+([^\n,\.]+)") or None
    days_raw = extract_field(text, r"(?:business\s+hours?|hours?)[:\s]+([^\n]+)") or None
    timezone_val = extract_field(text, r"time\s*zone[:\s]+([^\n,\.]+)") or None
    address = extract_field(text, r"address[:\s]+([^\n]+)") or None
    transfer_number = extract_field(
        text,
        r"(?:transfer\s+(?:to\s+)?(?:number|phone)|transfer\s+number|call\s+forward(?:ing)?\s+to)[:\s]+([\d\s\-\+\(\)]+)"
    ) or None
    after_hours_raw = extract_field(text, r"after[\s\-]hours?(?:\s+handling)?[:\s]+([^\n]+)") or None
    routing_raw = extract_field(text, r"routing(?:\s+rules?)?[:\s]+([^\n]+)") or None

    # Parse business hours into structured form
    days, start, end = _parse_business_hours(days_raw)
    bh = BusinessHours(
        days=days,
        start=start,
        end=end,
        timezone=timezone_val,
    )

    ctr = CallTransferRules(
        transfer_number=transfer_number,
        max_attempts=1,
        retry_delay_seconds=0,
        fail_message="I was unable to connect you. Let me take a message and arrange a callback.",
    )

    # Only infer services if explicitly named in routing — never guess
    services = _extract_explicit_services(routing_raw)

    # Non-emergency routing: only when routing_raw exists
    non_emer_route = {"description": routing_raw} if routing_raw else {}

    memo = AccountMemo(
        account_id=account_id,
        company_name=company_name,
        business_hours=bh,
        office_address=address,
        services_supported=services,
        emergency_definition=[],
        emergency_routing_rules={},
        non_emergency_routing_rules=non_emer_route,
        call_transfer_rules=ctr,
        integration_constraints=[],
        after_hours_flow_summary=after_hours_raw,
        office_hours_flow_summary=None,
        questions_or_unknowns=[],  # normalize_memo will fill this
        notes=None,
        version=version,
        source_type=source_type,
        updated_at_utc=now,
    )

    memo_dict = memo.to_dict()
    system_prompt = build_system_prompt(memo_dict)
    key_variables = build_key_variables(memo_dict)
    transfer_protocol = (
        f"Announce hold, attempt transfer to {transfer_number} (max 1 attempt), introduce caller on connect."
        if transfer_number else
        "Announce hold, route to appropriate team (max 1 attempt), introduce caller on connect."
    )

    spec = AgentSpec(
        account_id=account_id,
        agent_name=build_agent_name(company_name),
        voice_style="friendly_professional",
        system_prompt=system_prompt,
        key_variables=key_variables,
        tool_invocation_placeholders=build_tool_invocation_placeholders(),
        call_transfer_protocol=transfer_protocol,
        transfer_fail_protocol=ctr.fail_message,
        version=version,
        source_type=source_type,
        updated_at_utc=now,
    )

    raw_snippets = _build_raw_snippets(
        company_name=company_name,
        bh=bh,
        days_raw=days_raw,
        address=address,
        services=services,
        transfer_number=transfer_number,
        after_hours_raw=after_hours_raw,
        routing_raw=routing_raw,
        non_emer_route=non_emer_route,
    )

    return memo, spec, raw_snippets


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _detect_account_id(text: str, source_path: Path) -> str:
    match = re.search(r"account[_\s]?id[:\s]+([^\n,\s]+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return derive_account_id(source_path)


def _parse_business_hours(raw: str | None) -> tuple[list[str], str | None, str | None]:
    if not raw:
        return [], None, None

    day_map = {
        "monday": "Monday", "tuesday": "Tuesday", "wednesday": "Wednesday",
        "thursday": "Thursday", "friday": "Friday", "saturday": "Saturday", "sunday": "Sunday",
    }

    days: list[str] = []
    lower = raw.lower()

    range_match = re.search(r"(\w+day)\s+(?:to|through|–|-)\s+(\w+day)", lower)
    if range_match:
        start_day = day_map.get(range_match.group(1))
        end_day = day_map.get(range_match.group(2))
        if start_day and end_day:
            all_days = list(day_map.values())
            try:
                s_idx = all_days.index(start_day)
                e_idx = all_days.index(end_day)
                days = all_days[s_idx: e_idx + 1]
            except ValueError:
                pass
    else:
        for d_lower, d_title in day_map.items():
            if d_lower in lower:
                days.append(d_title)

    time_match = re.search(
        r"(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\s*(?:to|–|-)\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)",
        raw,
        re.IGNORECASE,
    )
    start_time = time_match.group(1).strip() if time_match else None
    end_time = time_match.group(2).strip() if time_match else None

    return days, start_time, end_time


def _extract_explicit_services(routing_raw: str | None) -> list[str]:
    """Only return services that are clearly and explicitly named in routing text."""
    if not routing_raw:
        return []
    services = []
    for keyword in ("sales", "support", "billing", "dispatch"):
        # Require the keyword to appear as a standalone word
        if re.search(rf"\b{keyword}\b", routing_raw, re.IGNORECASE):
            services.append(keyword.capitalize())
    return list(dict.fromkeys(services))


def _build_raw_snippets(
    *,
    company_name: str | None,
    bh: BusinessHours,
    days_raw: str | None,
    address: str | None,
    services: list[str],
    transfer_number: str | None,
    after_hours_raw: str | None,
    routing_raw: str | None,
    non_emer_route: dict[str, Any],
) -> RawSnippets:
    result: RawSnippets = {}

    def _add(field: str, value: Any, snippet: str | None) -> None:
        if value not in (None, [], {}):
            result[field] = (value, [snippet[:160]] if snippet else [], 0.9)

    _add("company_name", company_name, company_name)
    if days_raw:
        bh_val = bh.to_dict() if hasattr(bh, "to_dict") else None
        result["business_hours"] = (bh_val, [days_raw[:160]], 0.9)
    _add("office_address", address, address)
    _add("services_supported", services if services else None, routing_raw)
    _add("call_transfer_rules", {"transfer_number": transfer_number} if transfer_number else None, transfer_number)
    _add("after_hours_flow_summary", after_hours_raw, after_hours_raw)
    _add("non_emergency_routing_rules", non_emer_route if non_emer_route else None, routing_raw)

    return result

