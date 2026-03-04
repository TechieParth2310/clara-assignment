"""Typed schemas for pipeline outputs."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BusinessHours:
    days: list[str] = field(default_factory=list)
    start: str | None = None
    end: str | None = None
    timezone: str | None = None

    def to_dict(self) -> dict:
        return {
            "days": self.days,
            "start": self.start,
            "end": self.end,
            "timezone": self.timezone,
        }


@dataclass
class CallTransferRules:
    transfer_number: str | None = None
    max_attempts: int = 1
    retry_delay_seconds: int = 0
    fail_message: str = "I was unable to connect you. Let me take a message and have someone call you back."

    def to_dict(self) -> dict:
        return {
            "transfer_number": self.transfer_number,
            "max_attempts": self.max_attempts,
            "retry_delay_seconds": self.retry_delay_seconds,
            "fail_message": self.fail_message,
        }


@dataclass
class AccountMemo:
    account_id: str
    company_name: str | None
    business_hours: BusinessHours
    office_address: str | None
    services_supported: list[str]
    emergency_definition: list[str]
    emergency_routing_rules: dict[str, Any]
    non_emergency_routing_rules: dict[str, Any]
    call_transfer_rules: CallTransferRules
    integration_constraints: list[str]
    after_hours_flow_summary: str | None
    office_hours_flow_summary: str | None
    questions_or_unknowns: list[str]
    notes: str | None

    # Metadata
    version: str
    source_type: str
    updated_at_utc: str

    def to_dict(self) -> dict:
        return {
            "account_id": self.account_id,
            "company_name": self.company_name,
            "business_hours": self.business_hours.to_dict(),
            "office_address": self.office_address,
            "services_supported": self.services_supported,
            "emergency_definition": self.emergency_definition,
            "emergency_routing_rules": self.emergency_routing_rules,
            "non_emergency_routing_rules": self.non_emergency_routing_rules,
            "call_transfer_rules": self.call_transfer_rules.to_dict(),
            "integration_constraints": self.integration_constraints,
            "after_hours_flow_summary": self.after_hours_flow_summary,
            "office_hours_flow_summary": self.office_hours_flow_summary,
            "questions_or_unknowns": self.questions_or_unknowns,
            "notes": self.notes,
            "version": self.version,
            "source_type": self.source_type,
            "updated_at_utc": self.updated_at_utc,
        }


@dataclass
class AgentSpec:
    account_id: str
    agent_name: str
    voice_style: str
    system_prompt: str
    key_variables: dict[str, Any]
    tool_invocation_placeholders: list[str]
    call_transfer_protocol: str
    transfer_fail_protocol: str

    # Metadata
    version: str
    source_type: str
    updated_at_utc: str

    def to_dict(self) -> dict:
        return {
            "account_id": self.account_id,
            "agent_name": self.agent_name,
            "voice_style": self.voice_style,
            "system_prompt": self.system_prompt,
            "key_variables": self.key_variables,
            "tool_invocation_placeholders": self.tool_invocation_placeholders,
            "call_transfer_protocol": self.call_transfer_protocol,
            "transfer_fail_protocol": self.transfer_fail_protocol,
            "version": self.version,
            "source_type": self.source_type,
            "updated_at_utc": self.updated_at_utc,
        }


# Required memo fields for evidence tracking
MEMO_EVIDENCE_FIELDS = [
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
]


@dataclass
class EvidenceEntry:
    value: Any
    snippets: list[str] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "snippets": self.snippets,
            "confidence": self.confidence,
        }


@dataclass
class Evidence:
    account_id: str
    version: str
    fields: dict[str, EvidenceEntry] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "account_id": self.account_id,
            "version": self.version,
            "fields": {k: v.to_dict() for k, v in self.fields.items()},
        }
