"""
Retention Judge - The Constitution's Enforcement Arm

The Constitution:
1. Immunity Clause: Pinned = 1 means ABSOLUTE VETO (never decay)
2. Purgatory Protocol: Low-utility memories go to PENDING_DECAY for user review
3. Utility Score: Mathematical formula determines memory value

Glass Box Protocol: Math Clarity
- Use the provided formula exactly
- Ensure division by zero is impossible (e.g., access_count + 1)
- Document all constants and their meanings

@version 2.1.0-Guardian
"""

import math
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from loguru import logger


# =============================================================================
# CONSTANTS
# =============================================================================

DB_PATH = Path.home() / '.vidurai' / 'vidurai.db'

# Utility Score Weights (must sum to 1.0)
WEIGHT_ACCESS = 0.4      # How often was it accessed?
WEIGHT_RECENCY = 0.4     # How recent is it?
WEIGHT_OUTCOME = 0.2     # Did it help? (RL signal)

# Decay Threshold
DECAY_THRESHOLD = 0.15   # Below this = PENDING_DECAY

# Status Values
STATUS_ACTIVE = 'ACTIVE'
STATUS_PENDING_DECAY = 'PENDING_DECAY'
STATUS_ARCHIVED = 'ARCHIVED'
STATUS_DECAYED = 'DECAYED'


# =============================================================================
# UTILITY SCORE CALCULATION
# =============================================================================

@dataclass
class UtilityScore:
    """
    Breakdown of a memory's utility score.

    Used for transparency and debugging.
    """
    memory_id: int
    access_score: float      # log(access_count + 1)
    recency_score: float     # 1 / (days_since_creation + 1)
    outcome_score: float     # -1, 0, or 1
    total_score: float       # Weighted sum
    verdict: str             # 'ACTIVE' or 'PENDING_DECAY'


def calculate_utility_score(
    access_count: int,
    days_since_creation: float,
    outcome: int
) -> tuple:
    """
    Calculate utility score for a memory.

    Formula:
        access_score = log(access_count + 1)
        recency_score = 1 / (days_since_creation + 1)
        outcome_score = outcome  # Already -1, 0, or 1

        total = (0.4 * access_score) + (0.4 * recency_score) + (0.2 * outcome_score)

    Glass Box: Math Clarity
    - access_count + 1 prevents log(0)
    - days_since_creation + 1 prevents division by zero
    - Outcome is already bounded [-1, 1]

    Args:
        access_count: Number of times memory was accessed
        days_since_creation: Age of memory in days
        outcome: RL signal (-1=Failure, 0=Unknown, 1=Success)

    Returns:
        Tuple of (access_score, recency_score, outcome_score, total_score)
    """
    # Access score: log scale (diminishing returns)
    # +1 prevents log(0), ensures minimum score
    access_score = math.log(access_count + 1)

    # Recency score: newer = higher
    # +1 prevents division by zero, ensures minimum score
    recency_score = 1.0 / (days_since_creation + 1)

    # Outcome score: direct from RL signal
    # Already bounded [-1, 1]
    outcome_score = float(outcome)

    # Weighted sum
    total_score = (
        (WEIGHT_ACCESS * access_score) +
        (WEIGHT_RECENCY * recency_score) +
        (WEIGHT_OUTCOME * outcome_score)
    )

    return (access_score, recency_score, outcome_score, total_score)


# =============================================================================
# RETENTION JUDGE
# =============================================================================

