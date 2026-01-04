"""
Repo Analyst - Archive Intelligence Engine

The Awakening's analytics brain.
Queries archived memories in Parquet using DuckDB.

Glass Box Protocol: Empty Archive Rule
- Check if glob('~/.vidurai/archive/**/*.parquet') finds files
- If empty: Return [] (Don't crash)
- If exists: Create VIEW and run query

@version 2.1.0-Guardian
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from loguru import logger


# =============================================================================
# CONSTANTS
# =============================================================================

ARCHIVE_BASE = Path.home() / '.vidurai' / 'archive'


# =============================================================================
# REPO ANALYST
# =============================================================================

class RepoAnalyst:
    """
    Analytics engine for archived memories.

    Glass Box Protocol: Empty Archive Rule
    - Before any query, check if archive has files
    - Return empty list if archive is empty (don't crash)
    - Lazy load duckdb only when needed

    Usage:
        analyst = RepoAnalyst()

        # Query archive
        results = analyst.query_archive("SELECT * FROM history LIMIT 10")

        # Get memories with outcomes (for RL training)
        training_data = analyst.get_training_data()
    """

    def __init__(self, archive_base: Optional[Path] = None):
        """
        Initialize RepoAnalyst.

        Args:
            archive_base: Base path for Parquet archives
        """
        self.archive_base = archive_base or ARCHIVE_BASE

        # DuckDB connection (lazy loaded)
        self._con = None

        logger.debug(f"RepoAnalyst initialized (archive={self.archive_base})")

    def _has_archive_files(self) -> bool:
        """
        Check if archive has any Parquet files.

        Glass Box Protocol: Empty Archive Rule
        - Must check BEFORE any query
        - Prevents duckdb.read_parquet() crash on empty directory

        Returns:
            True if archive has files, False otherwise
        """
        if not self.archive_base.exists():
            return False

        # Use glob to find files
        parquet_files = list(self.archive_base.rglob('*.parquet'))
        return len(parquet_files) > 0

    def _get_connection(self):
        """
        Get or create DuckDB connection.

        Glass Box Protocol: Lazy Loading
        - Import duckdb only when needed
        - Create VIEW for archive files
        """
        if self._con is None:
            try:
                import duckdb  # Glass Box: Lazy Loading
            except ImportError:
                logger.error("RepoAnalyst: duckdb not installed")
                return None

            self._con = duckdb.connect()

            # Create VIEW for archive (if files exist)
            if self._has_archive_files():
                archive_glob = str(self.archive_base / '**' / '*.parquet')
                try:
                    self._con.execute(f"""
                        CREATE OR REPLACE VIEW history AS
                        SELECT * FROM read_parquet('{archive_glob}')
                    """)
                    logger.debug("RepoAnalyst: Created 'history' VIEW")
                except Exception as e:
                    logger.warning(f"RepoAnalyst: Failed to create VIEW: {e}")

        return self._con

    def query_archive(self, sql_query: str) -> List[Dict[str, Any]]:
        """
        Execute SQL query against archive.

        Glass Box Protocol: Empty Archive Rule
        - If archive is empty, return [] immediately
        - Don't crash on empty archive

        Args:
            sql_query: SQL query to execute (use 'history' VIEW)

        Returns:
            List of result dicts, or [] if archive empty/error
        """
        # Empty Archive Rule: Check first
        if not self._has_archive_files():
            logger.debug("RepoAnalyst: Archive is empty, returning []")
            return []

        con = self._get_connection()
        if con is None:
            return []

        try:
            result = con.execute(sql_query).fetchall()
            columns = [desc[0] for desc in con.description]

            # Convert to list of dicts
            return [dict(zip(columns, row)) for row in result]

        except Exception as e:
            logger.error(f"RepoAnalyst: Query failed: {e}")
            return []

    def get_training_data(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Get memories with outcomes for RL training.

        Used by DreamCycle to train the RL agent offline.

        Args:
            limit: Max rows to return

        Returns:
            List of memories where outcome != 0
        """
        return self.query_archive(f"""
            SELECT id, verbatim, gist, salience, outcome, access_count,
                   created_at, archived_at, file_path, event_type
            FROM history
            WHERE outcome IS NOT NULL AND outcome != 0
            ORDER BY archived_at DESC
            LIMIT {limit}
        """)

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get aggregate statistics from archive.

        Returns:
            Dict with archive statistics
        """
        if not self._has_archive_files():
            return {
                'total_memories': 0,
                'positive_outcomes': 0,
                'negative_outcomes': 0,
                'avg_salience': 0,
                'archive_empty': True,
            }

        stats_query = """
            SELECT
                COUNT(*) as total_memories,
                SUM(CASE WHEN outcome = 1 THEN 1 ELSE 0 END) as positive_outcomes,
                SUM(CASE WHEN outcome = -1 THEN 1 ELSE 0 END) as negative_outcomes,
                AVG(salience) as avg_salience,
                MIN(created_at) as oldest_memory,
                MAX(archived_at) as newest_archive
            FROM history
        """

        results = self.query_archive(stats_query)
        if results:
            stats = results[0]
            stats['archive_empty'] = False
            return stats

        return {'archive_empty': True}

    def search_archive(
        self,
        keyword: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search archived memories by keyword.

        Args:
            keyword: Search term (case-insensitive)
            limit: Max results

        Returns:
            List of matching memories
        """
        # Escape single quotes in keyword
        safe_keyword = keyword.replace("'", "''")

        return self.query_archive(f"""
            SELECT id, content, salience, outcome, project_path, archived_at
            FROM history
            WHERE LOWER(content) LIKE LOWER('%{safe_keyword}%')
            ORDER BY archived_at DESC
            LIMIT {limit}
        """)

    def close(self):
        """Close DuckDB connection."""
        if self._con:
            self._con.close()
            self._con = None
            logger.debug("RepoAnalyst: Connection closed")


# =============================================================================
# MODULE-LEVEL CONVENIENCE
# =============================================================================

_default_analyst: Optional[RepoAnalyst] = None


def get_analyst(archive_base: Optional[Path] = None) -> RepoAnalyst:
    """Get or create the default RepoAnalyst instance."""
    global _default_analyst
    if _default_analyst is None:
        _default_analyst = RepoAnalyst(archive_base=archive_base)
    return _default_analyst


def query_archive(sql_query: str) -> List[Dict[str, Any]]:
    """Convenience function to query archive."""
    return get_analyst().query_archive(sql_query)


# =============================================================================
# CLI TEST INTERFACE
# =============================================================================

def _test_cli():
    """
    Test function for manual verification.

    Usage:
        python -m vidurai.core.analytics.engine --test
    """
    import argparse

    parser = argparse.ArgumentParser(description="Repo Analyst Test")
    parser.add_argument("--test", action="store_true", help="Run test cases")
    parser.add_argument("--stats", action="store_true", help="Show archive statistics")
    parser.add_argument("--query", type=str, help="Execute SQL query")
    parser.add_argument("--search", type=str, help="Search keyword")

    args = parser.parse_args()

    analyst = RepoAnalyst()

    if args.stats:
        stats = analyst.get_memory_stats()
        print("\n=== Archive Statistics ===")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        return

    if args.query:
        print(f"\nExecuting: {args.query}")
        results = analyst.query_archive(args.query)
        print(f"Results: {len(results)} rows")
        for row in results[:5]:
            print(f"  {row}")
        return

    if args.search:
        print(f"\nSearching: {args.search}")
        results = analyst.search_archive(args.search)
        print(f"Results: {len(results)} matches")
        for row in results[:5]:
            content_preview = row.get('content', '')[:50]
            print(f"  {content_preview}...")
        return

    if args.test:
        print("\n=== Repo Analyst Test Cases ===\n")

        # Test 1: Create analyst
        try:
            a = RepoAnalyst()
            print("[PASS] Create analyst")
        except Exception as e:
            print(f"[FAIL] Create analyst: {e}")
            return

        # Test 2: Check archive files (Empty Archive Rule)
        try:
            has_files = a._has_archive_files()
            print(f"[PASS] Has archive files: {has_files}")
        except Exception as e:
            print(f"[FAIL] Check archive files: {e}")

        # Test 3: Get stats (should not crash even if empty)
        try:
            stats = a.get_memory_stats()
            print(f"[PASS] Get stats: archive_empty={stats.get('archive_empty')}")
        except Exception as e:
            print(f"[FAIL] Get stats: {e}")

        # Test 4: Query (should return [] if empty)
        try:
            results = a.query_archive("SELECT COUNT(*) FROM history")
            print(f"[PASS] Query archive: {len(results)} results")
        except Exception as e:
            print(f"[FAIL] Query archive: {e}")

        # Test 5: Get training data (for DreamCycle)
        try:
            training = a.get_training_data(limit=10)
            print(f"[PASS] Get training data: {len(training)} rows")
        except Exception as e:
            print(f"[FAIL] Get training data: {e}")

        # Cleanup
        analyst.close()
        print()


if __name__ == "__main__":
    _test_cli()
