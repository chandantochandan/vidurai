"""
Entity Extraction System
Extracts and preserves technical entities from memory text

Philosophy: "Technical details are anchors—never let them drift"
विस्मृति भी विद्या है (Forgetting too is knowledge)

Research Foundation:
- Named Entity Recognition (NER) for code artifacts
- Information extraction from unstructured text
- Lossless compression: preserve semantics, compress syntax
"""

import re
from typing import Dict, Any, List, Set, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path
from loguru import logger


@dataclass
class ExtractedEntities:
    """
    Collection of technical entities extracted from memory

    These entities MUST be preserved during compression/consolidation.
    """
    # Error information
    error_messages: List[str] = field(default_factory=list)
    error_types: List[str] = field(default_factory=list)  # TypeError, ValueError, etc.

    # Stack traces
    stack_traces: List[Dict[str, Any]] = field(default_factory=list)  # {file, line, function}

    # Code identifiers
    function_names: List[str] = field(default_factory=list)
    class_names: List[str] = field(default_factory=list)
    variable_names: List[str] = field(default_factory=list)

    # File system
    file_paths: List[str] = field(default_factory=list)
    line_numbers: List[int] = field(default_factory=list)

    # Configuration
    config_keys: List[str] = field(default_factory=list)  # API_KEY, DATABASE_URL
    environment_vars: Dict[str, str] = field(default_factory=dict)

    # Database
    database_fields: List[str] = field(default_factory=list)  # user.email, session.id

    # Temporal
    timestamps: List[str] = field(default_factory=list)  # ISO 8601 or other formats

    # Network
    urls: List[str] = field(default_factory=list)
    ip_addresses: List[str] = field(default_factory=list)

    # Other technical
    version_numbers: List[str] = field(default_factory=list)  # v1.2.3, 2.0.0
    hash_values: List[str] = field(default_factory=list)  # commit hashes, checksums

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for storage"""
        return asdict(self)

    def to_compact_string(self) -> str:
        """
        Create compact string representation for display

        Example: "[auth.py:42, validateToken(), jwt_timestamp, TypeError]"
        """
        items = []

        # Add most important entities
        if self.error_types:
            items.extend(self.error_types[:3])
        if self.file_paths:
            # Combine file + line
            for i, fp in enumerate(self.file_paths[:3]):
                if i < len(self.line_numbers):
                    items.append(f"{Path(fp).name}:{self.line_numbers[i]}")
                else:
                    items.append(Path(fp).name)
        if self.function_names:
            items.extend([f"{fn}()" for fn in self.function_names[:3]])
        if self.variable_names:
            items.extend(self.variable_names[:3])

        if not items:
            return "[]"

        return f"[{', '.join(items)}]"

    def merge(self, other: 'ExtractedEntities') -> 'ExtractedEntities':
        """
        Merge with another ExtractedEntities

        Returns:
            New ExtractedEntities with deduplicated union of both
        """
        return ExtractedEntities(
            error_messages=list(set(self.error_messages + other.error_messages)),
            error_types=list(set(self.error_types + other.error_types)),
            stack_traces=self.stack_traces + other.stack_traces,  # Keep all stack traces
            function_names=list(set(self.function_names + other.function_names)),
            class_names=list(set(self.class_names + other.class_names)),
            variable_names=list(set(self.variable_names + other.variable_names)),
            file_paths=list(set(self.file_paths + other.file_paths)),
            line_numbers=sorted(set(self.line_numbers + other.line_numbers)),
            config_keys=list(set(self.config_keys + other.config_keys)),
            environment_vars={**self.environment_vars, **other.environment_vars},
            database_fields=list(set(self.database_fields + other.database_fields)),
            timestamps=list(set(self.timestamps + other.timestamps)),
            urls=list(set(self.urls + other.urls)),
            ip_addresses=list(set(self.ip_addresses + other.ip_addresses)),
            version_numbers=list(set(self.version_numbers + other.version_numbers)),
            hash_values=list(set(self.hash_values + other.hash_values)),
        )

    def count(self) -> int:
        """Total number of entities extracted"""
        return (
            len(self.error_messages) +
            len(self.error_types) +
            len(self.stack_traces) +
            len(self.function_names) +
            len(self.class_names) +
            len(self.variable_names) +
            len(self.file_paths) +
            len(self.line_numbers) +
            len(self.config_keys) +
            len(self.environment_vars) +
            len(self.database_fields) +
            len(self.timestamps) +
            len(self.urls) +
            len(self.ip_addresses) +
            len(self.version_numbers) +
            len(self.hash_values)
        )


class EntityExtractor:
    """
    Extract technical entities from unstructured memory text

    Uses regex patterns optimized for code, errors, and technical content.
    """

    def __init__(self):
        """Initialize entity extractor with regex patterns"""

        # Error patterns
        self.error_type_pattern = re.compile(
            r'\b('
            r'TypeError|ValueError|KeyError|AttributeError|IndexError|'
            r'SyntaxError|NameError|ImportError|ModuleNotFoundError|'
            r'RuntimeError|AssertionError|FileNotFoundError|'
            r'PermissionError|TimeoutError|ConnectionError|'
            r'Exception|Error|Warning|Failed|Failure'
            r')\b',
            re.IGNORECASE
        )

        self.error_message_pattern = re.compile(
            r'(?:Error|Exception|Failed|Failure)[:\s]+([^\n]{10,200})',
            re.IGNORECASE
        )

        # Stack trace patterns
        # Python: "  File "/path/file.py", line 42, in function_name"
        self.python_stack_pattern = re.compile(
            r'File\s+"([^"]+)",\s+line\s+(\d+)(?:,\s+in\s+(\w+))?'
        )

        # JavaScript: "at functionName (file.js:42:10)"
        self.js_stack_pattern = re.compile(
            r'at\s+(\w+)\s+\(([^:]+):(\d+):(\d+)\)'
        )

        # Generic: "file.ext:line:col"
        self.generic_stack_pattern = re.compile(
            r'([\w/.-]+\.(?:py|js|ts|tsx|jsx|java|go|rs|cpp|c|h)):(\d+)(?::(\d+))?'
        )

        # Function/method patterns
        self.function_pattern = re.compile(
            r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)',  # functionName(...)
        )

        # Class patterns (CapitalizedWords)
        self.class_pattern = re.compile(
            r'\b([A-Z][a-zA-Z0-9]*(?:[A-Z][a-zA-Z0-9]*)+)\b'  # CamelCase
        )

        # Variable patterns (snake_case, camelCase)
        self.variable_pattern = re.compile(
            r'\b([a-z_][a-z0-9_]{2,})\b'  # At least 3 chars
        )

        # File path patterns (allow paths like src/auth.py or auth.py)
        self.file_path_pattern = re.compile(
            r'(?:[\w/.-]+/)?[\w.-]+\.(?:'
            r'py|js|ts|tsx|jsx|java|go|rs|cpp|c|h|hpp|'
            r'rb|php|swift|kt|kts|cs|'
            r'json|yaml|yml|toml|xml|html|css|scss|'
            r'md|txt|log|sql|sh|bash'
            r')\b'
        )

        # Config key patterns (SCREAMING_SNAKE_CASE)
        self.config_key_pattern = re.compile(
            r'\b([A-Z][A-Z0-9_]{2,})\b'
        )

        # Environment variable patterns (KEY=value)
        self.env_var_pattern = re.compile(
            r'([A-Z][A-Z0-9_]+)=([^\s;]+)'
        )

        # Database field patterns (table.column)
        self.db_field_pattern = re.compile(
            r'\b([a-z_][a-z0-9_]+)\.([a-z_][a-z0-9_]+)\b'
        )

        # Timestamp patterns (ISO 8601 and common formats)
        self.iso_timestamp_pattern = re.compile(
            r'\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d{3,6})?(?:Z|[+-]\d{2}:?\d{2})?'
        )

        # URL patterns
        self.url_pattern = re.compile(
            r'https?://[^\s<>"{}|\\^`\[\]]+',
            re.IGNORECASE
        )

        # IP address patterns
        self.ip_pattern = re.compile(
            r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        )

        # Version patterns (v1.2.3, 2.0.0, etc.)
        self.version_pattern = re.compile(
            r'\bv?\d+\.\d+(?:\.\d+)?(?:-[a-z0-9.]+)?\b',
            re.IGNORECASE
        )

        # Hash patterns (git commits, checksums - 7+ hex chars)
        self.hash_pattern = re.compile(
            r'\b[0-9a-f]{7,40}\b',
            re.IGNORECASE
        )

        logger.debug("Entity extractor initialized with pattern matching")

    def extract(self, text: str) -> ExtractedEntities:
        """
        Extract all technical entities from text

        Args:
            text: Memory verbatim or gist

        Returns:
            ExtractedEntities with all found entities
        """
        entities = ExtractedEntities()

        # Extract errors
        entities.error_types = self._extract_unique(text, self.error_type_pattern)
        entities.error_messages = self._extract_error_messages(text)

        # Extract stack traces
        entities.stack_traces = self._extract_stack_traces(text)

        # Extract from stack traces
        for trace in entities.stack_traces:
            if 'file' in trace:
                entities.file_paths.append(trace['file'])
            if 'line' in trace:
                entities.line_numbers.append(trace['line'])
            if 'function' in trace:
                entities.function_names.append(trace['function'])

        # Extract code identifiers
        entities.function_names.extend(self._extract_functions(text))
        entities.class_names = self._extract_unique(text, self.class_pattern)
        entities.variable_names = self._extract_variables(text)

        # Extract file paths
        entities.file_paths.extend(self._extract_unique(text, self.file_path_pattern))
        entities.file_paths = list(set(entities.file_paths))  # Deduplicate

        # Extract config
        entities.config_keys = self._extract_config_keys(text)
        entities.environment_vars = self._extract_env_vars(text)

        # Extract database fields (special handling for table.column format)
        db_matches = self.db_field_pattern.findall(text)
        entities.database_fields = [f"{table}.{column}" for table, column in db_matches if table and column]
        entities.database_fields = list(set(entities.database_fields))  # Deduplicate

        # Extract temporal
        entities.timestamps = self._extract_unique(text, self.iso_timestamp_pattern)

        # Extract network
        entities.urls = self._extract_unique(text, self.url_pattern)
        entities.ip_addresses = self._extract_unique(text, self.ip_pattern)

        # Extract versioning
        entities.version_numbers = self._extract_unique(text, self.version_pattern)
        entities.hash_values = self._extract_hashes(text)

        # Deduplicate all lists
        entities = self._deduplicate(entities)

        logger.debug(f"Extracted {entities.count()} entities from text")
        return entities

    def extract_batch(self, texts: List[str]) -> List[ExtractedEntities]:
        """
        Extract entities from multiple texts

        Args:
            texts: List of memory texts

        Returns:
            List of ExtractedEntities
        """
        return [self.extract(text) for text in texts]

    def _extract_unique(self, text: str, pattern: re.Pattern) -> List[str]:
        """Extract unique matches for a pattern"""
        matches = pattern.findall(text)
        # Handle tuples (from groups)
        if matches and isinstance(matches[0], tuple):
            matches = [m[0] if m[0] else m for m in matches]
        return list(set(matches))

    def _extract_error_messages(self, text: str) -> List[str]:
        """Extract error messages (full context)"""
        matches = self.error_message_pattern.findall(text)
        return [m.strip() for m in matches if len(m.strip()) > 10]

    def _extract_stack_traces(self, text: str) -> List[Dict[str, Any]]:
        """Extract stack trace information"""
        traces = []

        # Python stack traces
        for match in self.python_stack_pattern.finditer(text):
            traces.append({
                'file': match.group(1),
                'line': int(match.group(2)),
                'function': match.group(3) if match.group(3) else None,
                'format': 'python'
            })

        # JavaScript stack traces
        for match in self.js_stack_pattern.finditer(text):
            traces.append({
                'function': match.group(1),
                'file': match.group(2),
                'line': int(match.group(3)),
                'column': int(match.group(4)),
                'format': 'javascript'
            })

        # Generic stack traces
        for match in self.generic_stack_pattern.finditer(text):
            traces.append({
                'file': match.group(1),
                'line': int(match.group(2)),
                'column': int(match.group(3)) if match.group(3) else None,
                'format': 'generic'
            })

        return traces

    def _extract_functions(self, text: str) -> List[str]:
        """Extract function names (filter out common words)"""
        matches = self.function_pattern.findall(text)

        # Filter out common false positives
        blacklist = {
            'if', 'for', 'while', 'return', 'print', 'log', 'console',
            'get', 'set', 'is', 'has', 'new', 'this', 'super'
        }

        return list(set(m for m in matches if m.lower() not in blacklist))

    def _extract_variables(self, text: str) -> List[str]:
        """Extract variable names (filter out common words)"""
        matches = self.variable_pattern.findall(text)

        # Filter out common English words
        blacklist = {
            'the', 'and', 'for', 'are', 'with', 'from', 'that', 'this',
            'have', 'was', 'not', 'but', 'can', 'will', 'all', 'one',
            'been', 'has', 'had', 'were', 'said', 'use', 'each', 'which'
        }

        # Only keep if 3+ chars and not in blacklist
        filtered = [m for m in matches if len(m) >= 3 and m.lower() not in blacklist]

        # Limit to most common (avoid noise)
        from collections import Counter
        counter = Counter(filtered)
        top_variables = [var for var, count in counter.most_common(50)]

        return list(set(top_variables))

    def _extract_config_keys(self, text: str) -> List[str]:
        """Extract config keys (filter out common acronyms)"""
        matches = self.config_key_pattern.findall(text)

        # Filter out common acronyms/abbreviations
        blacklist = {
            'API', 'HTTP', 'HTTPS', 'URL', 'URI', 'SQL', 'HTML', 'CSS',
            'JSON', 'XML', 'JWT', 'AWS', 'GCP', 'SSH', 'TCP', 'UDP',
            'GET', 'POST', 'PUT', 'DELETE', 'PATCH'
        }

        # Keep if 3+ chars and looks like config (has underscore or is longer)
        return list(set(
            m for m in matches
            if (len(m) >= 3 and ('_' in m or len(m) > 4) and m not in blacklist)
        ))

    def _extract_env_vars(self, text: str) -> Dict[str, str]:
        """Extract environment variables with values"""
        matches = self.env_var_pattern.findall(text)
        return dict(matches)

    def _extract_hashes(self, text: str) -> List[str]:
        """Extract hash values (git commits, checksums)"""
        matches = self.hash_pattern.findall(text)

        # Filter out pure numbers and very short hashes
        return list(set(
            m for m in matches
            if not m.isdigit() and len(m) >= 7
        ))

    def _deduplicate(self, entities: ExtractedEntities) -> ExtractedEntities:
        """Deduplicate all entity lists"""
        entities.error_messages = list(set(entities.error_messages))
        entities.error_types = list(set(entities.error_types))
        entities.function_names = list(set(entities.function_names))
        entities.class_names = list(set(entities.class_names))
        entities.variable_names = list(set(entities.variable_names))
        entities.file_paths = list(set(entities.file_paths))
        entities.line_numbers = sorted(set(entities.line_numbers))
        entities.config_keys = list(set(entities.config_keys))
        entities.database_fields = list(set(entities.database_fields))
        entities.timestamps = list(set(entities.timestamps))
        entities.urls = list(set(entities.urls))
        entities.ip_addresses = list(set(entities.ip_addresses))
        entities.version_numbers = list(set(entities.version_numbers))
        entities.hash_values = list(set(entities.hash_values))

        return entities


# Convenience function
def extract_entities(text: str) -> ExtractedEntities:
    """
    Convenience function to extract entities from text

    Example:
        entities = extract_entities(
            "TypeError in auth.py line 42: Cannot find validateToken()"
        )
        print(entities.to_compact_string())
        # [TypeError, auth.py:42, validateToken()]
    """
    extractor = EntityExtractor()
    return extractor.extract(text)
