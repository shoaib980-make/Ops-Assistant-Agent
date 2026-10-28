"""
Security Guardrails and Prompt Injection Defense
------------------------------------------------
Provides:
1. Direct prompt injection detection (jailbreaks, instruction overrides).
2. Indirect prompt injection mitigation (content sanitization on tool outputs).
3. PII leak protection (blocking passwords, credit cards, secret keys).
4. Safe fallback messages.
"""

import re
from typing import Tuple

# Common prompt injection patterns (direct jailbreak attempts)
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"disregard\s+(the\s+)?(system\s+)?prompt",
    r"bypass\s+(the\s+)?(human|approval|guardrail|security)",
    r"reveal\s+(your\s+)?(system\s+prompt|hidden\s+rules)",
    r"export\s+(all\s+)?(passwords|credentials|secret\s+keys)",
    r"pretend\s+you\s+are\s+in\s+developer\s+mode",
    r"sudo\s+send",
]

# Sensitive PII patterns
PII_PATTERNS = [
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b.*(?:password|token|secret)\s*[:=]",
    r"\b(?:api[_-]?key|bearer|secret[_-]?token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}['\"]?",
    r"\b(?:\d{4}[ -]?){3}\d{4}\b",  # Credit card numbers
]


def validate_user_input(user_input: str) -> Tuple[bool, str]:
    """
    Checks incoming user messages against injection patterns.
    Returns (is_safe, error_or_sanitized_message).
    """
    cleaned = user_input.strip()

    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, cleaned, re.IGNORECASE):
            return (
                False,
                "Security Alert: Your request violates operational safety policy. "
                "Instruction overrides, security bypasses, and system prompt disclosures are prohibited."
            )

    return True, cleaned


def sanitize_tool_output(tool_output: str) -> str:
    """
    Mitigates indirect prompt injection by scanning tool outputs
    (database records or retrieved handbook text) for embedded malicious instructions.
    """
    sanitized = tool_output

    # Mask potential leaked API keys or secrets
    for pattern in PII_PATTERNS:
        sanitized = re.sub(pattern, "[REDACTED_CONFIDENTIAL_DATA]", sanitized, flags=re.IGNORECASE)

    # Neutralize embedded instruction overrides within external content
    for pattern in INJECTION_PATTERNS:
        sanitized = re.sub(
            pattern,
            "[BLOCKED_INDIRECT_INJECTION_ATTEMPT]",
            sanitized,
            flags=re.IGNORECASE
        )

    return sanitized

