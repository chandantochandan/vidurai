"""
Memory Archiver - SQLite to Parquet Migration

The Awakening's storage lifecycle manager.
Moves ARCHIVED memories from SQLite (Hot) to Parquet (Cold).

Glass Box Protocol: Atomic Archiver
1. Select rows where status = 'ARCHIVED'
2. Write to Parquet file (year=YYYY/month=MM partition)
3. VERIFY file exists on disk
4. ONLY THEN DELETE from SQLite

CRITICAL: Never delete from SQLite before Parquet write is confirmed.

@version 2.1.0-Guardian
"""

import os
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from loguru import logger


# =============================================================================
# CONSTANTS
# =============================================================================

DB_PATH = Path.home() / '.vidurai' / 'vidurai.db'
ARCHIVE_BASE = Path.home() / '.vidurai' / 'archive'


# =============================================================================
# MEMORY ARCHIVER
# =============================================================================

class MemoryArchiver:
    """
    Moves ARCHIVED memories from SQLite to Parquet.

    Glass Box Protocol: Atomic Archiver
    - Atomic Protocol: Select → Write → Verify → Purge
    - Partition Structure: year=YYYY/month=MM/memories_{timestamp}.parquet
    - Lazy Loading: pandas imported inside methods

    Usage:
        archiver = MemoryArchiver()
        count = archiver.flush_archived_memories()
        print(f"Archived {count} memories to Parquet")
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        archive_base: Optional[Path] = None
    ):
        """
        Initialize MemoryArchiver.

        Args:
            db_path: Path to SQLite database (default: ~/.vidurai/vidurai.db)
            archive_base: Base path for Parquet archives (default: ~/.vidurai/archive)
        """
        self.db_path = db_path or DB_PATH
        self.archive_base = archive_base or ARCHIVE_BASE

        # Ensure archive directory exists
        self.archive_base.mkdir(parents=True, exist_ok=True)

        logger.debug(f"MemoryArchiver initialized (db={self.db_path})")

    def flush_archived_memories(self) -> int:
        """
        Move ARCHIVED memories from SQLite to Parquet.

        Glass Box Protocol: Atomic Archiver
        1. Select rows where status = 'ARCHIVED'
        2. Convert to DataFrame
        3. Write to Parquet (partitioned by year/month)
        4. VERIFY file exists
        5. DELETE from SQLite ONLY if verified

        Returns:
            Number of memories archived (0 if none to archive)
        """
        # Step 1: Select ARCHIVED rows
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, verbatim, gist, salience, created_at, expires_at,
                   access_count, outcome, file_path, decay_reason, event_type,
                   tags, project_id
            FROM memories
            WHERE status = 'ARCHIVED'
        """)

        rows = cursor.fetchall()

        if not rows:
            logger.debug("MemoryArchiver: No ARCHIVED memories to flush")
            conn.close()
            return 0

        # Convert to list of dicts for DataFrame
        memories = []
        memory_ids = []
        for row in rows:
            memory_ids.append(row['id'])
            memories.append({
                'id': row['id'],
                'verbatim': row['verbatim'],
                'gist': row['gist'],
                'salience': row['salience'],
                'created_at': row['created_at'],
                'expires_at': row['expires_at'],
                'access_count': row['access_count'],
                'outcome': row['outcome'],
                'file_path': row['file_path'],
                'decay_reason': row['decay_reason'],
                'event_type': row['event_type'],
                'tags': row['tags'],
                'project_id': row['project_id'],
                'archived_at': datetime.now().isoformat(),
            })

        logger.info(f"MemoryArchiver: Found {len(memories)} ARCHIVED memories to flush")

        # Step 2: Convert to DataFrame (LAZY LOAD pandas)
        try:
            import pandas as pd  # Glass Box: Lazy Loading
        except ImportError:
            logger.error("MemoryArchiver: pandas not installed - cannot archive")
            conn.close()
            return 0

        df = pd.DataFrame(memories)

        # Step 3: Write to Parquet (partitioned by year/month)
        now = datetime.now()
        partition_path = self.archive_base / f"year={now.year}" / f"month={now.month:02d}"
        partition_path.mkdir(parents=True, exist_ok=True)

        timestamp = now.strftime('%Y%m%d_%H%M%S')
        parquet_file = partition_path / f"memories_{timestamp}.parquet"

        try:
            df.to_parquet(parquet_file, engine='pyarrow', compression='snappy')
            logger.info(f"MemoryArchiver: Wrote {len(memories)} memories to {parquet_file}")
        except Exception as e:
            logger.error(f"MemoryArchiver: Parquet write failed: {e}")
            conn.close()
            return 0

        # Step 4: VERIFY file exists (Glass Box: Atomic Protocol)
        if not parquet_file.exists():
            logger.error(f"MemoryArchiver: VERIFY FAILED - file not found: {parquet_file}")
            conn.close()
            return 0

        file_size = parquet_file.stat().st_size
        if file_size == 0:
            logger.error(f"MemoryArchiver: VERIFY FAILED - file is empty: {parquet_file}")
            parquet_file.unlink()  # Remove empty file
            conn.close()
            return 0

        logger.debug(f"MemoryArchiver: VERIFY PASSED - {parquet_file} ({file_size} bytes)")

        # Step 5: DELETE from SQLite (ONLY after verification)
        try:
            placeholders = ','.join('?' * len(memory_ids))
            cursor.execute(f"""
                DELETE FROM memories
                WHERE id IN ({placeholders})
            """, memory_ids)
            conn.commit()
            logger.info(f"MemoryArchiver: Purged {len(memory_ids)} memories from SQLite")
        except Exception as e:
            logger.error(f"MemoryArchiver: SQLite purge failed: {e}")
            # Note: Parquet file exists, data is safe even if purge fails
            conn.close()
            return len(memory_ids)  # Still count as archived (data is in Parquet)

        conn.close()

        return len(memory_ids)

    def get_archive_stats(self) -> Dict[str, Any]:
        """
        Get archive statistics.

        Returns:
            Dict with archive file counts and sizes
        """
        parquet_files = list(self.archive_base.rglob('*.parquet'))

        total_size = sum(f.stat().st_size for f in parquet_files if f.exists())

        # Count by year/month
        partitions = {}
        for f in parquet_files:
            parts = f.parts
            # Find year=YYYY and month=MM parts
            year_part = next((p for p in parts if p.startswith('year=')), None)
            month_part = next((p for p in parts if p.startswith('month=')), None)
            if year_part and month_part:
                key = f"{year_part}/{month_part}"
                partitions[key] = partitions.get(key, 0) + 1

        return {
            'total_files': len(parquet_files),
            'total_size_bytes': total_size,
            'total_size_mb': total_size / (1024 * 1024),
            'partitions': partitions,
            'archive_base': str(self.archive_base),
        }

    def list_archive_files(self) -> List[Path]:
        """
        List all archive Parquet files.

        Returns:
            List of Path objects for all archive files
        """
        return list(self.archive_base.rglob('*.parquet'))


