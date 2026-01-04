"""
State Linker - User Focus Tracking & Path Resolution

The Nervous System's connection to user intent.
Tracks what file/line/selection the user is currently working on.

Glass Box Protocol: Reality Grounding
- Trust No One: Validate ALL paths exist on disk before accepting
- Never pollute state with hallucinated/missing paths
- Thread-safe state management

@version 2.1.0-Guardian
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from threading import RLock
from datetime import datetime
from dataclasses import dataclass, field
from loguru import logger


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class FocusContext:
    """
    Current user focus context.

    Represents what the user is actively working on.
    """
    file: Optional[Path] = None
    line: Optional[int] = None
    column: Optional[int] = None
    selection: Optional[str] = None
    project_root: Optional[Path] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'file': str(self.file) if self.file else None,
            'line': self.line,
            'column': self.column,
            'selection': self.selection,
            'project_root': str(self.project_root) if self.project_root else None,
            'timestamp': self.timestamp.isoformat(),
        }


# =============================================================================
# STATE LINKER
# =============================================================================

class StateLinker:
    """
    Tracks user's active context and resolves paths.

    Glass Box Protocol:
    - Reality Grounding: All paths validated before acceptance
    - Thread-Safe: RLock protects all state mutations
    - Fuzzy Resolution: Can find files from partial names

    Usage:
        linker = StateLinker()

        # Update from VS Code event
        linker.update_focus({
            'file': '/path/to/auth.py',
            'line': 42,
            'selection': 'def login():'
        })

        # Get current focus
        active_file = linker.get_active_file()

        # Resolve partial path
        full_path = linker.resolve_fuzzy_path('auth')
    """

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize StateLinker.

        Args:
            project_root: Default project root for path resolution
        """
        self._lock = RLock()
        self._active_context = FocusContext()
        self._recent_files: List[Path] = []
        self._max_recent = 10
        self._project_root = Path(project_root) if project_root else None

        logger.debug("StateLinker initialized")

    @property
    def active_context(self) -> Dict[str, Any]:
        """Get current active context as dictionary (thread-safe)."""
        with self._lock:
            return self._active_context.to_dict()

    def update_focus(self, context: Dict[str, Any]) -> bool:
        """
        Update user focus context.

        Glass Box Protocol: Reality Grounding
        - Validates file path exists before accepting
        - Ignores updates with non-existent files

        Args:
            context: Dictionary with focus data:
                - file: Path to active file (required for validation)
                - line: Current line number
                - column: Current column
                - selection: Selected text
                - project_root: Project root path

        Returns:
            True if update accepted, False if rejected (file doesn't exist)
        """
        file_path_str = context.get('file')

        # Reality Grounding: Validate file exists
        if file_path_str:
            file_path = Path(file_path_str)

            # TRUST NO ONE: Verify file exists on disk
            if not file_path.exists():
                logger.warning(
                    f"StateLinker: Rejected update - file not found: {file_path_str}"
                )
                return False

            if not file_path.is_file():
                logger.warning(
                    f"StateLinker: Rejected update - not a file: {file_path_str}"
                )
                return False
        else:
            file_path = None

        # Validate project_root if provided
        project_root_str = context.get('project_root')
        if project_root_str:
            project_root = Path(project_root_str)
            if not project_root.exists() or not project_root.is_dir():
                logger.warning(
                    f"StateLinker: Invalid project_root ignored: {project_root_str}"
                )
                project_root = self._project_root
        else:
            project_root = self._project_root

        # Update state (thread-safe)
        with self._lock:
            self._active_context = FocusContext(
                file=file_path,
                line=context.get('line'),
                column=context.get('column'),
                selection=context.get('selection'),
                project_root=project_root,
                timestamp=datetime.now()
            )

            # Add to recent files
            if file_path and file_path not in self._recent_files:
                self._recent_files.insert(0, file_path)
                self._recent_files = self._recent_files[:self._max_recent]

        logger.debug(f"StateLinker: Focus updated to {file_path}")
        return True

    def get_active_file(self) -> Optional[Path]:
        """
        Get the currently active file.

        Returns:
            Path to active file, or None if no active context
        """
        with self._lock:
            return self._active_context.file

    def get_active_line(self) -> Optional[int]:
        """Get the current line number."""
        with self._lock:
            return self._active_context.line

    def get_selection(self) -> Optional[str]:
        """Get the current selection text."""
        with self._lock:
            return self._active_context.selection

    def get_recent_files(self, limit: int = 5) -> List[Path]:
        """
        Get recently accessed files.

        Args:
            limit: Max number of files to return

        Returns:
            List of recent file paths
        """
        with self._lock:
            return self._recent_files[:limit]

    def resolve_fuzzy_path(
        self,
        partial_path: str,
        project_root: Optional[Path] = None
    ) -> Optional[Path]:
        """
        Resolve a partial/fuzzy path to a full path.

        If user says "auth", find "src/core/auth.py".

        Args:
            partial_path: Partial file name or path (e.g., "auth", "auth.py")
            project_root: Root to search from (uses default if not specified)

        Returns:
            Full Path if found, None otherwise
        """
        root = project_root or self._project_root

        if not root:
            # Try current working directory
            root = Path.cwd()

        if not root.exists():
            return None

        # Normalize the partial path
        partial = partial_path.strip()

        # If it's already a valid absolute path, return it
        if os.path.isabs(partial):
            abs_path = Path(partial)
            if abs_path.exists() and abs_path.is_file():
                return abs_path
            return None

        # Strategy 1: Direct match (relative from root)
        direct = root / partial
        if direct.exists() and direct.is_file():
            return direct

        # Strategy 2: Add .py extension if missing
        if not partial.endswith('.py'):
            with_py = root / f"{partial}.py"
            if with_py.exists() and with_py.is_file():
                return with_py

        # Strategy 3: Recursive glob search
        # Search for **/partial* pattern
        try:
            # Exact filename match first
            pattern = f"**/{partial}"
            matches = list(root.glob(pattern))
            if matches:
                # Return first file match
                for match in matches:
                    if match.is_file():
                        return match

            # With .py extension
            if not partial.endswith('.py'):
                pattern = f"**/{partial}.py"
                matches = list(root.glob(pattern))
                if matches:
                    for match in matches:
                        if match.is_file():
                            return match

            # Partial name match (contains)
            pattern = f"**/*{partial}*"
            matches = list(root.glob(pattern))
            if matches:
                # Prefer .py files
                py_matches = [m for m in matches if m.suffix == '.py' and m.is_file()]
                if py_matches:
                    return py_matches[0]

                # Any file match
                for match in matches:
                    if match.is_file():
                        return match

        except Exception as e:
            logger.warning(f"StateLinker: Glob search failed: {e}")

        return None

    def set_project_root(self, project_root: Path) -> bool:
        """
        Set the default project root.

        Args:
            project_root: Path to project root

        Returns:
            True if valid and set, False otherwise
        """
        if not project_root.exists() or not project_root.is_dir():
            logger.warning(f"StateLinker: Invalid project root: {project_root}")
            return False

        with self._lock:
            self._project_root = project_root

        logger.debug(f"StateLinker: Project root set to {project_root}")
        return True

    def clear(self) -> None:
        """Clear all state."""
        with self._lock:
            self._active_context = FocusContext()
            self._recent_files = []

        logger.debug("StateLinker: State cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get state linker statistics."""
        with self._lock:
            return {
                'has_active_file': self._active_context.file is not None,
                'active_file': str(self._active_context.file) if self._active_context.file else None,
                'active_line': self._active_context.line,
                'recent_files_count': len(self._recent_files),
                'project_root': str(self._project_root) if self._project_root else None,
                'last_update': self._active_context.timestamp.isoformat(),
            }


# =============================================================================
# MODULE-LEVEL CONVENIENCE
# =============================================================================

_default_linker: Optional[StateLinker] = None


def get_linker(project_root: Optional[Path] = None) -> StateLinker:
    """
    Get or create the default StateLinker instance.

    Args:
        project_root: Optional project root path

    Returns:
        StateLinker singleton
    """
    global _default_linker
    if _default_linker is None:
        _default_linker = StateLinker(project_root=project_root)
    elif project_root:
        _default_linker.set_project_root(project_root)
    return _default_linker


def update_focus(context: Dict[str, Any]) -> bool:
    """
    Convenience function to update focus.

    Usage:
        from vidurai.core.state import update_focus
        update_focus({'file': '/path/to/file.py', 'line': 42})
    """
    return get_linker().update_focus(context)


def reset_linker() -> None:
    """Reset the default linker instance."""
    global _default_linker
    if _default_linker:
        _default_linker.clear()
    _default_linker = None


# =============================================================================
# CLI TEST INTERFACE
# =============================================================================

def _test_cli():
    """
    Test function for manual verification.

    Usage:
        python -m vidurai.core.state.linker --test
    """
    import argparse
    import tempfile

    parser = argparse.ArgumentParser(description="State Linker Test")
    parser.add_argument("--test", action="store_true", help="Run test cases")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--resolve", type=str, help="Resolve a fuzzy path")

    args = parser.parse_args()

    linker = StateLinker(project_root=Path.cwd())

    if args.stats:
        stats = linker.get_stats()
        print("\n=== State Linker Statistics ===")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        return

    if args.resolve:
        result = linker.resolve_fuzzy_path(args.resolve)
        if result:
            print(f"Resolved: {args.resolve} -> {result}")
        else:
            print(f"Could not resolve: {args.resolve}")
        return

    if args.test:
        print("\n=== State Linker Test Cases ===\n")

        # Create temp file for testing
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("# Test file\ndef hello(): pass\n")
            temp_path = f.name

        try:
            # Test 1: Valid file update
            result = linker.update_focus({'file': temp_path, 'line': 1})
            print(f"[{'PASS' if result else 'FAIL'}] Valid file update")

            # Test 2: Get active file
            active = linker.get_active_file()
            print(f"[{'PASS' if active else 'FAIL'}] Get active file: {active}")

            # Test 3: Invalid file (Reality Grounding)
            result = linker.update_focus({'file': '/nonexistent/ghost.py', 'line': 1})
            print(f"[{'PASS' if not result else 'FAIL'}] Reject nonexistent file")

            # Test 4: Recent files
            recent = linker.get_recent_files()
            print(f"[{'PASS' if len(recent) > 0 else 'FAIL'}] Recent files: {len(recent)}")

            # Test 5: Stats
            stats = linker.get_stats()
            print(f"[{'PASS' if stats else 'FAIL'}] Get stats")

        finally:
            # Cleanup
            Path(temp_path).unlink(missing_ok=True)

        print()


if __name__ == "__main__":
    _test_cli()