class RetentionJudge:
    """
    The Constitution's enforcement arm for memory retention.

    Laws:
    1. Immunity Clause: pinned=1 → ALWAYS return 'ACTIVE' (Absolute Veto)
    2. Utility Score: Calculate based on access, recency, outcome
    3. Verdict: score < 0.15 → 'PENDING_DECAY', else 'ACTIVE'

    Usage:
        judge = RetentionJudge()

        # Evaluate single memory
        verdict = judge.evaluate_memory(memory_row)

        # Batch evaluate all memories
        judge.evaluate_all_memories()

        # Get pending decay count
        count = judge.get_pending_decay_count()
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize RetentionJudge.

        Args:
            db_path: Path to SQLite database (default: ~/.vidurai/vidurai.db)
        """
        self.db_path = db_path or DB_PATH
        logger.debug("RetentionJudge initialized")

    def evaluate_memory(self, memory_row: Dict[str, Any]) -> str:
        """
        Evaluate a single memory and return verdict.

        Args:
            memory_row: Dictionary with memory data including:
                - id: Memory ID
                - pinned: 0 or 1
                - access_count: Number of accesses
                - created_at: Creation timestamp
                - outcome: RL signal (-1, 0, 1)

        Returns:
            'ACTIVE' or 'PENDING_DECAY'

        Constitution Laws:
        1. Immunity Clause: pinned=1 → ACTIVE (no further checks)
        2. Utility Score: Calculate and compare to threshold
        """
        memory_id = memory_row.get('id', 0)

        # LAW 1: Immunity Clause (Absolute Veto)
        if memory_row.get('pinned', 0) == 1:
            logger.debug(f"Memory {memory_id}: IMMUNE (pinned)")
            return STATUS_ACTIVE

        # Extract values
        access_count = memory_row.get('access_count', 0) or 0
        outcome = memory_row.get('outcome', 0) or 0

        # Calculate days since creation
        created_at = memory_row.get('created_at')
        if created_at:
            if isinstance(created_at, str):
                try:
                    created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except ValueError:
                    created_dt = datetime.now()
            else:
                created_dt = created_at
            days_since_creation = (datetime.now() - created_dt.replace(tzinfo=None)).days
        else:
            days_since_creation = 0

        # LAW 2: Calculate Utility Score
        access_score, recency_score, outcome_score, total_score = calculate_utility_score(
            access_count=access_count,
            days_since_creation=days_since_creation,
            outcome=outcome
        )

        # LAW 3: Verdict
        if total_score < DECAY_THRESHOLD:
            logger.debug(
                f"Memory {memory_id}: PENDING_DECAY (score={total_score:.3f} < {DECAY_THRESHOLD})"
            )
            return STATUS_PENDING_DECAY
        else:
            logger.debug(
                f"Memory {memory_id}: ACTIVE (score={total_score:.3f} >= {DECAY_THRESHOLD})"
            )
            return STATUS_ACTIVE

    def evaluate_memory_detailed(self, memory_row: Dict[str, Any]) -> UtilityScore:
        """
        Evaluate memory with detailed score breakdown.

        Returns UtilityScore dataclass for transparency.
        """
        memory_id = memory_row.get('id', 0)

        # Check immunity first
        if memory_row.get('pinned', 0) == 1:
            return UtilityScore(
                memory_id=memory_id,
                access_score=float('inf'),
                recency_score=float('inf'),
                outcome_score=float('inf'),
                total_score=float('inf'),
                verdict=STATUS_ACTIVE
            )

        # Calculate scores
        access_count = memory_row.get('access_count', 0) or 0
        outcome = memory_row.get('outcome', 0) or 0

        created_at = memory_row.get('created_at')
        if created_at:
            if isinstance(created_at, str):
                try:
                    created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except ValueError:
                    created_dt = datetime.now()
            else:
                created_dt = created_at
            days_since_creation = (datetime.now() - created_dt.replace(tzinfo=None)).days
        else:
            days_since_creation = 0

        access_score, recency_score, outcome_score, total_score = calculate_utility_score(
            access_count=access_count,
            days_since_creation=days_since_creation,
            outcome=outcome
        )

        verdict = STATUS_PENDING_DECAY if total_score < DECAY_THRESHOLD else STATUS_ACTIVE

        return UtilityScore(
            memory_id=memory_id,
            access_score=access_score,
            recency_score=recency_score,
            outcome_score=outcome_score,
            total_score=total_score,
            verdict=verdict
        )

    def evaluate_all_memories(self, project_id: Optional[int] = None) -> Dict[str, int]:
        """
        Evaluate all memories and update their status.

        Args:
            project_id: Filter by project (optional)

        Returns:
            Dictionary with counts: {'active': N, 'pending_decay': N, 'immune': N}
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Query all active memories
        if project_id:
            cursor.execute("""
                SELECT id, pinned, access_count, created_at, outcome
                FROM memories
                WHERE status = 'ACTIVE' AND project_id = ?
            """, (project_id,))
        else:
            cursor.execute("""
                SELECT id, pinned, access_count, created_at, outcome
                FROM memories
                WHERE status = 'ACTIVE'
            """)

        memories = cursor.fetchall()

        counts = {'active': 0, 'pending_decay': 0, 'immune': 0}
        updates = []

        for row in memories:
            memory_dict = dict(row)
            verdict = self.evaluate_memory(memory_dict)

            if memory_dict.get('pinned', 0) == 1:
                counts['immune'] += 1
            elif verdict == STATUS_PENDING_DECAY:
                counts['pending_decay'] += 1
                updates.append(memory_dict['id'])
            else:
                counts['active'] += 1

        # Batch update pending decay
        if updates:
            placeholders = ','.join('?' * len(updates))
            cursor.execute(f"""
                UPDATE memories
                SET status = 'PENDING_DECAY'
                WHERE id IN ({placeholders})
            """, updates)
            conn.commit()
            logger.info(f"Marked {len(updates)} memories as PENDING_DECAY")

        conn.close()

        return counts

    def get_pending_decay_count(self, project_id: Optional[int] = None) -> int:
        """Get count of memories pending decay."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        cursor = conn.cursor()

        if project_id:
            cursor.execute(
                "SELECT COUNT(*) FROM memories WHERE status = 'PENDING_DECAY' AND project_id = ?",
                (project_id,)
            )
        else:
            cursor.execute("SELECT COUNT(*) FROM memories WHERE status = 'PENDING_DECAY'")

        count = cursor.fetchone()[0]
        conn.close()

        return count

    def archive_pending(self) -> int:
        """
        Archive all memories with PENDING_DECAY status.

        Returns:
            Number of memories archived
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE memories
            SET status = 'ARCHIVED',
                decay_reason = 'Low utility score - archived by user'
            WHERE status = 'PENDING_DECAY'
        """)

        affected = cursor.rowcount
        conn.commit()
        conn.close()

        if affected > 0:
            logger.info(f"Archived {affected} memories")

        return affected

    def grant_mercy(self) -> int:
        """
        Grant mercy to all PENDING_DECAY memories.

        Bumps access_count and returns to ACTIVE status.

        Returns:
            Number of memories saved
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE memories
            SET status = 'ACTIVE',
                access_count = access_count + 1
            WHERE status = 'PENDING_DECAY'
        """)

        affected = cursor.rowcount
        conn.commit()
        conn.close()

        if affected > 0:
            logger.info(f"Granted mercy to {affected} memories (access_count bumped)")

        return affected

    def get_stats(self) -> Dict[str, Any]:
        """Get retention statistics."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        cursor = conn.cursor()

        # Count by status
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM memories
            GROUP BY status
        """)
        status_counts = {row[0] or 'ACTIVE': row[1] for row in cursor.fetchall()}

        # Count pinned
        cursor.execute("SELECT COUNT(*) FROM memories WHERE pinned = 1")
        pinned_count = cursor.fetchone()[0]

        conn.close()

        return {
            'status_counts': status_counts,
            'pinned_count': pinned_count,
            'decay_threshold': DECAY_THRESHOLD,
            'weights': {
                'access': WEIGHT_ACCESS,
                'recency': WEIGHT_RECENCY,
                'outcome': WEIGHT_OUTCOME,
            }
        }