# =============================================================================
# MODULE-LEVEL CONVENIENCE
# =============================================================================

_default_archiver: Optional[MemoryArchiver] = None


def get_archiver(
    db_path: Optional[Path] = None,
    archive_base: Optional[Path] = None
) -> MemoryArchiver:
    """Get or create the default MemoryArchiver instance."""
    global _default_archiver
    if _default_archiver is None:
        _default_archiver = MemoryArchiver(db_path=db_path, archive_base=archive_base)
    return _default_archiver


def flush_archived_memories() -> int:
    """Convenience function to flush archived memories."""
    return get_archiver().flush_archived_memories()


# =============================================================================
# CLI TEST INTERFACE
# =============================================================================

def _test_cli():
    """
    Test function for manual verification.

    Usage:
        python -m vidurai.core.archival.archiver --test
    """
    import argparse

    parser = argparse.ArgumentParser(description="Memory Archiver Test")
    parser.add_argument("--test", action="store_true", help="Run test cases")
    parser.add_argument("--flush", action="store_true", help="Flush archived memories")
    parser.add_argument("--stats", action="store_true", help="Show archive statistics")

    args = parser.parse_args()

    archiver = MemoryArchiver()

    if args.stats:
        stats = archiver.get_archive_stats()
        print("\n=== Archive Statistics ===")
        print(f"  Total Files: {stats['total_files']}")
        print(f"  Total Size: {stats['total_size_mb']:.2f} MB")
        print(f"  Archive Base: {stats['archive_base']}")
        print(f"  Partitions:")
        for partition, count in stats.get('partitions', {}).items():
            print(f"    {partition}: {count} files")
        return

    if args.flush:
        print("\nFlushing archived memories...")
        count = archiver.flush_archived_memories()
        print(f"Archived {count} memories to Parquet")
        return

    if args.test:
        print("\n=== Memory Archiver Test Cases ===\n")

        # Test 1: Create archiver
        try:
            a = MemoryArchiver()
            print("[PASS] Create archiver")
        except Exception as e:
            print(f"[FAIL] Create archiver: {e}")
            return

        # Test 2: Get stats (should not crash)
        try:
            stats = a.get_archive_stats()
            print(f"[PASS] Get stats: {stats['total_files']} files")
        except Exception as e:
            print(f"[FAIL] Get stats: {e}")

        # Test 3: List files (should not crash)
        try:
            files = a.list_archive_files()
            print(f"[PASS] List files: {len(files)} archive files")
        except Exception as e:
            print(f"[FAIL] List files: {e}")

        # Test 4: Flush (may return 0 if no archived memories)
        try:
            count = a.flush_archived_memories()
            print(f"[PASS] Flush archived: {count} memories")
        except Exception as e:
            print(f"[FAIL] Flush archived: {e}")

        print()


if __name__ == "__main__":
    _test_cli()
