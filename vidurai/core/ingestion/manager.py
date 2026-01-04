"""
Ingestion Manager for Knowledge Ingestion
Sprint 2 - "Ghost in the Shell"

Orchestrates the ingestion process:
1. Detect or select adapter
2. Stream events from file
3. Sanitize PII
4. Store with historical timestamps
5. Batch commits with hiccup prevention
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Generator, Callable

from loguru import logger

from vidurai.core.ingestion.sanitizer import PIISanitizer
from vidurai.core.ingestion.adapters import (
    BaseAdapter,
    ViduraiEvent,
    detect_adapter,
    get_adapter
)
from vidurai.vismriti_memory import VismritiMemory
from vidurai.core.data_structures_v3 import SalienceLevel


@dataclass
class IngestionStats:
    """Statistics from an ingestion run."""
    file_path: str
    source_type: str
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    events_processed: int = 0
    events_stored: int = 0
    events_skipped: int = 0
    pii_redactions: int = 0
    errors: int = 0
    conversations_seen: set = field(default_factory=set)

    @property
    def duration_seconds(self) -> float:
        """Get duration in seconds."""
        end = self.completed_at or datetime.now()
        return (end - self.started_at).total_seconds()

    @property
    def events_per_second(self) -> float:
        """Get processing rate."""
        duration = self.duration_seconds
        if duration > 0:
            return self.events_processed / duration
        return 0.0

    @property
    def conversations_count(self) -> int:
        """Get unique conversation count."""
        return len(self.conversations_seen)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'file_path': self.file_path,
            'source_type': self.source_type,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration_seconds': self.duration_seconds,
            'events_processed': self.events_processed,
            'events_stored': self.events_stored,
            'events_skipped': self.events_skipped,
            'pii_redactions': self.pii_redactions,
            'errors': self.errors,
            'conversations_count': self.conversations_count,
            'events_per_second': self.events_per_second
        }


class IngestionManager:
    """
    Manages the ingestion of historical AI conversations.

    Features:
    - Streaming processing for large files (>500MB)
    - PII sanitization before storage
    - Historical timestamp preservation
    - Batch processing with hiccup prevention
    - Progress callbacks for CLI integration

    Usage:
        >>> manager = IngestionManager(project_path="/my/project")
        >>> stats = manager.process_file("conversations.json", source_type="openai")
        >>> print(f"Ingested {stats.events_stored} events")
    """

    # Batch size for commit/sleep cycle (hiccup prevention)
    BATCH_SIZE = 50
    # Sleep duration between batches (10ms - enough for OS interrupts)
    BATCH_SLEEP_MS = 10

    def __init__(
        self,
        project_path: Optional[str] = None,
        memory: Optional[VismritiMemory] = None,
        sanitizer: Optional[PIISanitizer] = None,
        batch_size: int = None,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ):
        """
        Initialize ingestion manager.

        Args:
            project_path: Project path for memory storage
            memory: Optional pre-configured VismritiMemory instance
            sanitizer: Optional pre-configured PIISanitizer instance
            batch_size: Events per batch before sleep (default: 50)
            progress_callback: Optional callback(count, message) for progress
        """
        self.project_path = project_path or "."
        self.memory = memory or VismritiMemory(
            project_path=self.project_path,
            enable_gist_extraction=False,  # Don't extract gist from chat messages
            enable_aggregation=False  # Don't aggregate during ingestion
        )
        self.sanitizer = sanitizer or PIISanitizer()
        self.batch_size = batch_size or self.BATCH_SIZE
        self.progress_callback = progress_callback

        logger.info(f"IngestionManager initialized for project: {self.project_path}")

    def process_file(
        self,
        file_path: str,
        source_type: str = "auto",
        skip_roles: Optional[list] = None,
        min_content_length: int = 10,
        dry_run: bool = False
    ) -> IngestionStats:
        """
        Process an export file and ingest events.

        Args:
            file_path: Path to the export file
            source_type: 'openai', 'anthropic', 'gemini', or 'auto'
            skip_roles: Optional list of roles to skip (e.g., ['system'])
            min_content_length: Minimum content length to store (default: 10)
            dry_run: If True, don't store events (just count and sanitize)

        Returns:
            IngestionStats with processing results
        """
        file_path = Path(file_path)
        stats = IngestionStats(
            file_path=str(file_path),
            source_type=source_type
        )

        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            stats.errors += 1
            return stats

        # Get file size for progress estimation
        file_size = file_path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)
        logger.info(f"Processing {file_path.name} ({file_size_mb:.1f} MB)")

        # Detect or get adapter
        if source_type == "auto":
            adapter = detect_adapter(file_path)
            if adapter:
                stats.source_type = adapter.SOURCE_NAME
        else:
            adapter = get_adapter(source_type)
            if adapter:
                stats.source_type = adapter.SOURCE_NAME

        if not adapter:
            logger.error(f"Could not find adapter for {file_path.name}")
            stats.errors += 1
            return stats

        logger.info(f"Using {stats.source_type} adapter")

        # Process file
        skip_roles = skip_roles or []
        batch_count = 0

        try:
            with open(file_path, 'rb') as f:
                for event in adapter.stream_events(f):
                    stats.events_processed += 1

                    # Track conversations
                    if event.conversation_id:
                        stats.conversations_seen.add(event.conversation_id)

                    # Skip certain roles
                    if event.role in skip_roles:
                        stats.events_skipped += 1
                        continue

                    # Skip short content
                    if len(event.content) < min_content_length:
                        stats.events_skipped += 1
                        continue

                    # Sanitize PII
                    sanitized = self.sanitizer.clean_with_stats(event.content)
                    stats.pii_redactions += sanitized.redactions

                    if not dry_run:
                        # Store with historical timestamp
                        try:
                            self._store_event(event, sanitized.cleaned_text)
                            stats.events_stored += 1
                        except Exception as e:
                            logger.error(f"Error storing event: {e}")
                            stats.errors += 1
                    else:
                        stats.events_stored += 1  # Count as "would store"

                    # Batch processing with hiccup prevention
                    batch_count += 1
                    if batch_count >= self.batch_size:
                        # Sleep to allow OS interrupts (Ctrl+C, etc.)
                        time.sleep(self.BATCH_SLEEP_MS / 1000.0)
                        batch_count = 0

                        # Progress callback
                        if self.progress_callback:
                            self.progress_callback(
                                stats.events_processed,
                                f"Processed {stats.events_processed} events..."
                            )

        except Exception as e:
            logger.error(f"Error processing file: {e}")
            stats.errors += 1

        stats.completed_at = datetime.now()

        logger.info(
            f"Ingestion complete: {stats.events_stored} stored, "
            f"{stats.events_skipped} skipped, {stats.errors} errors, "
            f"{stats.pii_redactions} PII redactions"
        )

        return stats

    def _store_event(self, event: ViduraiEvent, sanitized_content: str) -> None:
        """
        Store a single event as a memory.

        Args:
            event: The ViduraiEvent to store
            sanitized_content: Already-sanitized content
        """
        # Build metadata
        metadata = {
            'type': f'{event.source}_import',
            'source': event.source,
            'role': event.role,
            'conversation_id': event.conversation_id,
            'conversation_title': event.conversation_title,
            'import_time': datetime.now().isoformat()
        }

        # Add any extra metadata from the event
        if event.metadata:
            metadata.update(event.metadata)

        # Determine salience based on role
        # User messages are generally more important (they define intent)
        salience = SalienceLevel.MEDIUM
        if event.role == 'user':
            salience = SalienceLevel.HIGH
        elif event.role == 'system':
            salience = SalienceLevel.LOW

        # Store with historical timestamp (Sprint 1.5 created_at support)
        self.memory.remember(
            content=sanitized_content,
            metadata=metadata,
            salience=salience,
            extract_gist=False,  # Don't re-extract gist from chat messages
            created_at=event.timestamp  # Preserve original timestamp
        )

    def stream_events(
        self,
        file_path: str,
        source_type: str = "auto"
    ) -> Generator[ViduraiEvent, None, None]:
        """
        Stream events from a file without storing them.

        Useful for preview/inspection of export files.

        Args:
            file_path: Path to the export file
            source_type: 'openai', 'anthropic', 'gemini', or 'auto'

        Yields:
            ViduraiEvent objects
        """
        file_path = Path(file_path)

        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return

        # Get adapter
        if source_type == "auto":
            adapter = detect_adapter(file_path)
        else:
            adapter = get_adapter(source_type)

        if not adapter:
            logger.error(f"Could not find adapter for {file_path.name}")
            return

        with open(file_path, 'rb') as f:
            yield from adapter.stream_events(f)

    def preview_file(
        self,
        file_path: str,
        source_type: str = "auto",
        max_events: int = 10
    ) -> list:
        """
        Preview first N events from a file.

        Args:
            file_path: Path to the export file
            source_type: 'openai', 'anthropic', 'gemini', or 'auto'
            max_events: Maximum events to return

        Returns:
            List of ViduraiEvent dicts
        """
        events = []
        for i, event in enumerate(self.stream_events(file_path, source_type)):
            if i >= max_events:
                break

            # Sanitize for preview
            sanitized = self.sanitizer.clean(event.content)

            events.append({
                'content': sanitized[:200] + '...' if len(sanitized) > 200 else sanitized,
                'timestamp': event.timestamp.isoformat(),
                'role': event.role,
                'source': event.source,
                'conversation_title': event.conversation_title
            })

        return events
