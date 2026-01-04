"""
PII Sanitizer for Knowledge Ingestion
Sprint 2 - "Ghost in the Shell"

Sanitizes sensitive data from ingested content before storage.
All patterns are compiled once for performance.
"""

import re
from typing import List, Tuple, Pattern
from dataclasses import dataclass
from loguru import logger


@dataclass
class SanitizationResult:
    """Result of sanitization with statistics."""
    cleaned_text: str
    redactions: int
    redaction_types: dict  # Type -> count


class PIISanitizer:
    """
    PII (Personally Identifiable Information) Sanitizer.

    Compiles regex patterns once at initialization for performance.
    All text MUST pass through clean() before being stored.

    Patterns:
    - OpenAI API keys: sk-... (48 chars)
    - AWS Access Keys: AKIA... (20 chars)
    - AWS Secret Keys: 40 char base64
    - Email addresses
    - Phone numbers (10 digits)
    - Credit card numbers (basic pattern)
    - SSN (Social Security Numbers)

    Usage:
        >>> sanitizer = PIISanitizer()
        >>> clean_text = sanitizer.clean("Contact me at john@example.com")
        >>> print(clean_text)
        'Contact me at [REDACTED_EMAIL]'
    """

    # Pattern definitions: (name, pattern, replacement)
    PATTERNS: List[Tuple[str, str, str]] = [
        # API Keys
        ("openai_key", r"sk-[a-zA-Z0-9]{20,}", "[REDACTED_OPENAI_KEY]"),
        ("openai_proj_key", r"sk-proj-[a-zA-Z0-9\-_]{20,}", "[REDACTED_OPENAI_KEY]"),
        ("anthropic_key", r"sk-ant-[a-zA-Z0-9\-_]{20,}", "[REDACTED_ANTHROPIC_KEY]"),
        ("aws_access_key", r"AKIA[0-9A-Z]{16}", "[REDACTED_AWS_KEY]"),
        ("aws_secret_key", r"(?<![A-Za-z0-9/+=])[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])", "[REDACTED_AWS_SECRET]"),
        ("google_api_key", r"AIza[0-9A-Za-z\-_]{35}", "[REDACTED_GOOGLE_KEY]"),
        ("github_token", r"gh[pousr]_[A-Za-z0-9_]{36,}", "[REDACTED_GITHUB_TOKEN]"),
        ("generic_api_key", r"(?i)api[_-]?key['\"]?\s*[:=]\s*['\"]?[a-zA-Z0-9\-_]{20,}['\"]?", "[REDACTED_API_KEY]"),

        # Personal Information
        ("email", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[REDACTED_EMAIL]"),
        ("phone_us", r"(?<!\d)(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}(?!\d)", "[REDACTED_PHONE]"),
        ("phone_intl", r"(?<!\d)\+\d{1,3}[-.\s]?\d{6,14}(?!\d)", "[REDACTED_PHONE]"),
        ("ssn", r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b", "[REDACTED_SSN]"),

        # Financial
        ("credit_card", r"\b(?:\d{4}[-\s]?){3}\d{4}\b", "[REDACTED_CC]"),

        # URLs with potential tokens
        ("url_with_token", r"https?://[^\s]*[?&](?:token|key|secret|api_key|apikey|access_token)=[^\s&]+", "[REDACTED_URL_WITH_TOKEN]"),

        # IP Addresses (optional - may be too aggressive)
        # ("ip_address", r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[REDACTED_IP]"),
    ]

    def __init__(self, extra_patterns: List[Tuple[str, str, str]] = None):
        """
        Initialize sanitizer with compiled patterns.

        Args:
            extra_patterns: Optional additional patterns as (name, regex, replacement)
        """
        self._compiled_patterns: List[Tuple[str, Pattern, str]] = []

        # Compile built-in patterns
        for name, pattern, replacement in self.PATTERNS:
            try:
                compiled = re.compile(pattern)
                self._compiled_patterns.append((name, compiled, replacement))
            except re.error as e:
                logger.warning(f"Failed to compile pattern '{name}': {e}")

        # Add extra patterns if provided
        if extra_patterns:
            for name, pattern, replacement in extra_patterns:
                try:
                    compiled = re.compile(pattern)
                    self._compiled_patterns.append((name, compiled, replacement))
                except re.error as e:
                    logger.warning(f"Failed to compile extra pattern '{name}': {e}")

        logger.debug(f"PIISanitizer initialized with {len(self._compiled_patterns)} patterns")

    def clean(self, text: str) -> str:
        """
        Clean text by replacing PII with redaction markers.

        Args:
            text: Raw text to sanitize

        Returns:
            Sanitized text with PII replaced
        """
        if not text:
            return text

        result = text
        for name, pattern, replacement in self._compiled_patterns:
            result = pattern.sub(replacement, result)

        return result

    def clean_with_stats(self, text: str) -> SanitizationResult:
        """
        Clean text and return statistics about redactions.

        Args:
            text: Raw text to sanitize

        Returns:
            SanitizationResult with cleaned text and redaction counts
        """
        if not text:
            return SanitizationResult(
                cleaned_text=text,
                redactions=0,
                redaction_types={}
            )

        result = text
        total_redactions = 0
        redaction_types = {}

        for name, pattern, replacement in self._compiled_patterns:
            matches = pattern.findall(result)
            if matches:
                count = len(matches)
                total_redactions += count
                redaction_types[name] = redaction_types.get(name, 0) + count
                result = pattern.sub(replacement, result)

        return SanitizationResult(
            cleaned_text=result,
            redactions=total_redactions,
            redaction_types=redaction_types
        )

    def has_pii(self, text: str) -> bool:
        """
        Check if text contains any PII patterns.

        Args:
            text: Text to check

        Returns:
            True if any PII pattern is found
        """
        if not text:
            return False

        for name, pattern, _ in self._compiled_patterns:
            if pattern.search(text):
                return True

        return False

    def get_pattern_names(self) -> List[str]:
        """Get list of active pattern names."""
        return [name for name, _, _ in self._compiled_patterns]
