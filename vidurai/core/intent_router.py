"""
Hybrid Intent Router for Vidurai REPL
Sprint 3 - The Interaction Layer

Routes user queries to the appropriate handler:
- CODE_RETRIEVAL: Show file contents
- MEMORY_QUERY: Search project memories
- COMMAND: Execute system commands

Design:
- Latency First: All routing logic runs locally (<10ms)
- Context-Aware: Checks if query tokens match actual project files
- No API calls in the routing path
"""

import os
import re
import time
from enum import Enum, auto
from pathlib import Path
from typing import Set, Tuple, Optional, List
from dataclasses import dataclass

from loguru import logger


class IntentType(Enum):
    """Types of user intents in the REPL."""
    CODE_RETRIEVAL = auto()  # User wants to see file contents
    MEMORY_QUERY = auto()    # User wants to search memories (narrative)
    COMMAND = auto()         # User wants to execute a system command


@dataclass
class RoutingResult:
    """Result of intent routing with metadata."""
    intent: IntentType
    query: str
    matched_file: Optional[str] = None  # File that was matched (for CODE_RETRIEVAL)
    command: Optional[str] = None       # Command name (for COMMAND)
    confidence: float = 1.0             # Routing confidence
    routing_time_ms: float = 0.0        # Time taken to route


