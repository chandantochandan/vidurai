"""
VismritiMemory - Intelligent Forgetting Memory System

The complete Vismriti Architecture implementation integrating:
- Phase 1: Gist/Verbatim Split (Fuzzy-Trace Theory)
- Phase 2: Salience Tagging (Dopamine-mediated)
- Phase 3A: Passive Decay (Synaptic Pruning)
- Phase 3B: Active Unlearning (Motivated Forgetting)
- Phase 4: Memory Ledger (Transparency)

Research Foundation: 104+ citations across neuroscience, AI, philosophy

विस्मृति भी विद्या है (Forgetting too is knowledge)
जय विदुराई! 🕉️
"""

import os
from typing import List, Dict, Optional, Any
from datetime import datetime
from loguru import logger

from vidurai.core.data_structures_v3 import Memory, SalienceLevel, MemoryStatus
from vidurai.core.salience_classifier import SalienceClassifier
from vidurai.core.passive_decay import PassiveDecayEngine
from vidurai.core.active_unlearning import ActiveUnlearningEngine
from vidurai.core.memory_ledger import MemoryLedger

# Optional gist extraction (requires OpenAI API key)
try:
    from vidurai.core.gist_extractor import GistExtractor
    GIST_EXTRACTION_AVAILABLE = True
except Exception:
    GIST_EXTRACTION_AVAILABLE = False
    logger.warning("Gist extraction unavailable (OpenAI API key not set)")

# Optional RL agent integration
try:
    from vidurai.core.rl_agent_v2 import VismritiRLAgent, RewardProfile
    RL_AGENT_AVAILABLE = True
except Exception:
    RL_AGENT_AVAILABLE = False
    RewardProfile = None
    logger.warning("RL Agent unavailable")


