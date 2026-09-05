"""
Prompt Sanitizer, Security Redactor, and Evidence Hallucination Validator for Phase 3 AI.
"""
import re
from typing import List, Tuple, Set

# Regex patterns for sensitive data leakage prevention
SENSITIVE_PATTERNS = [
    # Passwords / Secrets / API keys
    (re.compile(r'(?i)(?:api[_-]?key|secret|password|bearer|auth[_-]?token)\s*[:=]\s*["\']?([a-zA-Z0-9_\-\.]{8,})["\']?'), "[REDACTED_SECRET]"),
    # DB connection strings
    (re.compile(r'postgresql://[^\s@]+:[^\s@]+@[^\s/]+/[^\s]+'), "[REDACTED_DB_URL]"),
    # Credit Card 13-16 digit numbers
    (re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'), "[REDACTED_CARD_NUMBER]"),
    # JWT tokens
    (re.compile(r'eyJ[a-zA-Z0-9_\-]{10,}\.eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}'), "[REDACTED_JWT]"),
]

# Injection & Hijack heuristics
PROMPT_INJECTION_PATTERNS = [
    re.compile(r'(?i)ignore\s+(all\s+)?(previous|prior|above)\s+instructions'),
    re.compile(r'(?i)disregard\s+(all\s+)?(previous|prior|system)\s+rules'),
    re.compile(r'(?i)you\s+are\s+now\s+(in\s+)?(developer\s+mode|unrestricted|god\s+mode)'),
    re.compile(r'(?i)output\s+(your\s+)?(system\s+prompt|instructions|initial\s+prompt)'),
    re.compile(r'(?i)reveal\s+(api\s+key|database\s+password|credentials)'),
]

# Common entity ID pattern in CashPilot AI
ENTITY_ID_PATTERN = re.compile(
    r'\b(ORD-\d+|pay_[A-Za-z0-9_]+|SETL-\d+|BANK-\d+|REF-[A-Za-z0-9\-]+|CASE-[A-Za-z0-9\-]+|TXN-[A-Za-z0-9\-]+)\b'
)


def sanitize_input(prompt: str, max_chars: int = 2000) -> str:
    """
    Sanitizes user input by enforcing length limits, stripping control chars,
    and neutralizing prompt injection attempts.
    """
    if not prompt:
        return ""

    # Truncate
    cleaned = prompt.strip()[:max_chars]

    # Neutralize injection attempts
    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern.search(cleaned):
            cleaned = pattern.sub("[FILTERED_INSTRUCTION_OVERRIDE]", cleaned)

    return cleaned


def mask_sensitive_data(text: str) -> str:
    """
    Scans text and masks any discovered database URLs, API keys, passwords,
    or financial card numbers to prevent accidental data leaks.
    """
    if not text:
        return ""

    sanitized = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)

    return sanitized


def validate_evidence_references(text: str, allowed_evidence_ids: List[str]) -> Tuple[bool, List[str]]:
    """
    Verifies that any entity IDs (e.g., ORD-*, pay_*, SETL-*, BANK-*, CASE-*) mentioned
    in the AI-generated text actually exist within the verified evidence package.
    
    Returns:
        is_valid: True if no hallucinated entity IDs are referenced.
        hallucinated_ids: List of entity IDs mentioned that were NOT in allowed_evidence_ids.
    """
    if not text:
        return True, []

    allowed_set: Set[str] = set(allowed_evidence_ids or [])
    found_matches = ENTITY_ID_PATTERN.findall(text)

    hallucinated = []
    for match in set(found_matches):
        if match not in allowed_set:
            hallucinated.append(match)

    return (len(hallucinated) == 0, hallucinated)