class IntentRouter:
    """
    Hybrid Intent Router for the Vidurai REPL.

    Routes user queries using a fast, local algorithm:
    1. System Commands: Direct matches (exit, stats, pin, etc.)
    2. Explicit Verbs: Code retrieval keywords (cat, read, show, open)
    3. Entity Check: Query tokens matching actual filenames
    4. Default: Memory/narrative query

    Performance Target: <10ms routing time (no API calls)

    Usage:
        >>> router = IntentRouter(project_path="/my/project")
        >>> result = router.route("show me main.py")
        >>> print(result.intent)  # IntentType.CODE_RETRIEVAL
        >>> print(result.matched_file)  # "main.py"
    """

    # System commands that trigger COMMAND intent
    SYSTEM_COMMANDS = {
        'exit', 'quit', 'bye', 'q',
        'help', '?',
        'stats', 'statistics',
        'pin', 'unpin', 'pins',
        'ingest', 'import',
        'clear', 'reset',
        'context', 'ctx',
        'recall', 'search',
        'recent', 'history',
        'export',
        'refresh', 'reload',
    }

    # Explicit verbs that indicate code retrieval
    CODE_VERBS = {
        'cat', 'read', 'show', 'open', 'view', 'display',
        'print', 'dump', 'get', 'fetch', 'load',
        'see', 'look', 'examine', 'inspect',
    }

    # File extensions to recognize
    CODE_EXTENSIONS = {
        '.py', '.js', '.ts', '.tsx', '.jsx',
        '.java', '.c', '.cpp', '.h', '.hpp',
        '.go', '.rs', '.rb', '.php',
        '.html', '.css', '.scss', '.less',
        '.json', '.yaml', '.yml', '.toml', '.xml',
        '.md', '.txt', '.rst', '.csv',
        '.sh', '.bash', '.zsh', '.fish',
        '.sql', '.graphql',
        '.dockerfile', '.docker',
        '.env', '.gitignore', '.editorconfig',
    }

    def __init__(
        self,
        project_path: str = ".",
        cache_files: bool = True,
        max_cache_age_seconds: float = 30.0
    ):
        """
        Initialize the intent router.

        Args:
            project_path: Path to the project for file scanning
            cache_files: Whether to cache file list (recommended for speed)
            max_cache_age_seconds: Max age before refreshing file cache
        """
        self.project_path = Path(project_path).resolve()
        self.cache_files = cache_files
        self.max_cache_age = max_cache_age_seconds

        # File cache
        self._file_cache: Set[str] = set()
        self._file_cache_time: float = 0.0
        self._file_paths: dict = {}  # filename -> full path

        # Initial file scan
        if cache_files:
            self._refresh_file_cache()

        logger.debug(f"IntentRouter initialized for {self.project_path}")

    def _refresh_file_cache(self) -> None:
        """Refresh the cached list of project files."""
        start = time.time()
        self._file_cache.clear()
        self._file_paths.clear()

        try:
            # Walk project directory (limit depth for speed)
            max_depth = 3
            for root, dirs, files in os.walk(self.project_path):
                # Calculate depth
                depth = root.replace(str(self.project_path), '').count(os.sep)
                if depth >= max_depth:
                    dirs.clear()  # Don't descend further
                    continue

                # Skip hidden and common ignore directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {
                    'node_modules', '__pycache__', 'venv', '.venv', 'env',
                    'dist', 'build', '.git', '.idea', '.vscode',
                    'target', 'vendor', 'coverage', '.pytest_cache'
                }]

                # Add files
                for f in files:
                    if not f.startswith('.'):
                        self._file_cache.add(f.lower())
                        rel_path = os.path.relpath(os.path.join(root, f), self.project_path)
                        self._file_paths[f.lower()] = rel_path

            self._file_cache_time = time.time()
            elapsed = (time.time() - start) * 1000
            logger.debug(f"File cache refreshed: {len(self._file_cache)} files in {elapsed:.1f}ms")

        except Exception as e:
            logger.warning(f"Failed to scan project files: {e}")

    def _get_project_files(self) -> Set[str]:
        """Get cached project files, refreshing if stale."""
        if not self.cache_files:
            self._refresh_file_cache()
            return self._file_cache

        # Check cache age
        if time.time() - self._file_cache_time > self.max_cache_age:
            self._refresh_file_cache()

        return self._file_cache

    def _tokenize(self, query: str) -> List[str]:
        """
        Tokenize query into words for entity matching.

        Handles:
        - Splitting on whitespace and punctuation
        - Preserving filenames with extensions
        - Case normalization
        """
        # Split on whitespace
        tokens = query.split()

        # Further split on common separators but preserve file paths
        result = []
        for token in tokens:
            # Check if it looks like a path or filename
            if '/' in token or '\\' in token or any(token.endswith(ext) for ext in self.CODE_EXTENSIONS):
                # Keep path components together, extract filename
                parts = token.replace('\\', '/').split('/')
                result.extend(parts)
            else:
                # Split on punctuation except dots in potential filenames
                parts = re.split(r'[,;:!?\'"()\[\]{}]', token)
                result.extend(p for p in parts if p)

        return [t.lower().strip() for t in result if t.strip()]

    def _find_matching_file(self, tokens: List[str]) -> Optional[str]:
        """
        Find a project file that matches any token.

        Returns the relative path to the matched file, or None.
        """
        project_files = self._get_project_files()

        for token in tokens:
            token_lower = token.lower()

            # Exact match
            if token_lower in project_files:
                return self._file_paths.get(token_lower, token)

            # Match with common extensions
            for ext in self.CODE_EXTENSIONS:
                with_ext = token_lower + ext
                if with_ext in project_files:
                    return self._file_paths.get(with_ext, with_ext)

        return None

    def route(self, query: str, project_path: str = None) -> RoutingResult:
        """
        Route a user query to the appropriate intent.

        Order of operations (CTO Mandate):
        1. System Commands: If starts with known command -> COMMAND
        2. Explicit Verbs: If starts with code verb -> CODE_RETRIEVAL
        3. Entity Check: If any token matches a filename -> CODE_RETRIEVAL
        4. Default: MEMORY_QUERY (narrative search)

        Args:
            query: User's input query
            project_path: Optional override for project path

        Returns:
            RoutingResult with intent and metadata
        """
        start = time.time()

        # Update project path if provided
        if project_path and Path(project_path).resolve() != self.project_path:
            self.project_path = Path(project_path).resolve()
            self._refresh_file_cache()

        query = query.strip()
        query_lower = query.lower()
        tokens = self._tokenize(query)

        result = RoutingResult(
            intent=IntentType.MEMORY_QUERY,  # Default
            query=query
        )

        if not query:
            result.routing_time_ms = (time.time() - start) * 1000
            return result

        first_word = tokens[0] if tokens else ""

        # 1. System Commands
        if first_word in self.SYSTEM_COMMANDS:
            result.intent = IntentType.COMMAND
            result.command = first_word
            result.confidence = 1.0
            result.routing_time_ms = (time.time() - start) * 1000
            logger.debug(f"Routed to COMMAND: {first_word}")
            return result

        # 2. Explicit Verbs -> CODE_RETRIEVAL
        if first_word in self.CODE_VERBS:
            result.intent = IntentType.CODE_RETRIEVAL
            result.confidence = 0.9

            # Try to find the file in remaining tokens
            remaining_tokens = tokens[1:] if len(tokens) > 1 else tokens
            matched = self._find_matching_file(remaining_tokens)
            if matched:
                result.matched_file = matched
                result.confidence = 1.0

            result.routing_time_ms = (time.time() - start) * 1000
            logger.debug(f"Routed to CODE_RETRIEVAL (verb): {first_word}, file={matched}")
            return result

        # 3. Entity Check - Any token matches a filename
        matched_file = self._find_matching_file(tokens)
        if matched_file:
            result.intent = IntentType.CODE_RETRIEVAL
            result.matched_file = matched_file
            result.confidence = 0.85
            result.routing_time_ms = (time.time() - start) * 1000
            logger.debug(f"Routed to CODE_RETRIEVAL (entity): {matched_file}")
            return result

        # 4. Default: MEMORY_QUERY
        result.intent = IntentType.MEMORY_QUERY
        result.confidence = 0.7
        result.routing_time_ms = (time.time() - start) * 1000
        logger.debug(f"Routed to MEMORY_QUERY (default)")
        return result

    def refresh(self) -> int:
        """
        Force refresh the file cache.

        Returns:
            Number of files in cache
        """
        self._refresh_file_cache()
        return len(self._file_cache)

    def get_file_path(self, filename: str) -> Optional[Path]:
        """
        Get the full path to a project file.

        Args:
            filename: Filename to look up

        Returns:
            Full Path to the file, or None if not found
        """
        filename_lower = filename.lower()

        # Check cache first
        if filename_lower in self._file_paths:
            return self.project_path / self._file_paths[filename_lower]

        # Direct path check
        direct_path = self.project_path / filename
        if direct_path.exists():
            return direct_path

        # Try with common extensions
        for ext in self.CODE_EXTENSIONS:
            with_ext = filename_lower + ext
            if with_ext in self._file_paths:
                return self.project_path / self._file_paths[with_ext]

        return None