class VismritiMemory:
    """
    Vismriti Memory System - Intelligent Forgetting Architecture

    Research: "Forgetting is not a void; it is an active and intelligent process"

    Features:
    - Dual-trace memory (verbatim + gist)
    - Categorical salience (dopamine-inspired)
    - Differential decay (verbatim faster than gist)
    - Active unlearning (gradient ascent)
    - Complete transparency (memory ledger)

    Usage:
        >>> memory = VismritiMemory()
        >>> memory.remember("Fixed auth bug in auth.py", metadata={"solved_bug": True})
        >>> memories = memory.recall("auth bug")
        >>> ledger = memory.get_ledger()
        >>> memory.forget("temporary test data")
    """

    def __init__(
        self,
        enable_decay: bool = True,
        enable_gist_extraction: bool = False,
        enable_rl_agent: bool = False
    ):
        """
        Initialize VismritiMemory system

        Args:
            enable_decay: Enable passive decay (default: True)
            enable_gist_extraction: Extract gist from verbatim (default: False, requires OpenAI key)
            enable_rl_agent: Enable RL agent integration (default: False)
        """

        # Core components
        self.memories: List[Memory] = []

        # Phase 1: Gist Extraction (optional)
        self.enable_gist_extraction = enable_gist_extraction and GIST_EXTRACTION_AVAILABLE
        if self.enable_gist_extraction:
            self.gist_extractor = GistExtractor(model="gpt-4o-mini")
        else:
            self.gist_extractor = None

        # Phase 2: Salience Classification
        self.salience_classifier = SalienceClassifier()

        # Phase 3A: Passive Decay
        self.decay_engine = PassiveDecayEngine(enable_decay=enable_decay)

        # Phase 3B: Active Unlearning
        if enable_rl_agent and RL_AGENT_AVAILABLE:
            self.rl_agent = VismritiRLAgent(reward_profile=RewardProfile.QUALITY_FOCUSED)
        else:
            self.rl_agent = None

        self.unlearning_engine = ActiveUnlearningEngine(self.rl_agent)

        # Configuration
        self.enable_decay = enable_decay

        logger.info(
            f"VismritiMemory initialized: "
            f"gist={self.enable_gist_extraction}, decay={enable_decay}, "
            f"rl_agent={self.rl_agent is not None}"
        )

    def remember(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        salience: Optional[SalienceLevel] = None,
        extract_gist: bool = True
    ) -> Memory:
        """
        Store a new memory with intelligent processing

        Process:
        1. Split into verbatim + gist (if extraction enabled)
        2. Classify salience (dopamine-tagging simulation)
        3. Create Memory object
        4. Store in memory list

        Research: "All incoming data is immediately split into two
        independent representations: verbatim and gist"

        Args:
            content: Raw content to remember
            metadata: Additional context
            salience: Override salience classification (optional)
            extract_gist: Extract gist from content (default: True)

        Returns:
            Created Memory object

        Example:
            >>> memory.remember(
            ...     "Fixed authentication bug in auth.py",
            ...     metadata={"type": "bugfix", "file": "auth.py"}
            ... )
        """

        metadata = metadata or {}

        # Phase 1: Gist/Verbatim Split
        verbatim = content

        if self.enable_gist_extraction and extract_gist and self.gist_extractor:
            try:
                gist = self.gist_extractor.extract(verbatim, context=metadata)
            except Exception as e:
                logger.warning(f"Gist extraction failed: {e}, using verbatim as gist")
                gist = verbatim[:100]  # Fallback: truncate verbatim
        else:
            gist = verbatim  # No extraction, gist = verbatim

        # Create memory object
        memory = Memory(
            verbatim=verbatim,
            gist=gist,
            metadata=metadata
        )

        # Phase 2: Salience Classification
        if salience:
            memory.salience = salience  # User override
        else:
            memory.salience = self.salience_classifier.classify(memory)

        # Store
        self.memories.append(memory)

        logger.debug(
            f"Memory stored: gist='{gist[:50]}...', "
            f"salience={memory.salience.name}, "
            f"engram_id={memory.engram_id[:8]}"
        )

        return memory

    def recall(
        self,
        query: str,
        min_salience: Optional[SalienceLevel] = None,
        top_k: int = 10,
        include_forgotten: bool = False
    ) -> List[Memory]:
        """
        Retrieve memories matching query

        Phase 4: Reconstruction (not just keyword search)

        Research: "When user asks question, engine does not do simple
        keyword search. It reconstructs from durable gist memory."

        Args:
            query: Search query
            min_salience: Minimum salience level to include
            top_k: Maximum number of results
            include_forgotten: Include pruned/unlearned memories

        Returns:
            List of matching memories (sorted by relevance)
        """

        query_lower = query.lower()
        matches = []

        for memory in self.memories:
            # Filter by status
            if not include_forgotten and memory.status in [
                MemoryStatus.PRUNED,
                MemoryStatus.UNLEARNED
            ]:
                continue

            # Filter by salience
            if min_salience and memory.salience.value < min_salience.value:
                continue

            # Simple keyword matching (can be enhanced with semantic search)
            gist_lower = memory.gist.lower() if memory.gist else ""
            verbatim_lower = memory.verbatim.lower() if memory.verbatim else ""

            if query_lower in gist_lower or query_lower in verbatim_lower:
                # Record access (affects decay calculations)
                memory.access()
                matches.append(memory)

        # Sort by salience (higher first), then recency
        matches.sort(
            key=lambda m: (m.salience.value, m.created_at),
            reverse=True
        )

        results = matches[:top_k]

        logger.debug(f"Recall query '{query}': {len(results)} matches found")

        return results

    def forget(
        self,
        query: str,
        method: str = "simple_suppress",
        confirmation: bool = True
    ) -> Dict:
        """
        Actively forget memories matching query

        Phase 3B: Active Unlearning (Motivated Forgetting)

        Research: "This is motivated forgetting - conscious decision
        to suppress unwanted memories (lateral PFC → hippocampus)"

        Args:
            query: What to forget (search query)
            method: "gradient_ascent" or "simple_suppress"
            confirmation: Require explicit confirmation (safety)

        Returns:
            Statistics about forgetting operation

        Example:
            >>> memory.forget("temporary test data", confirmation=False)
            >>> memory.forget("debug logs", method="simple_suppress", confirmation=False)
        """

        # Find memories to forget
        memories_to_forget = self.recall(
            query,
            include_forgotten=False  # Don't forget already forgotten
        )

        if not memories_to_forget:
            logger.info(f"No memories found matching '{query}'")
            return {
                "memories_found": 0,
                "unlearned": 0,
                "query": query
            }

        # Safety confirmation
        if confirmation:
            logger.warning(
                f"About to forget {len(memories_to_forget)} memories. "
                f"Set confirmation=False to proceed."
            )
            return {
                "memories_found": len(memories_to_forget),
                "unlearned": 0,
                "confirmation_required": True,
                "message": "Set confirmation=False to proceed"
            }

        # Active unlearning
        stats = self.unlearning_engine.forget(
            memories_to_forget,
            method=method,
            explanation=f"User requested: '{query}'"
        )

        stats["query"] = query

        logger.info(
            f"Forgot {stats['unlearned']} memories matching '{query}' "
            f"via {method}"
        )

        return stats

    def run_decay_cycle(self) -> Dict:
        """
        Run passive decay cycle (simulates sleep cleanup)

        Phase 3A: Passive Decay (Synaptic Pruning)

        Research: "Sleep is to take out the garbage" - REM and SWS
        perform targeted memory cleanup

        Returns:
            Statistics about pruned memories
        """

        if not self.enable_decay:
            logger.info("Decay disabled, no pruning performed")
            return {"pruned": 0}

        stats = self.decay_engine.prune_batch(self.memories)

        logger.info(
            f"Decay cycle complete: {stats['pruned']} memories pruned"
        )

        return stats

    def get_ledger(
        self,
        include_pruned: bool = False,
        format: str = "dataframe"
    ):
        """
        Get transparent memory ledger

        Phase 4: Memory Ledger (Transparency)

        Research: "To make architecture perfectly transparent, present
        as 'Memory Ledger' users can inspect"

        Args:
            include_pruned: Include forgotten memories
            format: "dataframe" or "dict"

        Returns:
            Memory ledger (DataFrame or dict)
        """

        ledger = MemoryLedger(self.memories, self.decay_engine)

        if format == "dataframe":
            return ledger.get_ledger(include_pruned=include_pruned)
        elif format == "dict":
            df = ledger.get_ledger(include_pruned=include_pruned)
            return df.to_dict(orient="records")
        else:
            raise ValueError(f"Unknown format: {format}")

    def export_ledger(self, filepath: str = "memory_ledger.csv"):
        """Export memory ledger to CSV"""
        ledger = MemoryLedger(self.memories, self.decay_engine)
        return ledger.export_csv(filepath)

    def get_statistics(self) -> Dict:
        """Get comprehensive statistics about memory system"""
        ledger = MemoryLedger(self.memories, self.decay_engine)
        return ledger.get_statistics()

    def print_summary(self):
        """Print human-readable summary"""
        ledger = MemoryLedger(self.memories, self.decay_engine)
        ledger.print_summary()

    def __len__(self) -> int:
        """Get number of active memories"""
        return sum(
            1 for m in self.memories
            if m.status == MemoryStatus.ACTIVE
        )

    def __repr__(self):
        active = len(self)
        total = len(self.memories)
        return (
            f"VismritiMemory(active={active}, total={total}, "
            f"gist_extraction={self.enable_gist_extraction}, "
            f"decay={self.enable_decay})"
        )
