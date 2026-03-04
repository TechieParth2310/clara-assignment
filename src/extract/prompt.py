"""Extraction prompt builder and JSON response parser."""

import json
import re
from typing import Any


_MEMO_SCHEMA = """\
{
  "account_id": "<string>",
  "company_name": "<string or null>",
  "business_hours": {
    "days": ["<e.g. Monday, Tuesday, ...>"],
    "start": "<e.g. 09:00 or null>",
    "end": "<e.g. 17:00 or null>",
    "timezone": "<e.g. Central Time (CT) or null>"
  },
  "office_address": "<string or null>",
  "services_supported": ["<service1>", "..."],
  "emergency_definition": ["<what counts as an emergency>"],
  "emergency_routing_rules": {
    "description": "<string or null>",
    "transfer_to": "<string or null>"
  },
  "non_emergency_routing_rules": {
    "description": "<string or null>",
    "transfer_to": "<string or null>"
  },
  "call_transfer_rules": {
    "transfer_number": "<string or null>",
    "max_attempts": 1,
    "retry_delay_seconds": 0,
    "fail_message": "<string>"
  },
  "integration_constraints": ["<constraint1>", "..."],
  "after_hours_flow_summary": "<string or null>",
  "office_hours_flow_summary": "<string or null>",
  "questions_or_unknowns": ["<field_name: reason it is missing>"],
  "notes": "<string or null>",
  "evidence": {
    "company_name":               {"value": null, "snippets": [], "confidence": 0.0},
    "business_hours":             {"value": null, "snippets": [], "confidence": 0.0},
    "office_address":             {"value": null, "snippets": [], "confidence": 0.0},
    "services_supported":         {"value": null, "snippets": [], "confidence": 0.0},
    "emergency_definition":       {"value": null, "snippets": [], "confidence": 0.0},
    "emergency_routing_rules":    {"value": null, "snippets": [], "confidence": 0.0},
    "non_emergency_routing_rules":{"value": null, "snippets": [], "confidence": 0.0},
    "call_transfer_rules":        {"value": null, "snippets": [], "confidence": 0.0},
    "integration_constraints":    {"value": null, "snippets": [], "confidence": 0.0},
    "after_hours_flow_summary":   {"value": null, "snippets": [], "confidence": 0.0},
    "office_hours_flow_summary":  {"value": null, "snippets": [], "confidence": 0.0}
  }
}"""


def build_extraction_prompt(
    transcript: str,
    account_id: str,
    source_type: str,
) -> str:
    return f"""\
You are a data extraction assistant for a voice-agent configuration pipeline.

STRICT RULES — violating any rule makes your output unusable:
1. Output ONLY a single valid JSON object. No markdown, no code fences, no prose before or after.
2. Use ONLY facts explicitly stated in the transcript. NEVER infer, guess, or invent values.
3. If a field is not mentioned in the transcript: set its value to null (or [] for lists, {{}} for objects).
4. For every null or empty field, add an entry to questions_or_unknowns: "<field_name>: not found in transcript".
5. For each evidence entry: copy verbatim quotes (≤160 chars each) from the transcript into snippets; set confidence 0.0–1.0.
6. Missing evidence fields get snippets=[] and confidence=0.0.
7. account_id is exactly: {account_id}
8. source_type is exactly: {source_type}

FIELD GUIDANCE:
- business_hours.days: list of day names (e.g. ["Monday","Tuesday","Wednesday","Thursday","Friday"])
- business_hours.start/end: 24-hour "HH:MM" if possible, otherwise the exact phrasing from transcript
- emergency_definition: what the client defines as an emergency (life/property/urgent situations)
- emergency_routing_rules: how to handle emergency calls (transfer_to, instructions)
- non_emergency_routing_rules: how to handle routine calls
- call_transfer_rules.transfer_number: the phone number to transfer calls to
- after_hours_flow_summary: what happens when the office is closed
- office_hours_flow_summary: what happens during open hours
- services_supported: list of services/departments mentioned
- integration_constraints: any CRM, ticketing, or system integration requirements mentioned

OUTPUT SCHEMA (fill in every key — do not omit any key):
{_MEMO_SCHEMA}

TRANSCRIPT:
{transcript}"""


def parse_json_safely(text: str) -> dict[str, Any]:
    """
    Parse the first JSON object from *text*.

    Attempts light repairs before giving up:
      - strips markdown code fences
      - removes trailing commas before ] or }
      - replaces smart quotes with straight quotes
    """
    cleaned = _strip_fences(text).strip()

    obj = _try_loads(cleaned)
    if obj is not None:
        return obj

    repaired = _repair(cleaned)
    obj = _try_loads(repaired)
    if obj is not None:
        return obj

    preview = text[:300].replace("\n", " ")
    raise ValueError(f"Could not parse model response as JSON. Response preview: {preview!r}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _try_loads(text: str) -> dict[str, Any] | None:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        result = json.loads(match.group())
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass
    return None


def _strip_fences(text: str) -> str:
    return re.sub(r"```(?:json)?|```", "", text)


def _repair(text: str) -> str:
    # Remove trailing commas before closing bracket / brace
    text = re.sub(r",\s*([}\]])", r"\1", text)
    # Replace curly / smart quotes
    for orig, repl in [("\u201c", '"'), ("\u201d", '"'), ("\u2018", "'"), ("\u2019", "'")]:
        text = text.replace(orig, repl)
    return text
