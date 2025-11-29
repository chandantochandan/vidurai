"""
Retention Policy Layer
Provides abstraction for memory retention decisions

Philosophy: "Intelligence can be explicit (rules) or emergent (learning)"
विस्मृति भी विद्या है (Forgetting too is knowledge)

This module defines the interface between memory storage and decision-making,
allowing both rule-based and RL-based policies to coexist.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger("vidurai.retention_policy")


class RetentionAction(Enum):
    """
    Actions that can be taken on memory system

    These map to actual operations in VismritiMemory:
    - DO_NOTHING: Skip compression/consolidation this cycle
    - COMPRESS_LIGHT: Run semantic consolidation (normal mode)
    - COMPRESS_AGGRESSIVE: Run consolidation with lower thresholds
    - DECAY_LOW_VALUE: Trigger decay on LOW/NOISE memories
    - CONSOLIDATE_AND_DECAY: Both consolidation and decay together
    """
    DO_NOTHING = "do_nothing"
    COMPRESS_LIGHT = "compress_light"
    COMPRESS_AGGRESSIVE = "compress_aggressive"
    DECAY_LOW_VALUE = "decay_low_value"
    CONSOLIDATE_AND_DECAY = "consolidate_and_decay"


@dataclass
class RetentionContext:
    """
    Context for retention decisions

    This is passed to the policy to help it decide what action to take.
    Contains metrics about current memory state.
    """
    # Memory counts
    total_memories: int
    high_salience_count: int
    medium_salience_count: int
    low_salience_count: int
    noise_salience_count: int

    # Age metrics
    avg_age_days: float
    oldest_memory_days: float

    # Size metrics
    total_size_mb: float
    estimated_tokens: int

    # Activity metrics
    memories_added_last_day: int
    memories_accessed_last_day: int

    # Project context
    project_path: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/debugging"""
        return {
            'total_memories': self.total_memories,
            'high_salience': self.high_salience_count,
            'medium_salience': self.medium_salience_count,
            'low_salience': self.low_salience_count,
            'noise_salience': self.noise_salience_count,
            'avg_age_days': round(self.avg_age_days, 1),
            'oldest_memory_days': round(self.oldest_memory_days, 1),
            'total_size_mb': round(self.total_size_mb, 2),
            'estimated_tokens': self.estimated_tokens,
            'memories_added_last_day': self.memories_added_last_day,
            'memories_accessed_last_day': self.memories_accessed_last_day,
        }


@dataclass
class RetentionOutcome:
    """
    Result of executing a retention action

    Used for learning (in RL policy) and logging.
    """
    action: RetentionAction
    memories_before: int
    memories_after: int
    tokens_saved: int
    consolidations_performed: int
    decays_performed: int
    errors_encountered: int
    execution_time_ms: float

    @property
    def compression_ratio(self) -> float:
        """Calculate compression ratio (0.0 = no compression, 0.9 = 90% reduction)"""
        if self.memories_before == 0:
            return 0.0
        return 1.0 - (self.memories_after / self.memories_before)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        return {
            'action': self.action.value,
            'memories_before': self.memories_before,
            'memories_after': self.memories_after,
            'compression_ratio': round(self.compression_ratio, 3),
            'tokens_saved': self.tokens_saved,
            'consolidations': self.consolidations_performed,
            'decays': self.decays_performed,
            'errors': self.errors_encountered,
            'execution_time_ms': round(self.execution_time_ms, 2),
        }


