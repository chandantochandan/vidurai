"""
Archiver - Storage Lifecycle Management

Implements tiered storage with automatic archival:
- Hot Storage: JSONL files for recent events (fast writes)
- Cold Storage: Parquet files for archived data (efficient reads)
- Retention: Configurable policies for data lifecycle

Architecture:
- Events are first written to hot storage (JSONL)
- When hot files exceed threshold, they're archived to Parquet
- Parquet files are partitioned by date for efficient querying
- Old data is pruned based on retention policy

@version 2.1.0
"""

import json
import gzip
import shutil
import asyncio
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Iterator, Callable
from collections import defaultdict

logger = logging.getLogger("vidurai.archiver")

# Try to import pyarrow, gracefully degrade if not available
try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    PYARROW_AVAILABLE = True
except ImportError:
    PYARROW_AVAILABLE = False
    logger.warning("pyarrow not available - Parquet archival disabled")


# =============================================================================
# TYPES
# =============================================================================

@dataclass
class EventRecord:
    """A single event record for storage"""
    timestamp: float
    event_type: str
    file: Optional[str] = None
    project: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'timestamp': self.timestamp,
            'event_type': self.event_type,
            'file': self.file,
            'project': self.project,
            'data': self.data,
            'session_id': self.session_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EventRecord':
        """Create from dictionary"""
        return cls(
            timestamp=data.get('timestamp', 0),
            event_type=data.get('event_type', ''),
            file=data.get('file'),
            project=data.get('project'),
            data=data.get('data'),
            session_id=data.get('session_id'),
        )


@dataclass
class ArchiverOptions:
    """Archiver configuration"""
    # Storage paths
    base_dir: Optional[Path] = None  # Default: ~/.vidurai/archive

    # Hot storage settings
    hot_max_size_mb: float = 10.0  # Max size before rotation
    hot_max_age_hours: int = 24  # Max age before archival

    # Cold storage settings
    cold_compression: str = 'snappy'  # Parquet compression
    cold_partition_by: str = 'day'  # day, week, month

    # Retention settings
    hot_retention_days: int = 7
    cold_retention_days: int = 90

    # Background task settings
    archive_interval_minutes: int = 60
    cleanup_interval_hours: int = 24

    # Debug
    debug: bool = False


@dataclass
class StorageStats:
    """Storage statistics"""
    hot_files: int = 0
    hot_size_bytes: int = 0
    hot_events: int = 0
    cold_files: int = 0
    cold_size_bytes: int = 0
    cold_events: int = 0
    last_archive: Optional[datetime] = None
    last_cleanup: Optional[datetime] = None


# =============================================================================
# ARCHIVER CLASS
# =============================================================================

