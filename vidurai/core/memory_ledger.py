"""
Memory Ledger
Transparent view of forgetting operations

Research Foundation:
- Transparency requirement for user trust
- GDPR "Right to be Forgotten" compliance
- "Memory Ledger" concept from forgetting synthesis

Purpose:
Provides users with complete visibility into:
- What memories exist
- Why memories were forgotten
- Forgetting mechanisms applied
- Salience levels and decay status

जय विदुराई! 🕉️
"""

import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
from loguru import logger

from vidurai.core.data_structures_v3 import Memory, MemoryStatus, SalienceLevel


class MemoryLedger:
    """
    Transparent memory management ledger

    Research: "User transparency is critical for trust and adoption"

    Provides DataFrame view of all memories with:
    - Gist (semantic meaning)
    - Status (active/pruned/unlearned)
    - Salience (importance level)
    - Forgetting mechanism
    - Age and access patterns
    """

    def __init__(
        self,
        memories: List[Memory],
        decay_engine: Optional['PassiveDecayEngine'] = None
    ):
        """
        Initialize memory ledger

        Args:
            memories: List of all memories
            decay_engine: PassiveDecayEngine for decay info
        """
        self.memories = memories
        self.decay_engine = decay_engine

        logger.debug(f"MemoryLedger initialized with {len(memories)} memories")

    def get_ledger(self, include_pruned: bool = False) -> pd.DataFrame:
        """
        Generate comprehensive memory ledger

        Returns DataFrame matching research table format:
        | Memory (Gist) | Status | Salience | Forgetting Mechanism | Age | Accessed |

        Args:
            include_pruned: Include pruned/unlearned memories (default: False)

        Returns:
            Pandas DataFrame with memory ledger
        """

        ledger_data = []

        for memory in self.memories:
            # Filter pruned if requested
            if not include_pruned and memory.status in [
                MemoryStatus.PRUNED,
                MemoryStatus.UNLEARNED
            ]:
                continue

            ledger_data.append({
                "Gist": self._truncate(memory.gist, 80),
                "Verbatim Preview": self._truncate(memory.verbatim, 40) if memory.verbatim else "N/A",
                "Status": memory.status.value.title(),
                "Salience Score": memory.salience.value,
                "Salience Level": memory.salience.name,
                "Forgetting Mechanism": self._explain_forgetting(memory),
                "Age (days)": memory.age_days(),
                "Last Accessed": memory.last_accessed.strftime("%Y-%m-%d %H:%M"),
                "Access Count": memory.access_count,
                "Engram ID": memory.engram_id[:8]
            })

        df = pd.DataFrame(ledger_data)

        if not df.empty:
            # Sort by salience (highest first)
            df = df.sort_values("Salience Score", ascending=False)

        logger.info(f"Generated ledger with {len(df)} memories")

        return df

    def _explain_forgetting(self, memory: Memory) -> str:
        """
        Natural language explanation of forgetting strategy

        Maps to research mechanisms:
        - Passive Decay (System Pruning) - Synaptic pruning by microglia
        - Active Unlearning (Gradient Ascent) - Motivated forgetting (PFC)
        - Protected (EWC) - Elastic Weight Consolidation
        - Consolidated - Stable, high-salience memory
        - Silenced - Engram suppression
        """

        if memory.status == MemoryStatus.PRUNED:
            if memory.salience == SalienceLevel.NOISE:
                return "Passive Decay (System Pruning) - Verbatim noise cleanup"

            days_unused = memory.days_since_access()
            return (
                f"Passive Decay - Low salience ({memory.salience.name}), "
                f"{days_unused}d since last access"
            )

        if memory.status == MemoryStatus.UNLEARNED:
            method = memory.metadata.get("unlearn_method", "unknown")
            if method == "gradient_ascent":
                return "Active Unlearning (Gradient Ascent) - User-requested, RL retrained"
            return "Active Unlearning - User-requested suppression"

        if memory.status == MemoryStatus.CONSOLIDATED:
            if memory.salience == SalienceLevel.CRITICAL:
                return "Protected (EWC-style) - Critical memory, never decays"
            return f"Consolidated - High salience ({memory.salience.name}), durable"

        if memory.status == MemoryStatus.SILENCED:
            return "Silenced (Engram Suppression) - Trace exists but inaccessible"

        # Active memory
        if self.decay_engine:
            decay_info = self.decay_engine.get_decay_info(memory)
            if decay_info["will_decay"]:
                days_remaining = decay_info["time_remaining_days"]
                return f"Active - Will decay in {days_remaining}d ({memory.access_count} accesses)"

        return f"Active - {memory.access_count} accesses"

    def _truncate(self, text: str, max_len: int) -> str:
        """Truncate text with ellipsis"""
        if not text:
            return ""
        if len(text) <= max_len:
            return text
        return text[:max_len-3] + "..."

    def export_csv(self, filepath: str = "memory_ledger.csv", include_pruned: bool = False):
        """
        Export ledger to CSV file

        Args:
            filepath: Output file path
            include_pruned: Include pruned memories
        """
        df = self.get_ledger(include_pruned=include_pruned)
        df.to_csv(filepath, index=False)
        logger.info(f"Ledger exported to {filepath}")
        return filepath

    def get_statistics(self) -> Dict:
        """
        Get aggregate statistics about memory state

        Returns:
            Dictionary with counts and percentages
        """
        total = len(self.memories)

        status_counts = {}
        salience_counts = {}

        for memory in self.memories:
            # Count by status
            status = memory.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

            # Count by salience
            salience = memory.salience.name
            salience_counts[salience] = salience_counts.get(salience, 0) + 1

        return {
            "total_memories": total,
            "by_status": status_counts,
            "by_salience": salience_counts,
            "active_memories": status_counts.get("active", 0),
            "forgotten_memories": (
                status_counts.get("pruned", 0) +
                status_counts.get("unlearned", 0)
            )
        }

    def print_summary(self):
        """Print human-readable summary to console"""
        stats = self.get_statistics()

        print("\n" + "="*60)
        print("MEMORY LEDGER SUMMARY")
        print("="*60)
        print(f"Total Memories: {stats['total_memories']}")
        print(f"Active: {stats['active_memories']}")
        print(f"Forgotten: {stats['forgotten_memories']}")
        print("\nBy Status:")
        for status, count in stats['by_status'].items():
            pct = (count / stats['total_memories'] * 100)
            print(f"  {status.title()}: {count} ({pct:.1f}%)")
        print("\nBy Salience:")
        for salience, count in stats['by_salience'].items():
            pct = (count / stats['total_memories'] * 100)
            print(f"  {salience}: {count} ({pct:.1f}%)")
        print("="*60 + "\n")