class RetentionPolicy(ABC):
    """
    Abstract interface for memory retention policies

    Implementations:
    - RuleBasedPolicy: Uses explicit rules (current behavior)
    - RLPolicy: Uses reinforcement learning (VismritiRLAgent)

    The policy decides WHEN and HOW to compress/decay memories.
    """

    @abstractmethod
    def decide_action(self, context: RetentionContext) -> RetentionAction:
        """
        Decide what retention action to take

        Args:
            context: Current state of memory system

        Returns:
            Action to execute
        """
        pass

    @abstractmethod
    def learn_from_outcome(
        self,
        context: RetentionContext,
        action: RetentionAction,
        outcome: RetentionOutcome
    ):
        """
        Learn from the outcome of an action

        For rule-based policies, this is a no-op.
        For RL policies, this updates the Q-table.

        Args:
            context: Context when action was taken
            action: Action that was executed
            outcome: Result of the action
        """
        pass

    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about policy performance

        Returns:
            Dictionary with policy-specific stats
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable policy name"""
        pass


class RuleBasedPolicy(RetentionPolicy):
    """
    Rule-based retention policy (current behavior)

    Philosophy: "Explicit wisdom from human design"

    Rules:
    1. If >100 LOW/NOISE memories → CONSOLIDATE_AND_DECAY
    2. If >500 total memories → COMPRESS_LIGHT
    3. If >1000 total memories → COMPRESS_AGGRESSIVE
    4. If oldest memory >90 days → DECAY_LOW_VALUE
    5. Otherwise → DO_NOTHING

    This is deterministic and doesn't learn.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize rule-based policy

        Args:
            config: Optional configuration dict with thresholds
        """
        self.config = config or {}

        # Thresholds (can be overridden via config)
        self.low_noise_threshold = self.config.get('low_noise_threshold', 100)
        self.compress_light_threshold = self.config.get('compress_light_threshold', 500)
        self.compress_aggressive_threshold = self.config.get('compress_aggressive_threshold', 1000)
        self.decay_age_threshold_days = self.config.get('decay_age_threshold_days', 90)

        # Statistics
        self.actions_taken = 0
        self.action_counts = {action: 0 for action in RetentionAction}

        logger.info(f"Rule-based policy initialized with thresholds: "
                   f"low_noise={self.low_noise_threshold}, "
                   f"compress_light={self.compress_light_threshold}, "
                   f"compress_aggressive={self.compress_aggressive_threshold}")

    def decide_action(self, context: RetentionContext) -> RetentionAction:
        """
        Apply rules to decide action

        Priorities (checked in order):
        1. Too many low-value memories → consolidate and decay
        2. Memory count very high → aggressive compression
        3. Memory count high → light compression
        4. Old memories present → decay
        5. Otherwise → do nothing
        """
        self.actions_taken += 1

        # Rule 1: Too many LOW/NOISE memories
        low_noise_count = context.low_salience_count + context.noise_salience_count
        if low_noise_count > self.low_noise_threshold:
            action = RetentionAction.CONSOLIDATE_AND_DECAY
            logger.debug(f"Rule 1 triggered: {low_noise_count} LOW/NOISE memories > {self.low_noise_threshold}")

        # Rule 2: Very high memory count
        elif context.total_memories > self.compress_aggressive_threshold:
            action = RetentionAction.COMPRESS_AGGRESSIVE
            logger.debug(f"Rule 2 triggered: {context.total_memories} memories > {self.compress_aggressive_threshold}")

        # Rule 3: High memory count
        elif context.total_memories > self.compress_light_threshold:
            action = RetentionAction.COMPRESS_LIGHT
            logger.debug(f"Rule 3 triggered: {context.total_memories} memories > {self.compress_light_threshold}")

        # Rule 4: Old memories need decay
        elif context.oldest_memory_days > self.decay_age_threshold_days:
            action = RetentionAction.DECAY_LOW_VALUE
            logger.debug(f"Rule 4 triggered: oldest memory {context.oldest_memory_days}d > {self.decay_age_threshold_days}d")

        # Rule 5: Everything is fine
        else:
            action = RetentionAction.DO_NOTHING
            logger.debug("No rules triggered, doing nothing")

        # Track statistics
        self.action_counts[action] += 1

        return action

    def learn_from_outcome(
        self,
        context: RetentionContext,
        action: RetentionAction,
        outcome: RetentionOutcome
    ):
        """
        No-op for rule-based policy (doesn't learn)
        """
        # Rule-based policies are static
        pass

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about rule applications"""
        return {
            'policy': 'rule_based',
            'actions_taken': self.actions_taken,
            'action_counts': {action.value: count for action, count in self.action_counts.items()},
            'thresholds': {
                'low_noise': self.low_noise_threshold,
                'compress_light': self.compress_light_threshold,
                'compress_aggressive': self.compress_aggressive_threshold,
                'decay_age_days': self.decay_age_threshold_days,
            }
        }

    @property
    def name(self) -> str:
        return "Rule-Based Policy"


class RLPolicy(RetentionPolicy):
    """
    RL-based retention policy (learning from experience)

    Philosophy: "Wisdom emerges from experience, not just rules"

    This wraps VismritiRLAgent and translates between:
    - RetentionContext ↔ MemoryState
    - RetentionAction ↔ Action
    - RetentionOutcome ↔ Outcome

    The RL agent learns optimal policies over time.
    """

    def __init__(
        self,
        reward_profile: str = "BALANCED",
        storage_dir: str = "~/.vidurai"
    ):
        """
        Initialize RL-based policy

        Args:
            reward_profile: BALANCED, COST_FOCUSED, or QUALITY_FOCUSED
            storage_dir: Where to store Q-table and experiences
        """
        try:
            from .rl_agent_v2 import VismritiRLAgent, RewardProfile, Action

            # Convert string to enum
            profile_map = {
                'BALANCED': RewardProfile.BALANCED,
                'COST_FOCUSED': RewardProfile.COST_FOCUSED,
                'QUALITY_FOCUSED': RewardProfile.QUALITY_FOCUSED,
            }
            profile = profile_map.get(reward_profile.upper(), RewardProfile.BALANCED)

            # Initialize RL agent
            self.agent = VismritiRLAgent(
                reward_profile=profile,
                storage_dir=storage_dir
            )

            # Store mapping classes
            self.Action = Action

            # Current state tracking
            self.last_context: Optional[RetentionContext] = None
            self.last_action: Optional[RetentionAction] = None

            logger.info(f"RL policy initialized with reward profile: {reward_profile}")

        except ImportError as e:
            logger.error(f"Failed to initialize RL policy: {e}")
            raise RuntimeError("RL agent not available. Install required dependencies or use RuleBasedPolicy.")

    def decide_action(self, context: RetentionContext) -> RetentionAction:
        """
        Use RL agent to decide action

        Converts RetentionContext → MemoryState, asks agent, converts back.
        """
        from .rl_agent_v2 import MemoryState

        # Convert RetentionContext to MemoryState
        # Note: RL agent expects "working" and "episodic" memory counts
        # We map high/critical as "working", rest as "episodic"
        memory_state = MemoryState(
            working_memory_count=context.high_salience_count,
            episodic_memory_count=context.total_memories - context.high_salience_count,
            total_tokens=context.estimated_tokens,
            average_entropy=0.5,  # Not tracked in context, use neutral value
            average_importance=context.high_salience_count / max(context.total_memories, 1),
            messages_since_last_compression=context.memories_added_last_day,
        )

        # Ask RL agent for action
        rl_action = self.agent.decide(memory_state)

        # Convert RL Action to RetentionAction
        retention_action = self._map_rl_to_retention_action(rl_action)

        # Store for learning
        self.last_context = context
        self.last_action = retention_action

        logger.debug(f"RL agent decided: {rl_action.value} → {retention_action.value}")

        return retention_action

    def learn_from_outcome(
        self,
        context: RetentionContext,
        action: RetentionAction,
        outcome: RetentionOutcome
    ):
        """
        Update RL agent with outcome

        Converts RetentionOutcome → Outcome, updates Q-table.
        """
        from .rl_agent_v2 import MemoryState, Outcome

        if self.last_context is None:
            logger.warning("Cannot learn: no previous context stored")
            return

        # Convert outcome to RL format
        rl_outcome = Outcome(
            action=self._map_retention_to_rl_action(action),
            tokens_saved=outcome.tokens_saved,
            retrieval_accuracy=1.0 - (outcome.errors_encountered / max(outcome.memories_before, 1)),
            information_loss=outcome.compression_ratio * 0.1,  # Estimate
            user_satisfaction=0.8 if outcome.errors_encountered == 0 else 0.5,
        )

        # Convert new context to MemoryState
        next_state = MemoryState(
            working_memory_count=context.high_salience_count,
            episodic_memory_count=context.total_memories - context.high_salience_count,
            total_tokens=context.estimated_tokens,
            average_entropy=0.5,
            average_importance=context.high_salience_count / max(context.total_memories, 1),
            messages_since_last_compression=0,  # Just compressed
        )

        # Learn
        self.agent.learn(rl_outcome, next_state)

        logger.debug(f"RL agent learned from outcome: reward={rl_outcome.calculate_reward(self.agent.reward_profile):.2f}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get RL agent statistics"""
        stats = self.agent.get_statistics()
        stats['policy'] = 'rl_based'
        return stats

    @property
    def name(self) -> str:
        return f"RL Policy ({self.agent.reward_profile.value})"

    def _map_rl_to_retention_action(self, rl_action) -> RetentionAction:
        """
        Map RL Action to RetentionAction

        RL Agent Actions → Retention Actions:
        - COMPRESS_NOW → COMPRESS_LIGHT
        - COMPRESS_AGGRESSIVE → COMPRESS_AGGRESSIVE
        - DECAY_LOW_VALUE → DECAY_LOW_VALUE
        - CONSOLIDATE → CONSOLIDATE_AND_DECAY
        - DO_NOTHING → DO_NOTHING
        """
        mapping = {
            'compress_now': RetentionAction.COMPRESS_LIGHT,
            'compress_aggressive': RetentionAction.COMPRESS_AGGRESSIVE,
            'decay_low_value': RetentionAction.DECAY_LOW_VALUE,
            'consolidate': RetentionAction.CONSOLIDATE_AND_DECAY,
            'do_nothing': RetentionAction.DO_NOTHING,
        }

        return mapping.get(rl_action.value, RetentionAction.DO_NOTHING)

    def _map_retention_to_rl_action(self, retention_action: RetentionAction):
        """
        Map RetentionAction back to RL Action (for learning)
        """
        reverse_mapping = {
            RetentionAction.COMPRESS_LIGHT: self.Action.COMPRESS_NOW,
            RetentionAction.COMPRESS_AGGRESSIVE: self.Action.COMPRESS_AGGRESSIVE,
            RetentionAction.DECAY_LOW_VALUE: self.Action.DECAY_LOW_VALUE,
            RetentionAction.CONSOLIDATE_AND_DECAY: self.Action.CONSOLIDATE,
            RetentionAction.DO_NOTHING: self.Action.DO_NOTHING,
        }

        return reverse_mapping.get(retention_action, self.Action.DO_NOTHING)


# Factory function for easy initialization
def create_retention_policy(
    policy_type: str = "rule_based",
    **kwargs
) -> RetentionPolicy:
    """
    Factory function to create retention policies

    Args:
        policy_type: "rule_based" or "rl_based"
        **kwargs: Policy-specific configuration

    Returns:
        RetentionPolicy instance

    Example:
        # Rule-based policy
        policy = create_retention_policy('rule_based', low_noise_threshold=50)

        # RL-based policy
        policy = create_retention_policy('rl_based', reward_profile='COST_FOCUSED')
    """
    if policy_type == "rule_based":
        return RuleBasedPolicy(config=kwargs)
    elif policy_type == "rl_based":
        return RLPolicy(
            reward_profile=kwargs.get('reward_profile', 'BALANCED'),
            storage_dir=kwargs.get('storage_dir', '~/.vidurai')
        )
    else:
        raise ValueError(f"Unknown policy type: {policy_type}. Use 'rule_based' or 'rl_based'")
