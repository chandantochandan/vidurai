"""
Passive Decay Engine
Automatic forgetting via differential decay rates

Research Foundation:
- Synaptic pruning by microglia ("eat-me" signals)
- "Sleep to Forget" - cleanup during rest cycles
- Fuzzy-Trace Theory: Verbatim decays faster than gist
- "Synaptic Pruning: Optimizing global network architectures" (PLOS)

Biological Process:
Microglia (immune cells) phagocytize (eat) weak synapses based on:
- Contact-dependent signals ('eat-me', 'don't-eat-me', 'find-me')
- Usage patterns (unused synapses tagged for removal)
- Salience (important memories protected via consolidation)

Implementation:
- Different decay rates per salience level
- Verbatim decays 70% faster than gist (research finding)
- Unused memories decay faster (lack of retrieval = 'eat-me' signal)

जय विदुराई! 🕉️
"""

from datetime import datetime, timedelta
from typing import List, Dict
from loguru import logger

from vidurai.core.data_structures_v3 import Memory, SalienceLevel, MemoryStatus


class PassiveDecayEngine:
    """
    Passive forgetting via synaptic pruning simulation

    Research: "The brain expends significant energy not just to record
    the past, but to actively erase it" - Sleep-dependent cleanup

    Decay Rates (Research-based):
    - CRITICAL: Never decays (protected via EWC-style consolidation)
    - HIGH: 180 days (durable, like consolidated episodic memories)
    - MEDIUM: 90 days (normal working memory persistence)
    - LOW: 7 days (short-term, rapidly fading)
    - NOISE: 1 day (immediate cleanup, like raw sensory data)
    """

    def __init__(self, enable_decay: bool = True):
        """
        Initialize passive decay engine

        Args:
            enable_decay: Enable/disable automatic decay (default: True)
        """
        self.enable_decay = enable_decay

        # Decay periods based on neuroscience research
        # Research: "Verbatim traces become inaccessible at faster rate"
        self.decay_periods = {
            SalienceLevel.CRITICAL: None,                    # Protected (never decays)
            SalienceLevel.HIGH: timedelta(days=180),         # 6 months
            SalienceLevel.MEDIUM: timedelta(days=90),        # 3 months
            SalienceLevel.LOW: timedelta(days=7),            # 1 week
            SalienceLevel.NOISE: timedelta(hours=24),        # 1 day
        }

        # Verbatim decay multiplier (research: verbatim decays faster)
        # "Verbatim traces become inaccessible at faster rate than gist"
        self.verbatim_decay_multiplier = 0.3  # 70% faster decay

        # Unused memory multiplier (lack of access = 'eat-me' signal)
        self.unused_multiplier = 0.7  # 30% faster if never accessed

        logger.info(f"PassiveDecayEngine initialized (enabled={enable_decay})")

    def should_prune(self, memory: Memory) -> bool:
        """
        Determine if memory should be pruned

        Research: "Microglia phagocytize synapses based on usage patterns
        and salience tags"

        Decision factors:
        1. Salience level (dopamine-tagged importance)
        2. Age since creation
        3. Access patterns (unused = 'eat-me' signal)
        4. Verbatim-only status (faster decay)

        Args:
            memory: Memory to evaluate

        Returns:
            True if should be pruned (forgotten)
        """

        if not self.enable_decay:
            return False

        # Already pruned or unlearned
        if memory.status in [MemoryStatus.PRUNED, MemoryStatus.UNLEARNED]:
            return False

        # Get base decay period
        decay_period = self.decay_periods.get(memory.salience)

        # Protected memories never decay (EWC-style)
        if decay_period is None:
            return False

        # Calculate effective decay period with modifiers
        effective_decay = decay_period

        # Modifier 1: Verbatim-only memories decay faster
        # Research: "Verbatim traces become inaccessible at faster rate"
        if memory.is_verbatim_only():
            effective_decay = timedelta(
                seconds=decay_period.total_seconds() * self.verbatim_decay_multiplier
            )
            logger.debug(f"Memory {memory.engram_id[:8]} is verbatim-only, accelerated decay")

        # Modifier 2: Unused memories decay faster
        # Research: "Lack of retrieval signals = synaptic weakness"
        if memory.access_count == 0:
            effective_decay = timedelta(
                seconds=effective_decay.total_seconds() * self.unused_multiplier
            )
            logger.debug(f"Memory {memory.engram_id[:8]} never accessed, accelerated decay")

        # Check age
        age = datetime.now() - memory.created_at
        should_prune = age > effective_decay

        if should_prune:
            logger.debug(
                f"Memory {memory.engram_id[:8]} marked for pruning: "
                f"age={age.days}d, threshold={effective_decay.days}d, "
                f"salience={memory.salience.name}"
            )

        return should_prune

    def prune_batch(self, memories: List[Memory]) -> Dict[str, int]:
        """
        Prune memories in batch (simulates sleep cycle cleanup)

        Research: "Sleep is to take out the garbage" - REM and SWS
        perform targeted memory cleanup

        Args:
            memories: List of memories to evaluate

        Returns:
            Statistics dictionary with pruning counts per salience level
        """

        if not self.enable_decay:
            logger.info("Decay disabled, no pruning performed")
            return {}

        stats = {
            "total_evaluated": len(memories),
            "pruned": 0,
            "by_salience": {level.name: 0 for level in SalienceLevel}
        }

        for memory in memories:
            if self.should_prune(memory):
                # Mark as pruned (research: synaptic pruning)
                memory.status = MemoryStatus.PRUNED
                stats["pruned"] += 1
                stats["by_salience"][memory.salience.name] += 1

        logger.info(
            f"Passive decay cycle complete: {stats['pruned']}/{stats['total_evaluated']} "
            f"memories pruned"
        )

        return stats

    def get_decay_info(self, memory: Memory) -> Dict:
        """
        Get detailed decay information for a memory

        Returns human-readable decay status
        """

        decay_period = self.decay_periods.get(memory.salience)

        if decay_period is None:
            return {
                "will_decay": False,
                "reason": "Protected memory (CRITICAL salience)",
                "time_remaining": "Never"
            }

        effective_decay = decay_period

        # Apply modifiers
        if memory.is_verbatim_only():
            effective_decay = timedelta(
                seconds=decay_period.total_seconds() * self.verbatim_decay_multiplier
            )

        if memory.access_count == 0:
            effective_decay = timedelta(
                seconds=effective_decay.total_seconds() * self.unused_multiplier
            )

        age = datetime.now() - memory.created_at
        time_remaining = effective_decay - age

        return {
            "will_decay": True,
            "age_days": age.days,
            "decay_threshold_days": effective_decay.days,
            "time_remaining_days": max(0, time_remaining.days),
            "is_overdue": time_remaining.days < 0,
            "modifiers": {
                "verbatim_only": memory.is_verbatim_only(),
                "unused": memory.access_count == 0
            }
        }
