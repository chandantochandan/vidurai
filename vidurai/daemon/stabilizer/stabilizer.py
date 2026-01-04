"""
Stabilizer - Daemon-side Event Debouncing and Deduplication

Processes events received from VS Code extension, applying:
- Debouncing: Groups rapid events (e.g., typing) into single processing
- Deduplication: Prevents duplicate event processing within time window
- Rate Limiting: Caps events per second to prevent overload
- Smart Filtering: Ignores temp files, build artifacts, node_modules
- Batch Coalescing: Groups events for efficient storage

Architecture:
- Async-first design using asyncio
- Event callbacks for processed events
- Statistics tracking for monitoring

@version 2.1.0
"""

import re
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable, Awaitable, List, Set
from datetime import datetime

# v2.1: State Projection import (lazy to avoid circular deps)
_state_projector = None

def _get_state_projector():
    """Lazy load StateProjector to avoid import cycles"""
    global _state_projector
    if _state_projector is None:
        try:
            from intelligence.state_projector import get_state_projector
            _state_projector = get_state_projector()
        except ImportError:
            # Fall back to direct import path
            try:
                import sys
                from pathlib import Path
                daemon_path = Path(__file__).parent.parent
                if str(daemon_path) not in sys.path:
                    sys.path.insert(0, str(daemon_path))
                from intelligence.state_projector import get_state_projector
                _state_projector = get_state_projector()
            except ImportError as e:
                logging.getLogger("vidurai.stabilizer").warning(
                    f"StateProjector not available: {e}"
                )
                return None
    return _state_projector

logger = logging.getLogger("vidurai.stabilizer")

# =============================================================================
# TYPES
# =============================================================================

@dataclass
class StabilizedEvent:
    """A stabilized event ready for processing"""
    type: str
    file: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: float = field(default_factory=time.time)
    debounce_count: int = 1


@dataclass
class StabilizerOptions:
    """Stabilizer configuration"""
    debounce_delay: float = 0.5  # seconds
    dedupe_window: float = 1.0  # seconds
    max_events_per_second: int = 20
    enable_smart_filter: bool = True
    enable_batching: bool = True
    batch_window: float = 0.1  # seconds
    max_batch_size: int = 100
    debug: bool = False


@dataclass
class StabilizerStats:
    """Statistics for monitoring"""
    received: int = 0
    processed: int = 0
    debounced: int = 0
    deduplicated: int = 0
    rate_limited: int = 0
    filtered: int = 0
    batched: int = 0
    instant_commits: int = 0  # Save events that bypassed debounce


# =============================================================================
# CONSTANTS
# =============================================================================

# Patterns for files to ignore (smart filter)
IGNORE_PATTERNS: List[re.Pattern] = [
    # Build artifacts
    re.compile(r'[/\\]dist[/\\]'),
    re.compile(r'[/\\]build[/\\]'),
    re.compile(r'[/\\]out[/\\]'),
    re.compile(r'[/\\]\.next[/\\]'),
    re.compile(r'[/\\]\.nuxt[/\\]'),
    re.compile(r'[/\\]\.output[/\\]'),

    # Dependencies
    re.compile(r'[/\\]node_modules[/\\]'),
    re.compile(r'[/\\]vendor[/\\]'),
    re.compile(r'[/\\]\.venv[/\\]'),
    re.compile(r'[/\\]venv[/\\]'),
    re.compile(r'[/\\]__pycache__[/\\]'),
    re.compile(r'[/\\]\.pip[/\\]'),

    # Version control
    re.compile(r'[/\\]\.git[/\\]'),
    re.compile(r'[/\\]\.svn[/\\]'),
    re.compile(r'[/\\]\.hg[/\\]'),

    # IDE/Editor
    re.compile(r'[/\\]\.idea[/\\]'),
    re.compile(r'[/\\]\.vscode[/\\](?!settings\.json|launch\.json|tasks\.json)'),
    re.compile(r'[/\\]\.vs[/\\]'),

    # Temp files
    re.compile(r'\.tmp$', re.IGNORECASE),
    re.compile(r'\.temp$', re.IGNORECASE),
    re.compile(r'\.swp$', re.IGNORECASE),
    re.compile(r'\.swo$', re.IGNORECASE),
    re.compile(r'~$'),
    re.compile(r'\.bak$', re.IGNORECASE),

    # Lock files
    re.compile(r'package-lock\.json$'),
    re.compile(r'yarn\.lock$'),
    re.compile(r'pnpm-lock\.yaml$'),
    re.compile(r'Cargo\.lock$'),
    re.compile(r'poetry\.lock$'),
    re.compile(r'Gemfile\.lock$'),

    # Generated files
    re.compile(r'\.min\.js$'),
    re.compile(r'\.min\.css$'),
    re.compile(r'\.map$'),
    re.compile(r'\.d\.ts$'),

    # Binary/Media
    re.compile(r'\.(png|jpg|jpeg|gif|ico|svg|webp)$', re.IGNORECASE),
    re.compile(r'\.(mp3|mp4|wav|avi|mov)$', re.IGNORECASE),
    re.compile(r'\.(zip|tar|gz|rar|7z)$', re.IGNORECASE),
    re.compile(r'\.(pdf|doc|docx|xls|xlsx)$', re.IGNORECASE),

    # Log files
    re.compile(r'\.log$', re.IGNORECASE),
    re.compile(r'[/\\]logs[/\\]'),
]

