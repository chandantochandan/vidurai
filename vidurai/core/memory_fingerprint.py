"""
Memory Fingerprinting System
Detects duplicate and near-duplicate memories for aggregation

Research Foundation:
- "Repeated exposure strengthens initial memory, but after consolidation,
  additional exposures are redundant" (Consolidation Theory)
- "The brain doesn't store every repetition - it updates existing traces"

विस्मृति भी विद्या है (Forgetting too is knowledge)
जय विदुराई! 🕉️
"""

import hashlib
import re
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class MemoryFingerprint:
    """
    Unique identifier for memory content

    Used to detect:
    - Exact duplicates (same hash)
    - Near duplicates (same pattern_hash + file)
    - Repeated errors (same error_type + file)
    """

    # Full content hash (for exact duplicates)
    content_hash: str

    # Pattern hash (normalized content, for near-duplicates)
    pattern_hash: str

    # Error type (if this is an error memory)
    error_type: Optional[str] = None

    # File path (for file-specific aggregation)
    file_path: Optional[str] = None

    # Line number range (for location clustering)
    line_range: Optional[str] = None

    def __str__(self) -> str:
        """String representation for storage"""
        parts = [self.pattern_hash]
        if self.error_type:
            parts.append(f"err:{self.error_type}")
        if self.file_path:
            parts.append(f"file:{self._normalize_path(self.file_path)}")
        if self.line_range:
            parts.append(f"lines:{self.line_range}")
        return "|".join(parts)

    @staticmethod
    def _normalize_path(path: str) -> str:
        """Normalize file path for comparison"""
        # Get just the filename (ignore directory)
        return path.split('/')[-1] if '/' in path else path

    def matches(self, other: 'MemoryFingerprint',
                threshold: str = 'pattern') -> bool:
        """
        Check if two fingerprints match

        Thresholds:
        - 'exact': Content hash must match exactly
        - 'pattern': Pattern hash must match (default)
        - 'file': Same file + error type
        """
        if threshold == 'exact':
            return self.content_hash == other.content_hash

        elif threshold == 'pattern':
            # Pattern hash + same file + same error type
            return (
                self.pattern_hash == other.pattern_hash and
                self._normalize_path(self.file_path or '') ==
                self._normalize_path(other.file_path or '') and
                self.error_type == other.error_type
            )

        elif threshold == 'file':
            # Just same file + error type (loose matching)
            return (
                self._normalize_path(self.file_path or '') ==
                self._normalize_path(other.file_path or '') and
                self.error_type == other.error_type
            )

        return False


class MemoryFingerprinter:
    """
    Generate fingerprints for memories to detect duplicates

    Philosophy: "The brain recognizes patterns, not exact repetitions"
    """

    # Error type patterns (TypeScript, Python, etc.)
    ERROR_PATTERNS = [
        (r"TypeError", "TypeError"),
        (r"SyntaxError", "SyntaxError"),
        (r"Cannot find name", "NameError"),
        (r"Unexpected keyword or identifier", "SyntaxError"),
        (r"';' expected", "SyntaxError"),
        (r"ImportError", "ImportError"),
        (r"ModuleNotFoundError", "ModuleNotFoundError"),
        (r"AttributeError", "AttributeError"),
        (r"KeyError", "KeyError"),
        (r"ValueError", "ValueError"),
        (r"undefined is not", "UndefinedError"),
        (r"null is not", "NullError"),
    ]

    def __init__(self):
        """Initialize fingerprinter with compiled patterns"""
        self.error_patterns = [
            (re.compile(pattern, re.IGNORECASE), error_type)
            for pattern, error_type in self.ERROR_PATTERNS
        ]

    def fingerprint(
        self,
        content: str,
        metadata: Optional[Dict] = None
    ) -> MemoryFingerprint:
        """
        Generate fingerprint for memory content

        Args:
            content: Memory verbatim or gist
            metadata: Optional metadata with file_path, line_number, etc.

        Returns:
            MemoryFingerprint object
        """
        metadata = metadata or {}

        # 1. Full content hash (exact duplicates)
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        # 2. Pattern hash (normalized content for near-duplicates)
        normalized = self._normalize_content(content)
        pattern_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16]

        # 3. Detect error type
        error_type = self._detect_error_type(content)

        # 4. Extract file path
        file_path = metadata.get('file') or metadata.get('file_path')

        # 5. Line range (bucket lines into ranges of 10)
        line_range = self._get_line_range(metadata.get('line') or metadata.get('line_number'))

        return MemoryFingerprint(
            content_hash=content_hash,
            pattern_hash=pattern_hash,
            error_type=error_type,
            file_path=file_path,
            line_range=line_range
        )

    def _normalize_content(self, content: str) -> str:
        """
        Normalize content for pattern matching

        Removes:
        - Line numbers (Line 42 → Line X)
        - Timestamps
        - Variable names in some cases
        - Extra whitespace
        """
        normalized = content

        # Replace line numbers with placeholder
        normalized = re.sub(r'\bLine \d+\b', 'Line X', normalized, flags=re.IGNORECASE)

        # Replace timestamps
        normalized = re.sub(r'\d{4}-\d{2}-\d{2}', 'DATE', normalized)
        normalized = re.sub(r'\d{2}:\d{2}:\d{2}', 'TIME', normalized)

        # Normalize whitespace
        normalized = ' '.join(normalized.split())

        # Lowercase for case-insensitive matching
        normalized = normalized.lower()

        return normalized

    def _detect_error_type(self, content: str) -> Optional[str]:
        """
        Detect error type from content

        Returns error type string or None
        """
        for pattern, error_type in self.error_patterns:
            if pattern.search(content):
                return error_type

        # Generic "Error" detection
        if 'error' in content.lower():
            return "GenericError"

        return None

    def _get_line_range(self, line_number: Optional[int]) -> Optional[str]:
        """
        Bucket line numbers into ranges

        Examples:
        - Line 1-10 → "0-10"
        - Line 42 → "40-50"
        - Line 157 → "150-160"
        """
        if line_number is None:
            return None

        # Bucket into groups of 10
        range_start = (line_number // 10) * 10
        range_end = range_start + 10

        return f"{range_start}-{range_end}"

    def are_duplicates(
        self,
        fp1: MemoryFingerprint,
        fp2: MemoryFingerprint,
        threshold: str = 'pattern'
    ) -> bool:
        """
        Check if two fingerprints represent duplicate memories

        Args:
            fp1: First fingerprint
            fp2: Second fingerprint
            threshold: 'exact', 'pattern', or 'file'

        Returns:
            True if duplicates
        """
        return fp1.matches(fp2, threshold=threshold)
