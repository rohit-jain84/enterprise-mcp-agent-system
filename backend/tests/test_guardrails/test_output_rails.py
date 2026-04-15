"""Tests for output guardrails: PII redaction in agent responses."""

from __future__ import annotations

import re
from typing import Any

import pytest


# ---------------------------------------------------------------------------
# Output redaction helpers
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"\b(\+?1[-.]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CREDIT_CARD_RE = re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b")
_IP_ADDRESS_RE = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")


def redact_pii(text: str) -> tuple[str, list[dict[str, str]]]:
    """Redact PII from output text.

    Returns (redacted_text, list_of_redactions).
    Each redaction: {"type": str, "original": str, "replacement": str}.
    """
    redactions: list[dict[str, str]] = []

    def _replace(pattern: re.Pattern, pii_type: str, replacement: str, text: str) -> str:
        for match in pattern.finditer(text):
            redactions.append({
                "type": pii_type,
                "original": match.group(),
                "replacement": replacement,
            })
        return pattern.sub(replacement, text)

    text = _replace(_SSN_RE, "ssn", "[SSN REDACTED]", text)
    text = _replace(_CREDIT_CARD_RE, "credit_card", "[CREDIT CARD REDACTED]", text)
    text = _replace(_EMAIL_RE, "email", "[EMAIL REDACTED]", text)
    text = _replace(_PHONE_RE, "phone", "[PHONE REDACTED]", text)

    return text, redactions


def check_output_pii(text: str) -> dict[str, Any]:
    """Check if output contains PII that should be redacted.

    Returns {"has_pii": bool, "types": list[str]}.
    """
    types = []
    if _EMAIL_RE.search(text):
        types.append("email")
    if _PHONE_RE.search(text):
        types.append("phone")
    if _SSN_RE.search(text):
        types.append("ssn")
    if _CREDIT_CARD_RE.search(text):
        types.append("credit_card")
    return {"has_pii": len(types) > 0, "types": types}


# ---------------------------------------------------------------------------
# PII detection in output
# ---------------------------------------------------------------------------

class TestOutputPIIDetection:

    def test_detects_email(self):
        result = check_output_pii("The assignee is sarah@company.com")
        assert result["has_pii"] is True
        assert "email" in result["types"]

    def test_detects_phone(self):
        result = check_output_pii("Contact: (555) 123-4567")
        assert result["has_pii"] is True
        assert "phone" in result["types"]

    def test_detects_ssn(self):
        result = check_output_pii("SSN: 123-45-6789")
        assert result["has_pii"] is True
        assert "ssn" in result["types"]

    def test_detects_credit_card(self):
        result = check_output_pii("Card: 4111-1111-1111-1111")
        assert result["has_pii"] is True
        assert "credit_card" in result["types"]

    def test_no_pii_clean_text(self):
        result = check_output_pii("Sprint 24 is 62% complete with 13 points remaining.")
        assert result["has_pii"] is False
        assert result["types"] == []

    def test_multiple_pii_types(self):
        text = "Email: a@b.com, Phone: 555-123-4567, SSN: 123-45-6789"
        result = check_output_pii(text)
        assert result["has_pii"] is True
        assert "email" in result["types"]
        assert "phone" in result["types"]
        assert "ssn" in result["types"]


# ---------------------------------------------------------------------------
# PII redaction in output
# ---------------------------------------------------------------------------

class TestOutputPIIRedaction:

    def test_redact_email(self):
        text = "The ticket is assigned to sarah@company.com"
        redacted, changes = redact_pii(text)
        assert "[EMAIL REDACTED]" in redacted
        assert "sarah@company.com" not in redacted
        assert len(changes) == 1
        assert changes[0]["type"] == "email"

    def test_redact_phone(self):
        text = "Call (555) 123-4567 for support"
        redacted, changes = redact_pii(text)
        assert "[PHONE REDACTED]" in redacted
        assert "555" not in redacted or "REDACTED" in redacted
        assert any(c["type"] == "phone" for c in changes)

    def test_redact_ssn(self):
        text = "SSN on file: 123-45-6789"
        redacted, changes = redact_pii(text)
        assert "[SSN REDACTED]" in redacted
        assert "123-45-6789" not in redacted
        assert any(c["type"] == "ssn" for c in changes)

    def test_redact_credit_card(self):
        text = "Payment card: 4111-1111-1111-1111"
        redacted, changes = redact_pii(text)
        assert "[CREDIT CARD REDACTED]" in redacted
        assert "4111" not in redacted or "REDACTED" in redacted

    def test_redact_multiple_emails(self):
        text = "CC: alice@co.com and bob@co.com"
        redacted, changes = redact_pii(text)
        assert redacted.count("[EMAIL REDACTED]") == 2
        assert "alice@co.com" not in redacted
        assert "bob@co.com" not in redacted

    def test_clean_text_unchanged(self):
        text = "Sprint 24 has 13 remaining story points across 5 tickets."
        redacted, changes = redact_pii(text)
        assert redacted == text
        assert changes == []

    def test_redaction_preserves_context(self):
        text = "Sarah (sarah@company.com) is assigned to PAY-189"
        redacted, _ = redact_pii(text)
        assert "Sarah" in redacted
        assert "PAY-189" in redacted
        assert "sarah@company.com" not in redacted

    def test_redaction_returns_all_changes(self):
        text = "Email: a@b.com, SSN: 123-45-6789"
        _, changes = redact_pii(text)
        types = {c["type"] for c in changes}
        assert "email" in types
        assert "ssn" in types


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestOutputRailEdgeCases:

    def test_empty_string(self):
        redacted, changes = redact_pii("")
        assert redacted == ""
        assert changes == []

    def test_ticket_ids_not_redacted(self):
        """Ticket IDs like PAY-189 should not be treated as PII."""
        text = "Ticket PAY-189 is blocked by INFRA-42"
        result = check_output_pii(text)
        assert result["has_pii"] is False

    def test_ip_addresses_detected(self):
        """IP addresses in output should be flagged (not by default redact_pii)."""
        text = "Server 10.0.1.55 is down"
        assert _IP_ADDRESS_RE.search(text) is not None

    def test_version_numbers_not_pii(self):
        """Version strings like v3.2.1 should not be flagged."""
        text = "Deployed version 3.2.1 to production"
        result = check_output_pii(text)
        assert result["has_pii"] is False

    def test_markdown_formatting_preserved(self):
        text = "## Status\n- **PAY-189**: in progress\n- Contact: admin@internal.co"
        redacted, _ = redact_pii(text)
        assert "## Status" in redacted
        assert "**PAY-189**" in redacted
        assert "admin@internal.co" not in redacted