# Event types that should be debounced
DEBOUNCE_TYPES: Set[str] = {
    'file_edit',
    'selection',
    'diagnostic',
}

# Event types that should be deduplicated
DEDUPE_TYPES: Set[str] = {
    'terminal',
    'focus',
    'file_create',
    'file_delete',
}

# Change types that trigger instant commit (bypass debounce)
# When user explicitly saves (Ctrl+S), we commit immediately
INSTANT_COMMIT_CHANGES: Set[str] = {
    'save',
}


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def should_ignore_file(file_path: str) -> bool:
    """
    Check if a file should be ignored based on patterns.

    Args:
        file_path: Path to check

    Returns:
        True if file should be ignored
    """
    if not file_path:
        return False

    # Normalize path separators
    normalized = file_path.replace('\\', '/')

    for pattern in IGNORE_PATTERNS:
        if pattern.search(normalized) or pattern.search(file_path):
            return True

    return False


# =============================================================================
# STABILIZER CLASS
# =============================================================================

class Stabilizer:
    """
    Daemon-side event stabilizer.

    Processes incoming events with debouncing, deduplication,
    and rate limiting before passing to storage/processing.

    Example:
        stabilizer = Stabilizer()

        async def handle_event(event):
            print(f"Processing: {event.type}")

        stabilizer.on_event(handle_event)
        await stabilizer.start()

        # Submit events
        await stabilizer.submit({'type': 'file_edit', 'file': '/path/to/file.ts'})
    """

    def __init__(self, options: Optional[StabilizerOptions] = None):
        self.options = options or StabilizerOptions()
        self.stats = StabilizerStats()

        # Debounce state
        self._debounce_map: Dict[str, Dict[str, Any]] = {}
        self._debounce_tasks: Dict[str, asyncio.Task] = {}

        # Dedupe state
        self._dedupe_cache: Dict[str, float] = {}

        # Rate limiting state
        self._rate_bucket_count: int = 0
        self._rate_bucket_reset: float = time.time() + 1.0

        # Batching state
        self._batch_queue: List[StabilizedEvent] = []
        self._batch_task: Optional[asyncio.Task] = None

        # Callbacks
        self._event_handler: Optional[Callable[[StabilizedEvent], Awaitable[None]]] = None
        self._batch_handler: Optional[Callable[[List[StabilizedEvent]], Awaitable[None]]] = None

        # Running state
        self._running = False
        self._cleanup_task: Optional[asyncio.Task] = None

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def on_event(self, handler: Callable[[StabilizedEvent], Awaitable[None]]) -> None:
        """Register handler for individual events"""
        self._event_handler = handler

    def on_batch(self, handler: Callable[[List[StabilizedEvent]], Awaitable[None]]) -> None:
        """Register handler for event batches"""
        self._batch_handler = handler

    async def start(self) -> None:
        """Start the stabilizer background tasks"""
        if self._running:
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        # v2.1: Start StateProjector for Current Truth maintenance
        try:
            projector = _get_state_projector()
            if projector:
                await projector.start()
                self._log("StateProjector started")
        except Exception as e:
            logger.warning(f"Failed to start StateProjector: {e}")

        self._log("Stabilizer started")

    async def stop(self) -> None:
        """Stop the stabilizer and flush pending events"""
        if not self._running:
            return

        self._running = False

        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Cancel debounce tasks
        for task in self._debounce_tasks.values():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Flush remaining events
        await self.flush()

        # v2.1: Stop StateProjector
        try:
            projector = _get_state_projector()
            if projector:
                await projector.stop()
                self._log("StateProjector stopped")
        except Exception as e:
            logger.warning(f"Error stopping StateProjector: {e}")

        self._log("Stabilizer stopped")

    async def submit(self, event_data: Dict[str, Any]) -> bool:
        """
        Submit an event for processing.

        Args:
            event_data: Event dictionary with 'type', optional 'file' and 'data'

        Returns:
            True if event was accepted, False if filtered/rate-limited
        """
        self.stats.received += 1

        event_type = event_data.get('type', '')
        file_path = event_data.get('data', {}).get('file') or event_data.get('file')
        data = event_data.get('data', {})

        # Step 1: Smart file filtering
        if self.options.enable_smart_filter and file_path:
            if should_ignore_file(file_path):
                self.stats.filtered += 1
                self._log(f"Filtered: {file_path}")
                return False

        # Step 2: Rate limiting
        if not self._check_rate_limit():
            self.stats.rate_limited += 1
            self._log(f"Rate limited: {event_type}")
            return False

        # Step 3: Check for instant commit (save events bypass debounce)
        # When user explicitly saves (Ctrl+S), commit immediately
        change_type = data.get('change') or data.get('change_type')
        if change_type in INSTANT_COMMIT_CHANGES:
            self.stats.instant_commits += 1
            self._log(f"Instant commit (save): {event_type} {file_path or ''}")

            # Flush any pending debounced events for this file first
            if file_path:
                debounce_key = f"{event_type}:{file_path}"
                if debounce_key in self._debounce_map:
                    # Cancel the pending debounce timer
                    if debounce_key in self._debounce_tasks:
                        self._debounce_tasks[debounce_key].cancel()
                        self._debounce_tasks.pop(debounce_key, None)
                    # Remove from debounce map (save supersedes pending edits)
                    self._debounce_map.pop(debounce_key, None)

            # Emit immediately - no debounce delay
            event = StabilizedEvent(
                type=event_type,
                file=file_path,
                data=data,
                timestamp=time.time()
            )
            await self._emit_event(event)
            return True

        # Step 4: Debouncing (for non-save events)
        if event_type in DEBOUNCE_TYPES:
            await self._debounce(event_type, file_path, data)
            return True

        # Step 5: Deduplication
        if event_type in DEDUPE_TYPES:
            dedupe_key = self._get_dedupe_key(event_type, file_path, data)
            if self._is_duplicate(dedupe_key):
                self.stats.deduplicated += 1
                self._log(f"Deduplicated: {event_type}")
                return False
            self._mark_seen(dedupe_key)

        # Step 5: Batching or immediate processing
        event = StabilizedEvent(
            type=event_type,
            file=file_path,
            data=data,
            timestamp=time.time()
        )

        if self.options.enable_batching:
            await self._add_to_batch(event)
        else:
            await self._emit_event(event)

        return True

    async def flush(self) -> None:
        """Flush all pending events"""
        # Flush debounced events
        for key in list(self._debounce_map.keys()):
            entry = self._debounce_map.pop(key, None)
            if entry:
                event = StabilizedEvent(
                    type=entry['type'],
                    file=entry['file'],
                    data=entry['data'],
                    timestamp=entry['timestamp'],
                    debounce_count=entry['count']
                )
                await self._emit_event(event)

        # Cancel pending debounce tasks
        for task in self._debounce_tasks.values():
            task.cancel()
        self._debounce_tasks.clear()

        # Flush batch queue
        await self._flush_batch()

    def get_stats(self) -> StabilizerStats:
        """Get current statistics"""
        return StabilizerStats(
            received=self.stats.received,
            processed=self.stats.processed,
            debounced=self.stats.debounced,
            deduplicated=self.stats.deduplicated,
            rate_limited=self.stats.rate_limited,
            filtered=self.stats.filtered,
            batched=self.stats.batched,
            instant_commits=self.stats.instant_commits,
        )

    def reset_stats(self) -> None:
        """Reset statistics"""
        self.stats = StabilizerStats()

    # -------------------------------------------------------------------------
    # Rate Limiting
    # -------------------------------------------------------------------------

    def _check_rate_limit(self) -> bool:
        """Check if event passes rate limit"""
        now = time.time()

        # Reset bucket if window expired
        if now >= self._rate_bucket_reset:
            self._rate_bucket_count = 0
            self._rate_bucket_reset = now + 1.0

        # Check limit
        if self._rate_bucket_count >= self.options.max_events_per_second:
            return False

        self._rate_bucket_count += 1
        return True

    # -------------------------------------------------------------------------
    # Deduplication
    # -------------------------------------------------------------------------

    def _get_dedupe_key(self, event_type: str, file_path: Optional[str], data: Dict) -> str:
        """Generate deduplication key"""
        parts = [event_type]
        if file_path:
            parts.append(file_path)
        if 'change' in data:
            parts.append(str(data['change']))
        if 'command' in data:
            parts.append(str(data['command']))
        return ':'.join(parts)

    def _is_duplicate(self, key: str) -> bool:
        """Check if event is duplicate"""
        last_seen = self._dedupe_cache.get(key)
        if last_seen is None:
            return False
        elapsed = time.time() - last_seen
        return elapsed < self.options.dedupe_window

    def _mark_seen(self, key: str) -> None:
        """Mark event as seen"""
        self._dedupe_cache[key] = time.time()

    # -------------------------------------------------------------------------
    # Debouncing
    # -------------------------------------------------------------------------

    async def _debounce(self, event_type: str, file_path: Optional[str], data: Dict) -> None:
        """Debounce an event"""
        key = f"{event_type}:{file_path or 'global'}"

        # Update or create entry
        if key in self._debounce_map:
            entry = self._debounce_map[key]
            entry['data'] = data
            entry['count'] += 1
            entry['timestamp'] = time.time()
            self.stats.debounced += 1
            self._log(f"Debounced ({entry['count']}x): {event_type} {file_path or ''}")

            # Cancel existing task
            if key in self._debounce_tasks:
                self._debounce_tasks[key].cancel()
        else:
            self._debounce_map[key] = {
                'type': event_type,
                'file': file_path,
                'data': data,
                'count': 1,
                'timestamp': time.time(),
            }

        # Create new debounce task
        self._debounce_tasks[key] = asyncio.create_task(
            self._debounce_timer(key)
        )

    async def _debounce_timer(self, key: str) -> None:
        """Timer task for debounce"""
        try:
            await asyncio.sleep(self.options.debounce_delay)

            entry = self._debounce_map.pop(key, None)
            self._debounce_tasks.pop(key, None)

            if entry:
                event = StabilizedEvent(
                    type=entry['type'],
                    file=entry['file'],
                    data=entry['data'],
                    timestamp=entry['timestamp'],
                    debounce_count=entry['count']
                )

                if self.options.enable_batching:
                    await self._add_to_batch(event)
                else:
                    await self._emit_event(event)

        except asyncio.CancelledError:
            pass

    # -------------------------------------------------------------------------
    # Batching
    # -------------------------------------------------------------------------

    async def _add_to_batch(self, event: StabilizedEvent) -> None:
        """Add event to batch queue"""
        self._batch_queue.append(event)
        self.stats.batched += 1

        # Flush if batch is full
        if len(self._batch_queue) >= self.options.max_batch_size:
            await self._flush_batch()
            return

        # Start batch timer if not running
        if self._batch_task is None or self._batch_task.done():
            self._batch_task = asyncio.create_task(self._batch_timer())

    async def _batch_timer(self) -> None:
        """Timer task for batch flushing"""
        try:
            await asyncio.sleep(self.options.batch_window)
            await self._flush_batch()
        except asyncio.CancelledError:
            pass

    async def _flush_batch(self) -> None:
        """Flush the batch queue"""
        if self._batch_task and not self._batch_task.done():
            self._batch_task.cancel()
            try:
                await self._batch_task
            except asyncio.CancelledError:
                pass
            self._batch_task = None

        if not self._batch_queue:
            return

        # Emit single event directly, multiple as batch
        if len(self._batch_queue) == 1:
            await self._emit_event(self._batch_queue[0])
        elif self._batch_handler:
            self._log(f"Emitting batch of {len(self._batch_queue)} events")
            await self._batch_handler(list(self._batch_queue))
            self.stats.processed += len(self._batch_queue)
        else:
            # No batch handler, emit individually
            for event in self._batch_queue:
                await self._emit_event(event)

        self._batch_queue.clear()

    # -------------------------------------------------------------------------
    # Event Emission
    # -------------------------------------------------------------------------

    async def _emit_event(self, event: StabilizedEvent) -> None:
        """Emit a processed event"""
        self.stats.processed += 1
        self._log(f"Emitting: {event.type} {event.file or ''}")

        if self._event_handler:
            try:
                await self._event_handler(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")

        # v2.1: Update State Projection (async, non-blocking)
        # This maintains "Current Truth" by tracking/removing errors
        try:
            projector = _get_state_projector()
            if projector:
                # Build event dict for projector
                event_dict = {
                    'type': event.type,
                    'file': event.file,
                    'data': event.data or {}
                }
                # Fire-and-forget: don't block the hot log write
                asyncio.create_task(projector.update_state(event_dict))
        except Exception as e:
            # State projection should never block main flow
            logger.debug(f"State projection error (non-fatal): {e}")

        # v2.2: Persist to long-term memory (Memory Bridge)
        # Stores significant events to SQLite memories table
        try:
            await self._persist_to_memory(event)
        except Exception as e:
            # Memory persistence should never block main flow
            logger.debug(f"Memory persistence error (non-fatal): {e}")

    # -------------------------------------------------------------------------
    # Memory Persistence (v2.2)
    # -------------------------------------------------------------------------

    async def _persist_to_memory(self, event: StabilizedEvent) -> None:
        """
        Persist significant events to long-term SQLite memory.

        Only persists:
        - Diagnostic events (errors/warnings)
        - Terminal errors (non-zero exit codes)
        - File saves (explicit user action)

        Skips:
        - File edits (too noisy, handled by state projection)
        - Transient events
        """
        # Only persist significant event types
        significant_types = {'diagnostic', 'terminal', 'file_edit'}
        if event.type not in significant_types:
            return

        # For file_edit, only persist saves (not every keystroke)
        if event.type == 'file_edit':
            change_type = (event.data or {}).get('change', '')
            if change_type != 'save':
                return

        # For terminal, only persist errors
        if event.type == 'terminal':
            exit_code = (event.data or {}).get('code', 0)
            if exit_code == 0:
                return

        try:
            # Lazy import to avoid circular dependencies
            from vidurai.storage.database import MemoryDatabase

            db = MemoryDatabase()

            # Build memory content based on event type
            if event.type == 'diagnostic':
                verbatim = f"[{event.data.get('sev', 'error')}] {event.file}: {event.data.get('msg', '')}"
                gist = event.data.get('msg', '')[:200]
                salience = 'HIGH' if event.data.get('sev', 0) == 0 else 'MEDIUM'
                event_type = 'diagnostic'

            elif event.type == 'terminal':
                cmd = event.data.get('cmd', '')
                err = event.data.get('err', '')
                verbatim = f"Command failed: {cmd}\nError: {err}"
                gist = f"'{cmd}' failed with exit code {event.data.get('code', 1)}"
                salience = 'HIGH'
                event_type = 'terminal_error'

            elif event.type == 'file_edit':
                verbatim = f"Saved: {event.file}"
                gist = event.data.get('gist', f'Saved {event.file}')[:200]
                salience = 'LOW'
                event_type = 'file_save'

            else:
                return  # Unknown type, skip

            # Store to database
            db.store_memory(
                verbatim=verbatim,
                gist=gist,
                salience=salience,
                event_type=event_type,
                file_path=event.file,
                project_path=event.data.get('project', '')
            )

            self._log(f"Persisted to memory: {event_type} ({salience})")

        except ImportError:
            logger.debug("MemoryDatabase not available - skipping persistence")
        except Exception as e:
            logger.debug(f"Memory persistence failed: {e}")

    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------

    async def _cleanup_loop(self) -> None:
        """Background task to clean up stale cache entries"""
        while self._running:
            try:
                await asyncio.sleep(60)  # Cleanup every minute
                self._cleanup_dedupe_cache()
            except asyncio.CancelledError:
                break

    def _cleanup_dedupe_cache(self) -> None:
        """Remove expired entries from dedupe cache"""
        now = time.time()
        cutoff = now - self.options.dedupe_window

        expired = [k for k, v in self._dedupe_cache.items() if v < cutoff]
        for key in expired:
            del self._dedupe_cache[key]

        if expired:
            self._log(f"Cleaned up {len(expired)} dedupe entries")

    # -------------------------------------------------------------------------
    # Utilities
    # -------------------------------------------------------------------------

    def _log(self, message: str) -> None:
        """Debug logging"""
        if self.options.debug:
            logger.debug(f"[Stabilizer] {message}")


# =============================================================================
# SINGLETON
# =============================================================================

_default_stabilizer: Optional[Stabilizer] = None


def get_stabilizer(options: Optional[StabilizerOptions] = None) -> Stabilizer:
    """Get or create the default stabilizer"""
    global _default_stabilizer
    if _default_stabilizer is None:
        _default_stabilizer = Stabilizer(options)
    return _default_stabilizer


def reset_stabilizer() -> None:
    """Reset the default stabilizer"""
    global _default_stabilizer
    if _default_stabilizer:
        asyncio.create_task(_default_stabilizer.stop())
        _default_stabilizer = None
