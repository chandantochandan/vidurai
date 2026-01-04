"""
Reality Check Sensor - Ground Truth Verification

Verifies if code snippets in memories actually exist in the codebase.
Provides RL signal (outcome) for learning from real-world results.

Glass Box Protocol:
- Fuzzy Reality: Use normalized matching (strip whitespace) to handle formatting
- Robustness: Handle missing files, encoding errors gracefully
- Integration: Updates outcome column in memories table

Outcome Values:
-  1 = Success (code exists in file)
- -1 = Failure (code not found in file)
-  0 = Unknown (file not found, encoding error, etc.)

@version 2.1.0-Guardian
"""

import re
import sqlite3
from pathlib import Path
from typing import Optional, Tuple
from loguru import logger

# =============================================================================
# CONSTANTS
# =============================================================================

DB_PATH = Path.home() / '.vidurai' / 'vidurai.db'

# Outcome values
OUTCOME_SUCCESS = 1   # Code exists in file
OUTCOME_FAILURE = -1  # Code not found in file
OUTCOME_UNKNOWN = 0   # Cannot determine (file missing, error, etc.)


# =============================================================================
# REALITY VERIFIER
# =============================================================================

class RealityVerifier:
    """
    Verifies memory snippets against actual file contents.

    Glass Box Protocol: Fuzzy Reality
    - Normalizes whitespace for comparison
    - Handles formatting differences (tabs vs spaces)
    - Provides RL signal for learning

    Usage:
        verifier = RealityVerifier()

        # Verify a specific memory
        outcome = verifier.verify_outcome(
            memory_id=42,
            file_path="/path/to/file.py",
            snippet="def hello():"
        )

        # Update database with result
        verifier.update_db_outcome(memory_id=42, result=outcome)
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize RealityVerifier.

        Args:
            db_path: Path to SQLite database (default: ~/.vidurai/vidurai.db)
        """
        self.db_path = db_path or DB_PATH
        logger.debug("RealityVerifier initialized")

    @staticmethod
    def normalize(text: str) -> str:
        """
        Normalize text for comparison.

        Glass Box Protocol: Fuzzy Reality
        - Strips all whitespace (spaces, tabs, newlines)
        - Converts to lowercase
        - Removes comments (optional)

        This handles formatting differences like:
        - Tabs vs spaces
        - Trailing whitespace
        - Line ending differences
        """
        if not text:
            return ""

        # Remove all whitespace characters
        normalized = re.sub(r'\s+', '', text)

        # Lowercase for case-insensitive matching
        normalized = normalized.lower()

        return normalized

    def verify_outcome(
        self,
        memory_id: int,
        file_path: str,
        snippet: str
    ) -> int:
        """
        Verify if a code snippet exists in the specified file.

        Args:
            memory_id: ID of the memory being verified
            file_path: Path to the file to check
            snippet: Code snippet to search for

        Returns:
            1 (Success/Present), -1 (Failure/Missing), 0 (Unknown/Error)

        Glass Box Protocol:
        - Normalizes both snippet and file content
        - Handles missing files gracefully
        - Logs verification attempts
        """
        if not file_path or not snippet:
            logger.debug(f"Reality check skipped for memory {memory_id}: missing file_path or snippet")
            return OUTCOME_UNKNOWN

        file_path_obj = Path(file_path)

        # Check if file exists
        if not file_path_obj.exists():
            logger.debug(f"Reality check: file not found - {file_path}")
            return OUTCOME_UNKNOWN

        if not file_path_obj.is_file():
            logger.debug(f"Reality check: not a file - {file_path}")
            return OUTCOME_UNKNOWN

        # Read file content
        try:
            file_content = file_path_obj.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            # Try with latin-1 as fallback
            try:
                file_content = file_path_obj.read_text(encoding='latin-1')
            except Exception as e:
                logger.debug(f"Reality check: encoding error - {file_path}: {e}")
                return OUTCOME_UNKNOWN
        except Exception as e:
            logger.debug(f"Reality check: read error - {file_path}: {e}")
            return OUTCOME_UNKNOWN

        # Normalize both for comparison (Fuzzy Reality)
        normalized_snippet = self.normalize(snippet)
        normalized_content = self.normalize(file_content)

        # Check if normalized snippet exists in normalized content
        if normalized_snippet in normalized_content:
            logger.debug(f"Reality check PASS: memory {memory_id} found in {file_path}")
            return OUTCOME_SUCCESS
        else:
            logger.debug(f"Reality check FAIL: memory {memory_id} not found in {file_path}")
            return OUTCOME_FAILURE

    def update_db_outcome(self, memory_id: int, result: int) -> bool:
        """
        Update the outcome column for a memory.

        Args:
            memory_id: Memory ID to update
            result: Outcome value (1, -1, or 0)

        Returns:
            True if update succeeded, False otherwise
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute(
                "UPDATE memories SET outcome = ? WHERE id = ?",
                (result, memory_id)
            )

            affected = cursor.rowcount
            conn.commit()
            conn.close()

            if affected > 0:
                outcome_name = {1: "SUCCESS", -1: "FAILURE", 0: "UNKNOWN"}.get(result, "?")
                logger.debug(f"Updated memory {memory_id} outcome to {outcome_name}")
                return True
            else:
                logger.warning(f"Memory {memory_id} not found for outcome update")
                return False

        except Exception as e:
            logger.error(f"Failed to update outcome for memory {memory_id}: {e}")
            return False

    def verify_and_update(
        self,
        memory_id: int,
        file_path: str,
        snippet: str
    ) -> int:
        """
        Verify outcome and update database in one call.

        Convenience method combining verify_outcome + update_db_outcome.

        Args:
            memory_id: Memory ID
            file_path: File to check
            snippet: Snippet to verify

        Returns:
            Outcome value (1, -1, or 0)
        """
        result = self.verify_outcome(memory_id, file_path, snippet)
        self.update_db_outcome(memory_id, result)
        return result

    def batch_verify(self, limit: int = 100) -> Tuple[int, int, int]:
        """
        Verify memories that have outcome=0 (Unknown).

        Finds memories with file_path and verbatim content,
        verifies them against actual files.

        Args:
            limit: Max memories to verify in this batch

        Returns:
            Tuple of (success_count, failure_count, unknown_count)
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Find unverified memories with file paths
        cursor.execute("""
            SELECT id, file_path, verbatim
            FROM memories
            WHERE outcome = 0
              AND file_path IS NOT NULL
              AND file_path != ''
              AND verbatim IS NOT NULL
              AND verbatim != ''
            LIMIT ?
        """, (limit,))

        memories = cursor.fetchall()
        conn.close()

        if not memories:
            logger.info("No memories to verify")
            return (0, 0, 0)

        logger.info(f"Verifying {len(memories)} memories...")

        success = 0
        failure = 0
        unknown = 0

        for memory_id, file_path, verbatim in memories:
            result = self.verify_and_update(memory_id, file_path, verbatim)

            if result == OUTCOME_SUCCESS:
                success += 1
            elif result == OUTCOME_FAILURE:
                failure += 1
            else:
                unknown += 1

        logger.info(
            f"Verification complete: {success} success, {failure} failure, {unknown} unknown"
        )

        return (success, failure, unknown)

    def get_stats(self) -> dict:
        """Get reality verification statistics."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Count by outcome
        cursor.execute("""
            SELECT outcome, COUNT(*) as count
            FROM memories
            GROUP BY outcome
        """)

        outcome_counts = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()

        total = sum(outcome_counts.values())

        return {
            'total_memories': total,
            'verified_success': outcome_counts.get(OUTCOME_SUCCESS, 0),
            'verified_failure': outcome_counts.get(OUTCOME_FAILURE, 0),
            'unverified': outcome_counts.get(OUTCOME_UNKNOWN, 0),
            'verification_rate': round(
                ((outcome_counts.get(OUTCOME_SUCCESS, 0) + outcome_counts.get(OUTCOME_FAILURE, 0))
                 / total * 100) if total > 0 else 0, 2
            )
        }


# =============================================================================
# MODULE-LEVEL CONVENIENCE
# =============================================================================

_default_verifier: Optional[RealityVerifier] = None


def get_reality_verifier(db_path: Optional[Path] = None) -> RealityVerifier:
    """
    Get or create the default RealityVerifier instance.

    Args:
        db_path: Optional database path

    Returns:
        RealityVerifier singleton
    """
    global _default_verifier
    if _default_verifier is None:
        _default_verifier = RealityVerifier(db_path=db_path)
    return _default_verifier


def reset_reality_verifier() -> None:
    """Reset the default verifier instance."""
    global _default_verifier
    _default_verifier = None


# =============================================================================
# CLI TEST INTERFACE
# =============================================================================

def _test_cli():
    """
    Test function for manual verification.

    Usage:
        python -m vidurai.core.sensors.reality_check --test
    """
    import argparse

    parser = argparse.ArgumentParser(description="Reality Check Sensor Test")
    parser.add_argument("--test", action="store_true", help="Run test verification")
    parser.add_argument("--batch", type=int, default=10, help="Batch size for verification")
    parser.add_argument("--stats", action="store_true", help="Show statistics")

    args = parser.parse_args()

    verifier = RealityVerifier()

    if args.stats:
        stats = verifier.get_stats()
        print("\n=== Reality Check Statistics ===")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        return

    if args.test or args.batch:
        print(f"\nRunning batch verification (limit={args.batch})...")
        success, failure, unknown = verifier.batch_verify(limit=args.batch)
        print(f"\nResults:")
        print(f"  Success: {success}")
        print(f"  Failure: {failure}")
        print(f"  Unknown: {unknown}")


if __name__ == "__main__":
    _test_cli()
