"""
Zombie Killer - Log Deduplication System

Glass Box Protocol: No Zombie Errors
- Before logging an error, check the ZombieKiller deduplicator
- Do not flood the user's console with 50 copies of the same traceback

The Zombie Killer maintains a time-windowed cache of error hashes.
Duplicate errors within the TTL window are silently dropped.

@version 2.1.0-Guardian
"""

import hashlib
import time
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from threading import Lock

logger = logging.getLogger("vidurai.zombie_killer")


@dataclass
class ZombieEntry:
    """A cached error entry with timestamp and occurrence count."""
    hash: str
    first_seen: float
    last_seen: float
    count: int


class LogDeduplicator:
    """
    Deduplicates log entries within a time window.

    Glass Box Protocol: No Zombie Errors
    - Tracks error hashes with timestamps
    - Drops duplicates within TTL window
    - Allows periodic re-logging after TTL expires

    Usage:
        dedup = LogDeduplicator(ttl_seconds=300)  # 5 minute window

        if dedup.should_process("TypeError: foo is not defined", line=42):
            logger.error("TypeError: foo is not defined")
        # Duplicate within 5 minutes will return False

    Thread Safety:
        All operations are thread-safe via internal lock.
    """

    def __init__(
        self,
        ttl_seconds: float = 300.0,  # 5 minutes default
        max_entries: int = 1000,     # Max cache size
        include_line_number: bool = True
    ):
        """
        Initialize LogDeduplicator.

        Args:
            ttl_seconds: Time-to-live for cached entries (seconds)
            max_entries: Maximum cache size (LRU eviction when exceeded)
            include_line_number: Include line number in hash for uniqueness
        """
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self.include_line_number = include_line_number

        # Cache: hash -> ZombieEntry
        self._cache: Dict[str, ZombieEntry] = {}
        self._lock = Lock()

        # Statistics
        self._total_processed = 0
        self._total_dropped = 0

    def _compute_hash(
        self,
        log_entry: str,
        line_number: Optional[int] = None,
        file_path: Optional[str] = None
    ) -> str:
        """
        Compute MD5 hash of error signature.

        The hash includes:
        - Error message (normalized)
        - Line number (if include_line_number is True)
        - File path (if provided)

        Args:
            log_entry: The error/log message
            line_number: Optional line number
            file_path: Optional file path

        Returns:
            MD5 hex digest of the signature
        """
        # Normalize: strip whitespace, lowercase for comparison
        normalized = log_entry.strip().lower()

        # Build signature components
        components = [normalized]

        if self.include_line_number and line_number is not None:
            components.append(f"line:{line_number}")

        if file_path:
            components.append(f"file:{file_path}")

        # Join and hash
        signature = "|".join(components)
        return hashlib.md5(signature.encode('utf-8')).hexdigest()

    def should_process(
        self,
        log_entry: str,
        line_number: Optional[int] = None,
        file_path: Optional[str] = None
    ) -> bool:
        """
        Check if a log entry should be processed or dropped.

        Glass Box Rule: If hash exists and is < TTL old, return False (drop it).

        Args:
            log_entry: The error/log message to check
            line_number: Optional line number for uniqueness
            file_path: Optional file path for uniqueness

        Returns:
            True if entry should be processed (new or expired)
            False if entry is a duplicate within TTL window (drop it)
        """
        now = time.time()
        entry_hash = self._compute_hash(log_entry, line_number, file_path)

        with self._lock:
            self._total_processed += 1

            # Check if entry exists in cache
            if entry_hash in self._cache:
                entry = self._cache[entry_hash]

                # Check if within TTL window
                if (now - entry.last_seen) < self.ttl_seconds:
                    # Duplicate within window - DROP IT
                    entry.last_seen = now
                    entry.count += 1
                    self._total_dropped += 1

                    logger.debug(
                        f"Zombie killed: duplicate #{entry.count} "
                        f"(hash={entry_hash[:8]}...)"
                    )
                    return False

                else:
                    # TTL expired - allow re-processing
                    entry.last_seen = now
                    entry.count += 1
                    logger.debug(
                        f"Zombie revived after TTL: #{entry.count} "
                        f"(hash={entry_hash[:8]}...)"
                    )
                    return True

            else:
                # New entry - add to cache
                self._cache[entry_hash] = ZombieEntry(
                    hash=entry_hash,
                    first_seen=now,
                    last_seen=now,
                    count=1
                )

                # LRU eviction if cache is full
                if len(self._cache) > self.max_entries:
                    self._evict_oldest()

                return True

    def _evict_oldest(self) -> None:
        """Evict the oldest entry from cache (LRU policy)."""
        if not self._cache:
            return

        # Find oldest by last_seen
        oldest_hash = min(
            self._cache.keys(),
            key=lambda h: self._cache[h].last_seen
        )
        del self._cache[oldest_hash]

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from cache.

        Returns:
            Number of entries removed
        """
        now = time.time()
        removed = 0

        with self._lock:
            expired_hashes = [
                h for h, entry in self._cache.items()
                if (now - entry.last_seen) >= self.ttl_seconds
            ]

            for h in expired_hashes:
                del self._cache[h]
                removed += 1

        if removed > 0:
            logger.debug(f"Zombie cleanup: removed {removed} expired entries")

        return removed

    def get_stats(self) -> Dict[str, int]:
        """
        Get deduplication statistics.

        Returns:
            Dict with cache_size, total_processed, total_dropped, drop_rate
        """
        with self._lock:
            drop_rate = (
                (self._total_dropped / self._total_processed * 100)
                if self._total_processed > 0 else 0
            )

            return {
                'cache_size': len(self._cache),
                'total_processed': self._total_processed,
                'total_dropped': self._total_dropped,
                'drop_rate_percent': round(drop_rate, 2)
            }

    def get_top_zombies(self, limit: int = 10) -> list:
        """
        Get top repeated errors (most frequently killed zombies).

        Returns:
            List of (hash, count) tuples sorted by count descending
        """
        with self._lock:
            sorted_entries = sorted(
                self._cache.values(),
                key=lambda e: e.count,
                reverse=True
            )

            return [
                {'hash': e.hash[:16], 'count': e.count, 'first_seen': e.first_seen}
                for e in sorted_entries[:limit]
            ]

    def clear(self) -> None:
        """Clear all cached entries and reset statistics."""
        with self._lock:
            self._cache.clear()
            self._total_processed = 0
            self._total_dropped = 0


# =============================================================================
# SINGLETON
# =============================================================================

_default_deduplicator: Optional[LogDeduplicator] = None


def get_deduplicator(
    ttl_seconds: float = 300.0,
    max_entries: int = 1000
) -> LogDeduplicator:
    """
    Get or create the default LogDeduplicator instance.

    Args:
        ttl_seconds: Time window for deduplication
        max_entries: Max cache size

    Returns:
        LogDeduplicator singleton instance
    """
    global _default_deduplicator
    if _default_deduplicator is None:
        _default_deduplicator = LogDeduplicator(
            ttl_seconds=ttl_seconds,
            max_entries=max_entries
        )
    return _default_deduplicator


def should_log(
    message: str,
    line_number: Optional[int] = None,
    file_path: Optional[str] = None
) -> bool:
    """
    Convenience function to check if a message should be logged.

    Usage:
        from vidurai.core.ingestion.zombie_killer import should_log

        if should_log("Error: connection failed", line=42):
            logger.error("Error: connection failed")
    """
    return get_deduplicator().should_process(message, line_number, file_path)


def reset_deduplicator() -> None:
    """Reset the default deduplicator instance."""
    global _default_deduplicator
    if _default_deduplicator:
        _default_deduplicator.clear()
    _default_deduplicator = None