class Archiver:
    """
    Storage lifecycle manager.

    Handles tiered storage with automatic archival from JSONL to Parquet.

    Example:
        archiver = Archiver()
        await archiver.start()

        # Write events
        await archiver.write(EventRecord(
            timestamp=time.time(),
            event_type='file_edit',
            file='/path/to/file.ts',
            project='my-project'
        ))

        # Query events
        events = await archiver.query(
            start_time=time.time() - 3600,
            event_types=['file_edit']
        )

        await archiver.stop()
    """

    def __init__(self, options: Optional[ArchiverOptions] = None):
        self.options = options or ArchiverOptions()

        # Set up storage directories
        if self.options.base_dir is None:
            self.base_dir = Path.home() / '.vidurai' / 'archive'
        else:
            self.base_dir = self.options.base_dir

        self.hot_dir = self.base_dir / 'hot'
        self.cold_dir = self.base_dir / 'cold'

        # Create directories
        self.hot_dir.mkdir(parents=True, exist_ok=True)
        self.cold_dir.mkdir(parents=True, exist_ok=True)

        # Current hot file
        self._current_hot_file: Optional[Path] = None
        self._current_hot_handle = None
        self._hot_event_count = 0

        # Statistics
        self.stats = StorageStats()

        # Background tasks
        self._running = False
        self._archive_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None

        # Lock for thread safety
        self._write_lock = asyncio.Lock()

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    async def start(self) -> None:
        """Start the archiver background tasks"""
        if self._running:
            return

        self._running = True

        # Open current hot file
        self._open_hot_file()

        # Start background tasks
        self._archive_task = asyncio.create_task(self._archive_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        # Calculate initial stats
        await self._update_stats()

        self._log(f"Archiver started at {self.base_dir}")

    async def stop(self) -> None:
        """Stop the archiver and flush pending writes"""
        if not self._running:
            return

        self._running = False

        # Cancel background tasks
        for task in [self._archive_task, self._cleanup_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Close hot file
        self._close_hot_file()

        self._log("Archiver stopped")

    # -------------------------------------------------------------------------
    # Writing
    # -------------------------------------------------------------------------

    async def write(self, event: EventRecord) -> bool:
        """
        Write an event to hot storage.

        Args:
            event: Event record to write

        Returns:
            True if write succeeded
        """
        async with self._write_lock:
            try:
                # Rotate if needed
                if self._should_rotate_hot():
                    self._rotate_hot_file()

                # Ensure file is open
                if self._current_hot_handle is None:
                    self._open_hot_file()

                # Write event as JSONL
                line = json.dumps(event.to_dict()) + '\n'
                self._current_hot_handle.write(line)
                self._current_hot_handle.flush()

                self._hot_event_count += 1
                self.stats.hot_events += 1

                return True

            except Exception as e:
                logger.error(f"Write error: {e}")
                return False

    async def write_batch(self, events: List[EventRecord]) -> int:
        """
        Write multiple events to hot storage.

        Args:
            events: List of event records

        Returns:
            Number of events written
        """
        written = 0
        for event in events:
            if await self.write(event):
                written += 1
        return written

    # -------------------------------------------------------------------------
    # Hot File Management
    # -------------------------------------------------------------------------

    def _open_hot_file(self) -> None:
        """Open a new hot file for writing"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self._current_hot_file = self.hot_dir / f'events_{timestamp}.jsonl'
        self._current_hot_handle = open(self._current_hot_file, 'a', encoding='utf-8')
        self._hot_event_count = 0
        self._log(f"Opened hot file: {self._current_hot_file.name}")

    def _close_hot_file(self) -> None:
        """Close the current hot file"""
        if self._current_hot_handle:
            self._current_hot_handle.close()
            self._current_hot_handle = None

    def _should_rotate_hot(self) -> bool:
        """Check if hot file should be rotated"""
        if self._current_hot_file is None:
            return True

        if not self._current_hot_file.exists():
            return True

        # Flush to ensure size is accurate
        if self._current_hot_handle:
            self._current_hot_handle.flush()

        # Check size
        size_mb = self._current_hot_file.stat().st_size / (1024 * 1024)
        if size_mb >= self.options.hot_max_size_mb:
            return True

        return False

    def _rotate_hot_file(self) -> None:
        """Rotate to a new hot file"""
        self._close_hot_file()
        self._open_hot_file()
        self._log("Rotated hot file")

    # -------------------------------------------------------------------------
    # Archival (Hot -> Cold)
    # -------------------------------------------------------------------------

    async def archive_hot_files(self) -> int:
        """
        Archive eligible hot files to Parquet.

        Returns:
            Number of files archived
        """
        if not PYARROW_AVAILABLE:
            self._log("Skipping archive - pyarrow not available")
            return 0

        archived = 0
        cutoff_time = datetime.now() - timedelta(hours=self.options.hot_max_age_hours)

        for hot_file in self.hot_dir.glob('events_*.jsonl'):
            # Skip current file
            if hot_file == self._current_hot_file:
                continue

            # Check age
            mtime = datetime.fromtimestamp(hot_file.stat().st_mtime)
            if mtime > cutoff_time:
                continue

            try:
                if await self._archive_file(hot_file):
                    archived += 1
            except Exception as e:
                logger.error(f"Failed to archive {hot_file}: {e}")

        if archived > 0:
            self.stats.last_archive = datetime.now()
            self._log(f"Archived {archived} files")

        return archived

    async def _archive_file(self, hot_file: Path) -> bool:
        """Archive a single hot file to Parquet"""
        # Read events from JSONL
        events = []
        with open(hot_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        events.append(data)
                    except json.JSONDecodeError:
                        continue

        if not events:
            # Empty file, just delete
            hot_file.unlink()
            return True

        # Convert to Parquet
        try:
            # Create Arrow table
            table = self._events_to_arrow_table(events)

            # Determine partition path
            first_ts = events[0].get('timestamp', 0)
            partition_path = self._get_partition_path(first_ts)
            parquet_file = partition_path / f'{hot_file.stem}.parquet'

            # Ensure partition directory exists
            partition_path.mkdir(parents=True, exist_ok=True)

            # Write Parquet file
            pq.write_table(
                table,
                parquet_file,
                compression=self.options.cold_compression
            )

            # Delete hot file
            hot_file.unlink()

            self._log(f"Archived {len(events)} events to {parquet_file.name}")
            return True

        except Exception as e:
            logger.error(f"Parquet conversion failed: {e}")
            return False

    def _events_to_arrow_table(self, events: List[Dict]) -> 'pa.Table':
        """Convert event dictionaries to Arrow table"""
        # Extract columns
        timestamps = []
        event_types = []
        files = []
        projects = []
        session_ids = []
        data_json = []

        for event in events:
            timestamps.append(event.get('timestamp', 0))
            event_types.append(event.get('event_type', ''))
            files.append(event.get('file'))
            projects.append(event.get('project'))
            session_ids.append(event.get('session_id'))
            # Store data as JSON string for flexibility
            data = event.get('data')
            data_json.append(json.dumps(data) if data else None)

        # Create Arrow arrays
        schema = pa.schema([
            ('timestamp', pa.float64()),
            ('event_type', pa.string()),
            ('file', pa.string()),
            ('project', pa.string()),
            ('session_id', pa.string()),
            ('data', pa.string()),  # JSON-encoded
        ])

        arrays = [
            pa.array(timestamps, type=pa.float64()),
            pa.array(event_types, type=pa.string()),
            pa.array(files, type=pa.string()),
            pa.array(projects, type=pa.string()),
            pa.array(session_ids, type=pa.string()),
            pa.array(data_json, type=pa.string()),
        ]

        return pa.Table.from_arrays(arrays, schema=schema)

    def _get_partition_path(self, timestamp: float) -> Path:
        """Get partition path for a timestamp"""
        dt = datetime.fromtimestamp(timestamp)

        if self.options.cold_partition_by == 'day':
            partition = dt.strftime('%Y/%m/%d')
        elif self.options.cold_partition_by == 'week':
            partition = dt.strftime('%Y/W%W')
        elif self.options.cold_partition_by == 'month':
            partition = dt.strftime('%Y/%m')
        else:
            partition = dt.strftime('%Y/%m/%d')

        return self.cold_dir / partition

    # -------------------------------------------------------------------------
    # Cleanup / Retention
    # -------------------------------------------------------------------------

    async def cleanup_old_files(self) -> Dict[str, int]:
        """
        Remove files older than retention period.

        Returns:
            Dict with 'hot' and 'cold' counts of removed files
        """
        removed = {'hot': 0, 'cold': 0}

        # Cleanup hot files
        hot_cutoff = datetime.now() - timedelta(days=self.options.hot_retention_days)
        for hot_file in self.hot_dir.glob('events_*.jsonl'):
            if hot_file == self._current_hot_file:
                continue
            mtime = datetime.fromtimestamp(hot_file.stat().st_mtime)
            if mtime < hot_cutoff:
                try:
                    hot_file.unlink()
                    removed['hot'] += 1
                except Exception as e:
                    logger.error(f"Failed to remove {hot_file}: {e}")

        # Cleanup cold files
        cold_cutoff = datetime.now() - timedelta(days=self.options.cold_retention_days)
        for parquet_file in self.cold_dir.rglob('*.parquet'):
            mtime = datetime.fromtimestamp(parquet_file.stat().st_mtime)
            if mtime < cold_cutoff:
                try:
                    parquet_file.unlink()
                    removed['cold'] += 1
                except Exception as e:
                    logger.error(f"Failed to remove {parquet_file}: {e}")

        # Remove empty partition directories
        for dir_path in sorted(self.cold_dir.rglob('*'), reverse=True):
            if dir_path.is_dir() and not any(dir_path.iterdir()):
                try:
                    dir_path.rmdir()
                except Exception:
                    pass

        if removed['hot'] > 0 or removed['cold'] > 0:
            self.stats.last_cleanup = datetime.now()
            self._log(f"Cleaned up {removed['hot']} hot, {removed['cold']} cold files")

        return removed

    # -------------------------------------------------------------------------
    # Querying
    # -------------------------------------------------------------------------

    async def query(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        event_types: Optional[List[str]] = None,
        file_pattern: Optional[str] = None,
        project: Optional[str] = None,
        limit: int = 1000,
    ) -> List[EventRecord]:
        """
        Query events from storage.

        Args:
            start_time: Start timestamp (inclusive)
            end_time: End timestamp (exclusive)
            event_types: Filter by event types
            file_pattern: Filter by file path (substring match)
            project: Filter by project
            limit: Maximum results

        Returns:
            List of matching EventRecords
        """
        results = []

        # Query hot files
        hot_results = await self._query_hot(
            start_time, end_time, event_types, file_pattern, project, limit
        )
        results.extend(hot_results)

        if len(results) >= limit:
            return results[:limit]

        # Query cold files if needed
        remaining = limit - len(results)
        cold_results = await self._query_cold(
            start_time, end_time, event_types, file_pattern, project, remaining
        )
        results.extend(cold_results)

        # Sort by timestamp
        results.sort(key=lambda e: e.timestamp, reverse=True)

        return results[:limit]

    async def _query_hot(
        self,
        start_time: Optional[float],
        end_time: Optional[float],
        event_types: Optional[List[str]],
        file_pattern: Optional[str],
        project: Optional[str],
        limit: int,
    ) -> List[EventRecord]:
        """Query hot storage (JSONL files)"""
        results = []

        for hot_file in sorted(self.hot_dir.glob('events_*.jsonl'), reverse=True):
            try:
                with open(hot_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue

                        try:
                            data = json.loads(line)
                            record = EventRecord.from_dict(data)

                            # Apply filters
                            if not self._matches_filter(
                                record, start_time, end_time,
                                event_types, file_pattern, project
                            ):
                                continue

                            results.append(record)

                            if len(results) >= limit:
                                return results

                        except json.JSONDecodeError:
                            continue

            except Exception as e:
                logger.error(f"Error reading {hot_file}: {e}")

        return results

    async def _query_cold(
        self,
        start_time: Optional[float],
        end_time: Optional[float],
        event_types: Optional[List[str]],
        file_pattern: Optional[str],
        project: Optional[str],
        limit: int,
    ) -> List[EventRecord]:
        """Query cold storage (Parquet files)"""
        if not PYARROW_AVAILABLE:
            return []

        results = []

        # Find relevant partition directories based on time range
        parquet_files = list(self.cold_dir.rglob('*.parquet'))
        parquet_files.sort(reverse=True)  # Newest first

        for parquet_file in parquet_files:
            try:
                # Read Parquet file
                table = pq.read_table(parquet_file)

                # Convert to Python records
                for i in range(table.num_rows):
                    data_str = table['data'][i].as_py()
                    data = json.loads(data_str) if data_str else None

                    record = EventRecord(
                        timestamp=table['timestamp'][i].as_py(),
                        event_type=table['event_type'][i].as_py(),
                        file=table['file'][i].as_py(),
                        project=table['project'][i].as_py(),
                        session_id=table['session_id'][i].as_py(),
                        data=data,
                    )

                    # Apply filters
                    if not self._matches_filter(
                        record, start_time, end_time,
                        event_types, file_pattern, project
                    ):
                        continue

                    results.append(record)

                    if len(results) >= limit:
                        return results

            except Exception as e:
                logger.error(f"Error reading {parquet_file}: {e}")

        return results

    def _matches_filter(
        self,
        record: EventRecord,
        start_time: Optional[float],
        end_time: Optional[float],
        event_types: Optional[List[str]],
        file_pattern: Optional[str],
        project: Optional[str],
    ) -> bool:
        """Check if record matches filter criteria"""
        if start_time and record.timestamp < start_time:
            return False

        if end_time and record.timestamp >= end_time:
            return False

        if event_types and record.event_type not in event_types:
            return False

        if file_pattern and record.file:
            if file_pattern.lower() not in record.file.lower():
                return False

        if project and record.project != project:
            return False

        return True

    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    async def _update_stats(self) -> None:
        """Update storage statistics"""
        # Flush current file to get accurate size
        if self._current_hot_handle:
            self._current_hot_handle.flush()

        # Hot storage stats
        hot_files = list(self.hot_dir.glob('events_*.jsonl'))
        self.stats.hot_files = len(hot_files)
        self.stats.hot_size_bytes = sum(f.stat().st_size for f in hot_files if f.exists())

        # Cold storage stats
        cold_files = list(self.cold_dir.rglob('*.parquet'))
        self.stats.cold_files = len(cold_files)
        self.stats.cold_size_bytes = sum(f.stat().st_size for f in cold_files if f.exists())

    def get_stats(self) -> StorageStats:
        """Get current storage statistics"""
        return StorageStats(
            hot_files=self.stats.hot_files,
            hot_size_bytes=self.stats.hot_size_bytes,
            hot_events=self.stats.hot_events,
            cold_files=self.stats.cold_files,
            cold_size_bytes=self.stats.cold_size_bytes,
            cold_events=self.stats.cold_events,
            last_archive=self.stats.last_archive,
            last_cleanup=self.stats.last_cleanup,
        )

    # -------------------------------------------------------------------------
    # Background Tasks
    # -------------------------------------------------------------------------

    async def _archive_loop(self) -> None:
        """Background task for periodic archival"""
        while self._running:
            try:
                await asyncio.sleep(self.options.archive_interval_minutes * 60)
                if self._running:
                    await self.archive_hot_files()
                    await self._update_stats()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Archive loop error: {e}")

    async def _cleanup_loop(self) -> None:
        """Background task for periodic cleanup"""
        while self._running:
            try:
                await asyncio.sleep(self.options.cleanup_interval_hours * 3600)
                if self._running:
                    await self.cleanup_old_files()
                    await self._update_stats()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")

    # -------------------------------------------------------------------------
    # Utilities
    # -------------------------------------------------------------------------

    def _log(self, message: str) -> None:
        """Debug logging"""
        if self.options.debug:
            logger.debug(f"[Archiver] {message}")


# =============================================================================
# SINGLETON
# =============================================================================

_default_archiver: Optional[Archiver] = None


def get_archiver(options: Optional[ArchiverOptions] = None) -> Archiver:
    """Get or create the default archiver"""
    global _default_archiver
    if _default_archiver is None:
        _default_archiver = Archiver(options)
    return _default_archiver


def reset_archiver() -> None:
    """Reset the default archiver"""
    global _default_archiver
    if _default_archiver:
        asyncio.create_task(_default_archiver.stop())
        _default_archiver = None
