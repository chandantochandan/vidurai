"""
State Projector - Zombie Killer

Maintains a "Current Truth" view of file states by:
- UPSERTing diagnostic events with errors into active_state
- DELETEing from active_state when diagnostics are clean
- Touching last_updated on file saves

This ensures the database reflects CURRENT reality, not zombie states
from past errors that have since been fixed.

Architecture:
- Async-first design (doesn't block hot log writes)
- Uses database module for state persistence
- Integrated with Stabilizer via event hooks

@version 2.1.0
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from vidurai.storage.database import MemoryDatabase

logger = logging.getLogger("vidurai.state_projector")


# =============================================================================
# TYPES
# =============================================================================

@dataclass
class StateUpdate:
    """Represents a state update operation"""
    file_path: str
    project_path: str
    has_errors: bool
    error_count: int = 0
    warning_count: int = 0
    error_summary: Optional[str] = None


@dataclass
class StateProjectorStats:
    """Statistics for monitoring"""
    events_processed: int = 0
    errors_upserted: int = 0
    errors_cleared: int = 0
    files_touched: int = 0
    async_errors: int = 0


# =============================================================================
# CONSTANTS
# =============================================================================

# IPC severity codes (from VS Code extension)
SEVERITY_ERROR = 0
SEVERITY_WARNING = 1
SEVERITY_INFO = 2
SEVERITY_HINT = 3


# =============================================================================
# STATE PROJECTOR
# =============================================================================

class StateProjector:
    """
    Projects events into current file state.

    Tracks which files currently have errors and removes them
    from active_state when they're fixed.

    Example:
        projector = StateProjector(database)

        # Error event arrives
        await projector.update_state({
            'type': 'diagnostic',
            'file': '/path/to/file.ts',
            'data': {'sev': 0, 'msg': 'Type error'}
        })
        # -> Row inserted/updated in active_state

        # Clean event arrives (file fixed)
        await projector.update_state({
            'type': 'diagnostic',
            'file': '/path/to/file.ts',
            'data': {'sev': 2, 'msg': ''}  # info level = clean
        })
        # -> Row deleted from active_state (zombie killed!)
    """

    def __init__(
        self,
        database: Optional['MemoryDatabase'] = None,
        project_path: Optional[str] = None
    ):
        """
        Initialize State Projector.

        Args:
            database: Database instance (will lazy-load if not provided)
            project_path: Default project path for operations
        """
        self._db = database
        self._project_path = project_path
        self.stats = StateProjectorStats()

        # Async queue for non-blocking updates
        self._update_queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None
        self._running = False

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def database(self) -> 'MemoryDatabase':
        """Get or lazy-load database"""
        if self._db is None:
            # Lazy import to avoid circular dependencies
            from vidurai.storage.database import MemoryDatabase
            self._db = MemoryDatabase()
        return self._db

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    async def start(self) -> None:
        """Start the async worker for processing state updates"""
        if self._running:
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._process_queue())
        logger.info("StateProjector started")

    async def stop(self) -> None:
        """Stop the async worker and flush pending updates"""
        if not self._running:
            return

        self._running = False

        # Process remaining items in queue
        while not self._update_queue.empty():
            try:
                update = self._update_queue.get_nowait()
                await self._apply_update(update)
            except asyncio.QueueEmpty:
                break

        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        logger.info("StateProjector stopped")

    async def update_state(self, event: Dict[str, Any]) -> None:
        """
        Process an event and update state accordingly.

        This is the main entry point called from Stabilizer.
        Updates are queued for async processing to avoid blocking.

        Args:
            event: Event dict with 'type', 'file', and 'data' fields
        """
        self.stats.events_processed += 1

        event_type = event.get('type', '')
        file_path = event.get('file') or event.get('data', {}).get('file')
        data = event.get('data', {})

        if not file_path:
            return  # Can't update state without file path

        # Determine project path
        project_path = self._project_path or self._infer_project_path(file_path)

        # Handle different event types
        if event_type == 'diagnostic':
            update = self._process_diagnostic(file_path, project_path, data)
            if update:
                await self._queue_update(update)

        elif event_type == 'file_edit':
            # Check if this is a save event
            change_type = data.get('change') or data.get('change_type')
            if change_type == 'save':
                # Touch the file state (update timestamp)
                await self._queue_touch(file_path)

    def update_state_sync(self, event: Dict[str, Any]) -> None:
        """
        Synchronous wrapper for update_state.

        Used when called from non-async context. Queues the update
        for later async processing.

        Args:
            event: Event dict
        """
        self.stats.events_processed += 1

        event_type = event.get('type', '')
        file_path = event.get('file') or event.get('data', {}).get('file')
        data = event.get('data', {})

        if not file_path:
            return

        project_path = self._project_path or self._infer_project_path(file_path)

        if event_type == 'diagnostic':
            update = self._process_diagnostic(file_path, project_path, data)
            if update:
                try:
                    self._update_queue.put_nowait(('update', update))
                except asyncio.QueueFull:
                    self.stats.async_errors += 1
                    logger.warning("State update queue full, dropping update")

        elif event_type == 'file_edit':
            change_type = data.get('change') or data.get('change_type')
            if change_type == 'save':
                try:
                    self._update_queue.put_nowait(('touch', file_path))
                except asyncio.QueueFull:
                    self.stats.async_errors += 1

    def get_stats(self) -> StateProjectorStats:
        """Get current statistics"""
        return StateProjectorStats(
            events_processed=self.stats.events_processed,
            errors_upserted=self.stats.errors_upserted,
            errors_cleared=self.stats.errors_cleared,
            files_touched=self.stats.files_touched,
            async_errors=self.stats.async_errors,
        )

    # -------------------------------------------------------------------------
    # State Query API
    # -------------------------------------------------------------------------

    def get_current_errors(self, project_path: Optional[str] = None) -> list:
        """
        Get files that currently have errors.

        Args:
            project_path: Optional project filter

        Returns:
            List of file state dicts
        """
        return self.database.get_files_with_errors(
            project_path or self._project_path
        )

    def get_file_state(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get current state for a specific file.

        Args:
            file_path: File to check

        Returns:
            State dict or None if file has no active issues
        """
        return self.database.get_file_state(file_path)

    def get_summary(self, project_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Get summary of current state.

        Args:
            project_path: Optional project filter

        Returns:
            Summary dict with counts
        """
        return self.database.get_active_state_summary(
            project_path or self._project_path
        )

    # -------------------------------------------------------------------------
    # Internal: Processing
    # -------------------------------------------------------------------------

    def _process_diagnostic(
        self,
        file_path: str,
        project_path: str,
        data: Dict[str, Any]
    ) -> Optional[StateUpdate]:
        """
        Process diagnostic event data into state update.

        Args:
            file_path: File with diagnostic
            project_path: Project root
            data: Diagnostic data from IPC

        Returns:
            StateUpdate to apply, or None if no update needed
        """
        # Extract severity from IPC format
        severity = data.get('sev')
        if severity is None:
            # Try alternative formats
            sev_str = data.get('severity', '')
            if sev_str == 'error':
                severity = SEVERITY_ERROR
            elif sev_str == 'warning':
                severity = SEVERITY_WARNING
            else:
                severity = SEVERITY_INFO

        message = data.get('msg') or data.get('message', '')

        # Determine if this is an error/warning or clean
        is_error = (severity == SEVERITY_ERROR)
        is_warning = (severity == SEVERITY_WARNING)

        if is_error or is_warning:
            # File has errors/warnings - UPSERT into active_state
            return StateUpdate(
                file_path=file_path,
                project_path=project_path,
                has_errors=is_error,
                error_count=1 if is_error else 0,
                warning_count=1 if is_warning else 0,
                error_summary=message[:200] if message else None
            )
        else:
            # File is clean (info/hint level) - signal to DELETE
            return StateUpdate(
                file_path=file_path,
                project_path=project_path,
                has_errors=False,
                error_count=0,
                warning_count=0,
                error_summary=None
            )

    async def _queue_update(self, update: StateUpdate) -> None:
        """Queue a state update for async processing"""
        try:
            await self._update_queue.put(('update', update))
        except Exception as e:
            self.stats.async_errors += 1
            logger.error(f"Failed to queue state update: {e}")

    async def _queue_touch(self, file_path: str) -> None:
        """Queue a file touch for async processing"""
        try:
            await self._update_queue.put(('touch', file_path))
        except Exception as e:
            self.stats.async_errors += 1
            logger.error(f"Failed to queue file touch: {e}")

    async def _process_queue(self) -> None:
        """Background worker to process state updates"""
        while self._running:
            try:
                # Wait for update with timeout
                try:
                    item = await asyncio.wait_for(
                        self._update_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                operation, payload = item

                if operation == 'update':
                    await self._apply_update(payload)
                elif operation == 'touch':
                    await self._apply_touch(payload)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.stats.async_errors += 1
                logger.error(f"Error processing state update: {e}")

    async def _apply_update(self, update: StateUpdate) -> None:
        """Apply a state update to the database"""
        try:
            if update.has_errors or update.warning_count > 0:
                # UPSERT - file has issues
                self.database.upsert_file_state(
                    file_path=update.file_path,
                    project_path=update.project_path,
                    has_errors=update.has_errors,
                    error_count=update.error_count,
                    warning_count=update.warning_count,
                    error_summary=update.error_summary
                )
                self.stats.errors_upserted += 1
                logger.debug(f"UPSERT state: {update.file_path} (errors={update.error_count})")
            else:
                # DELETE - file is clean (ZOMBIE KILLED!)
                deleted = self.database.clear_file_state(update.file_path)
                if deleted:
                    self.stats.errors_cleared += 1
                    logger.info(f"ZOMBIE KILLED: {update.file_path} is now clean")

        except Exception as e:
            self.stats.async_errors += 1
            logger.error(f"Error applying state update: {e}")

    async def _apply_touch(self, file_path: str) -> None:
        """Apply a file touch to the database"""
        try:
            updated = self.database.touch_file_state(file_path)
            if updated:
                self.stats.files_touched += 1
                logger.debug(f"Touched state: {file_path}")

        except Exception as e:
            self.stats.async_errors += 1
            logger.error(f"Error touching file state: {e}")

    def _infer_project_path(self, file_path: str) -> str:
        """
        Infer project path from file path.

        Simple heuristic: find parent directory with common markers.
        Falls back to parent directory if no markers found.
        """
        path = Path(file_path)
        markers = ['.git', 'package.json', 'pyproject.toml', 'Cargo.toml', '.vidurai']

        for parent in path.parents:
            for marker in markers:
                if (parent / marker).exists():
                    return str(parent)

        # Fall back to immediate parent
        return str(path.parent)


# =============================================================================
# SINGLETON
# =============================================================================

_default_projector: Optional[StateProjector] = None


def get_state_projector(
    database: Optional['MemoryDatabase'] = None,
    project_path: Optional[str] = None
) -> StateProjector:
    """Get or create the default state projector"""
    global _default_projector
    if _default_projector is None:
        _default_projector = StateProjector(database, project_path)
    return _default_projector


def reset_state_projector() -> None:
    """Reset the default state projector"""
    global _default_projector
    if _default_projector:
        asyncio.create_task(_default_projector.stop())
        _default_projector = None
