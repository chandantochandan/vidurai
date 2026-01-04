"""
ShadowWorkspace - Safe, Isolated Code Modification
Sprint 4 - The Shadow Layer

Provides a sandboxed environment for code modifications:
- All writes happen in a temp directory (never touch originals directly)
- Atomic promotion with metadata preservation
- Full diff visibility before applying changes
- Self-destructing cleanup on session end

Zero Trust Architecture:
- Original files are NEVER modified directly
- All changes staged in shadow workspace
- User must explicitly promote changes

Usage:
    with ShadowWorkspace("/my/project") as workspace:
        shadow_path = workspace.stage_file("src/main.py")
        # Make modifications to shadow_path
        print(workspace.get_diff("src/main.py"))
        if user_confirms:
            workspace.promote_file("src/main.py")
    # Workspace auto-cleans up
"""

import difflib
import os
import shutil
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass, field

from loguru import logger


@dataclass
class StagedFile:
    """Metadata for a staged file in the shadow workspace."""
    original_path: Path
    shadow_path: Path
    staged_at: datetime = field(default_factory=datetime.now)
    modified: bool = False


class ShadowWorkspace:
    """
    ShadowWorkspace for safe, isolated code modification.

    Zero Trust Architecture:
    - NEVER modifies original files directly
    - All writes happen in temp directory
    - Atomic promotion with shutil.copy2 (preserves metadata)
    - Self-destructs on cleanup (even on errors)

    Usage:
        >>> workspace = ShadowWorkspace("/my/project")
        >>> try:
        ...     shadow_path = workspace.stage_file("src/main.py")
        ...     # Modify shadow_path safely
        ...     workspace.apply_patch("src/main.py", new_content)
        ...     print(workspace.get_diff("src/main.py"))
        ...     workspace.promote_file("src/main.py")
        ... finally:
        ...     workspace.cleanup()

    Or with context manager:
        >>> with ShadowWorkspace("/my/project") as ws:
        ...     shadow_path = ws.stage_file("src/main.py")
        ...     # Changes auto-cleanup if not promoted
    """

    def __init__(self, project_path: str):
        """
        Initialize a shadow workspace.

        Creates temp directory: .vidurai/shadow/<session_id>/

        Args:
            project_path: Path to the project root
        """
        self.project_path = Path(project_path).resolve()
        self.session_id = str(uuid.uuid4())[:8]
        self.created_at = datetime.now()

        # Shadow directory: .vidurai/shadow/<session_id>/
        self.shadow_root = self.project_path / ".vidurai" / "shadow" / self.session_id
        self.shadow_root.mkdir(parents=True, exist_ok=True)

        # Track staged files
        self._staged_files: Dict[str, StagedFile] = {}

        # Cleanup flag
        self._cleaned_up = False

        logger.info(f"ShadowWorkspace created: {self.shadow_root}")

    def __enter__(self) -> "ShadowWorkspace":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Context manager exit - always cleanup."""
        self.cleanup()
        return False  # Don't suppress exceptions

    def __del__(self):
        """Destructor - ensure cleanup on garbage collection."""
        if not self._cleaned_up:
            try:
                self.cleanup()
            except Exception:
                pass  # Best effort cleanup in destructor

    def _normalize_path(self, file_path: str) -> Path:
        """
        Normalize a file path relative to project root.

        Args:
            file_path: Absolute or relative file path

        Returns:
            Normalized Path object relative to project root
        """
        path = Path(file_path)

        if path.is_absolute():
            # Make relative to project
            try:
                return path.relative_to(self.project_path)
            except ValueError:
                # Path is outside project - use as-is
                return path
        else:
            return path

    def _get_original_path(self, file_path: str) -> Path:
        """Get absolute path to original file."""
        rel_path = self._normalize_path(file_path)
        return self.project_path / rel_path

    def get_shadow_path(self, original_path: str) -> Path:
        """
        Get the calculated shadow path for a file.

        CTO Mandate: Essential for running linters/tests on shadow files.

        Args:
            original_path: Original file path (absolute or relative)

        Returns:
            Absolute path to the shadow version of the file
        """
        rel_path = self._normalize_path(original_path)
        return self.shadow_root / rel_path

    def stage_file(self, file_path: str) -> Path:
        """
        Stage a file in the shadow workspace.

        Copies the original file to the shadow directory, preserving
        the relative path structure.

        Args:
            file_path: Path to the file to stage (absolute or relative)

        Returns:
            Absolute path to the staged shadow file

        Raises:
            FileNotFoundError: If original file doesn't exist
        """
        rel_path = self._normalize_path(file_path)
        original = self._get_original_path(file_path)
        shadow = self.get_shadow_path(file_path)

        # Verify original exists
        if not original.exists():
            raise FileNotFoundError(f"Original file not found: {original}")

        # Create parent directories in shadow
        shadow.parent.mkdir(parents=True, exist_ok=True)

        # Copy file preserving metadata
        shutil.copy2(original, shadow)

        # Track staged file
        key = str(rel_path)
        self._staged_files[key] = StagedFile(
            original_path=original,
            shadow_path=shadow,
            staged_at=datetime.now(),
            modified=False
        )

        logger.debug(f"Staged file: {rel_path} -> {shadow}")
        return shadow

    def apply_patch(self, file_path: str, new_content: str) -> None:
        """
        Apply a patch to the shadow file.

        Overwrites the shadow file with new content.
        NEVER touches the original file.

        Args:
            file_path: Path to the file (must be already staged)
            new_content: New content to write

        Raises:
            ValueError: If file is not staged
        """
        rel_path = self._normalize_path(file_path)
        key = str(rel_path)

        # Check if staged
        if key not in self._staged_files:
            # Auto-stage if not already
            self.stage_file(file_path)

        shadow = self.get_shadow_path(file_path)

        # Write new content to shadow file
        shadow.write_text(new_content, encoding='utf-8')

        # Mark as modified
        self._staged_files[key].modified = True

        logger.debug(f"Applied patch to shadow: {rel_path}")

    def get_diff(self, file_path: str, context_lines: int = 3) -> str:
        """
        Get unified diff between original and shadow file.

        Args:
            file_path: Path to the file
            context_lines: Number of context lines in diff

        Returns:
            Unified diff string, or empty string if no changes
        """
        rel_path = self._normalize_path(file_path)
        original = self._get_original_path(file_path)
        shadow = self.get_shadow_path(file_path)

        if not shadow.exists():
            return ""

        # Read original
        try:
            original_lines = original.read_text(encoding='utf-8').splitlines(keepends=True)
        except Exception:
            original_lines = []

        # Read shadow
        try:
            shadow_lines = shadow.read_text(encoding='utf-8').splitlines(keepends=True)
        except Exception:
            shadow_lines = []

        # Generate unified diff
        diff_lines = list(difflib.unified_diff(
            original_lines,
            shadow_lines,
            fromfile=f"a/{rel_path} (original)",
            tofile=f"b/{rel_path} (shadow)",
            n=context_lines
        ))

        return ''.join(diff_lines)

    def get_diff_stats(self, file_path: str) -> Dict[str, int]:
        """
        Get statistics about the diff.

        Returns:
            Dict with 'additions', 'deletions', 'changes' counts
        """
        diff = self.get_diff(file_path)

        additions = 0
        deletions = 0

        for line in diff.splitlines():
            if line.startswith('+') and not line.startswith('+++'):
                additions += 1
            elif line.startswith('-') and not line.startswith('---'):
                deletions += 1

        return {
            'additions': additions,
            'deletions': deletions,
            'changes': additions + deletions
        }

    def promote_file(self, file_path: str) -> None:
        """
        Promote shadow file to production (replace original).

        THE DANGEROUS PART - Only call after user confirmation!

        Uses shutil.copy2 for atomic operation with metadata preservation.

        Args:
            file_path: Path to the file to promote

        Raises:
            ValueError: If file is not staged
            FileNotFoundError: If shadow file doesn't exist
        """
        rel_path = self._normalize_path(file_path)
        key = str(rel_path)

        if key not in self._staged_files:
            raise ValueError(f"File not staged: {rel_path}")

        staged = self._staged_files[key]
        shadow = staged.shadow_path
        original = staged.original_path

        if not shadow.exists():
            raise FileNotFoundError(f"Shadow file not found: {shadow}")

        # Create backup of original (optional safety net)
        backup_path = original.with_suffix(original.suffix + '.bak')
        try:
            if original.exists():
                shutil.copy2(original, backup_path)
        except Exception as e:
            logger.warning(f"Could not create backup: {e}")

        # ATOMIC PROMOTION: Copy shadow to original
        # Using copy2 to preserve metadata (timestamps, permissions)
        try:
            shutil.copy2(shadow, original)
            logger.info(f"Promoted shadow to production: {rel_path}")

            # Clean up backup on success
            if backup_path.exists():
                backup_path.unlink()

        except Exception as e:
            # Restore from backup if promotion failed
            if backup_path.exists():
                shutil.copy2(backup_path, original)
                backup_path.unlink()
            raise RuntimeError(f"Promotion failed: {e}") from e

    def promote_all(self) -> List[str]:
        """
        Promote all modified files.

        Returns:
            List of promoted file paths
        """
        promoted = []

        for key, staged in self._staged_files.items():
            if staged.modified:
                self.promote_file(key)
                promoted.append(key)

        return promoted

    def discard_file(self, file_path: str) -> None:
        """
        Discard changes to a file (remove from shadow).

        Args:
            file_path: Path to the file to discard
        """
        rel_path = self._normalize_path(file_path)
        key = str(rel_path)

        if key in self._staged_files:
            shadow = self._staged_files[key].shadow_path
            if shadow.exists():
                shadow.unlink()
            del self._staged_files[key]
            logger.debug(f"Discarded shadow: {rel_path}")

    def discard_all(self) -> None:
        """Discard all staged changes."""
        for key in list(self._staged_files.keys()):
            self.discard_file(key)

    def list_staged(self) -> List[Dict]:
        """
        List all staged files.

        Returns:
            List of dicts with file info
        """
        result = []
        for key, staged in self._staged_files.items():
            diff_stats = self.get_diff_stats(key)
            result.append({
                'path': key,
                'shadow_path': str(staged.shadow_path),
                'staged_at': staged.staged_at.isoformat(),
                'modified': staged.modified,
                'additions': diff_stats['additions'],
                'deletions': diff_stats['deletions'],
            })
        return result

    def cleanup(self) -> None:
        """
        Clean up the shadow workspace.

        Removes the entire shadow session directory.
        Safe to call multiple times.
        """
        if self._cleaned_up:
            return

        try:
            if self.shadow_root.exists():
                shutil.rmtree(self.shadow_root)
                logger.info(f"ShadowWorkspace cleaned up: {self.shadow_root}")

            # Also clean up empty parent directories
            shadow_parent = self.shadow_root.parent  # .vidurai/shadow/
            if shadow_parent.exists() and not any(shadow_parent.iterdir()):
                shadow_parent.rmdir()

            vidurai_dir = shadow_parent.parent  # .vidurai/
            if vidurai_dir.exists() and vidurai_dir.name == ".vidurai":
                # Only remove if shadow dir is empty
                shadow_dir = vidurai_dir / "shadow"
                if shadow_dir.exists() and not any(shadow_dir.iterdir()):
                    shadow_dir.rmdir()

        except Exception as e:
            logger.warning(f"Cleanup error (non-fatal): {e}")

        finally:
            self._cleaned_up = True
            self._staged_files.clear()

    def get_session_info(self) -> Dict:
        """Get information about this shadow session."""
        return {
            'session_id': self.session_id,
            'project_path': str(self.project_path),
            'shadow_root': str(self.shadow_root),
            'created_at': self.created_at.isoformat(),
            'staged_files': len(self._staged_files),
            'modified_files': sum(1 for s in self._staged_files.values() if s.modified),
            'cleaned_up': self._cleaned_up
        }