# =============================================================================
# MODULE-LEVEL CONVENIENCE
# =============================================================================

_default_judge: Optional[RetentionJudge] = None


def get_judge(db_path: Optional[Path] = None) -> RetentionJudge:
    """Get or create the default RetentionJudge instance."""
    global _default_judge
    if _default_judge is None:
        _default_judge = RetentionJudge(db_path=db_path)
    return _default_judge


def evaluate_memory(memory_row: Dict[str, Any]) -> str:
    """
    Convenience function to evaluate a memory.

    Usage:
        from vidurai.core.constitution import evaluate_memory
        verdict = evaluate_memory({'id': 1, 'access_count': 5, ...})
    """
    return get_judge().evaluate_memory(memory_row)


# =============================================================================
# CLI TEST INTERFACE
# =============================================================================

def _test_cli():
    """
    Test function for manual verification.

    Usage:
        python -m vidurai.core.constitution.retention --test
    """
    import argparse

    parser = argparse.ArgumentParser(description="Retention Judge Test")
    parser.add_argument("--test", action="store_true", help="Run test cases")
    parser.add_argument("--evaluate", action="store_true", help="Evaluate all memories")
    parser.add_argument("--stats", action="store_true", help="Show statistics")

    args = parser.parse_args()

    judge = RetentionJudge()

    if args.stats:
        stats = judge.get_stats()
        print("\n=== Retention Statistics ===")
        print(f"Decay Threshold: {stats['decay_threshold']}")
        print(f"Weights: {stats['weights']}")
        print(f"Pinned Count: {stats['pinned_count']}")
        print(f"Status Counts: {stats['status_counts']}")
        return

    if args.evaluate:
        print("\nEvaluating all memories...")
        counts = judge.evaluate_all_memories()
        print(f"Results:")
        print(f"  Active: {counts['active']}")
        print(f"  Immune (pinned): {counts['immune']}")
        print(f"  Pending Decay: {counts['pending_decay']}")
        return

    if args.test:
        print("\n=== Retention Judge Test Cases ===\n")

        test_cases = [
            ("Pinned (immune)", {'id': 1, 'pinned': 1, 'access_count': 0, 'outcome': -1}),
            ("High access", {'id': 2, 'pinned': 0, 'access_count': 100, 'outcome': 0}),
            ("Recent + success", {'id': 3, 'pinned': 0, 'access_count': 1, 'outcome': 1, 'created_at': datetime.now().isoformat()}),
            ("Old + no access", {'id': 4, 'pinned': 0, 'access_count': 0, 'outcome': 0, 'created_at': '2020-01-01T00:00:00'}),
            ("Failed outcome", {'id': 5, 'pinned': 0, 'access_count': 2, 'outcome': -1, 'created_at': '2024-01-01T00:00:00'}),
        ]

        for name, memory in test_cases:
            score = judge.evaluate_memory_detailed(memory)
            print(f"[{score.verdict}] {name}")
            print(f"         Score: {score.total_score:.3f}")
            if score.total_score != float('inf'):
                print(f"         Access: {score.access_score:.3f}, Recency: {score.recency_score:.3f}, Outcome: {score.outcome_score:.1f}")
            print()


if __name__ == "__main__":
    _test_cli()
