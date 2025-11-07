"""
Vidurai v2.0 - Module 4: Reinforcement Learning Agent
The learning brain of Vismriti

Philosophy:
"From youthful exploration to mature wisdom, through experience"
"""
import math
import random
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from collections import defaultdict


class Action(Enum):
    """
    All actions the RL agent can take
    """
    # Compression actions
    COMPRESS_NOW = "compress_now"
    COMPRESS_AGGRESSIVE = "compress_aggressive"
    COMPRESS_CONSERVATIVE = "compress_conservative"
    
    # Decay actions
    DECAY_LOW_VALUE = "decay_low_value"
    DECAY_THRESHOLD_HIGH = "decay_high"
    DECAY_THRESHOLD_LOW = "decay_low"
    
    # Consolidation (future)
    CONSOLIDATE = "consolidate"
    
    # Wait
    DO_NOTHING = "do_nothing"


class RewardProfile(Enum):
    """
    User-defined priorities for the reward function
    Allows end-users to tune behavior
    """
    BALANCED = "balanced"
    COST_FOCUSED = "cost_focused"
    QUALITY_FOCUSED = "quality_focused"


@dataclass
class MemoryState:
    """
    Snapshot of memory system state
    What the RL agent observes before making decisions
    """
    # Memory metrics
    working_memory_count: int
    episodic_memory_count: int
    total_tokens: int
    
    # Quality metrics
    average_entropy: float = 0.5
    average_importance: float = 0.5
    
    # Context
    messages_since_last_compression: int = 0
    time_since_last_action: float = 0.0
    
    # Recent performance
    recent_compressions: int = 0
    recent_decays: int = 0
    
    def to_hash(self) -> str:
        """
        Create discrete state hash for Q-table
        Bucketize continuous values for generalization
        """
        # Discretize values into buckets
        wm_bucket = min(self.working_memory_count // 5, 10)  # 0-50 in steps of 5
        em_bucket = min(self.episodic_memory_count // 100, 10)
        token_bucket = min(self.total_tokens // 500, 20)
        
        entropy_bucket = int(self.average_entropy * 10)  # 0-10
        importance_bucket = int(self.average_importance * 10)
        
        msg_bucket = min(self.messages_since_last_compression // 3, 5)
        
        return f"{wm_bucket}|{em_bucket}|{token_bucket}|{entropy_bucket}|{importance_bucket}|{msg_bucket}"


@dataclass
class Outcome:
    """
    Result of an action (what the agent learns from)
    """
    action: Action
    tokens_saved: int = 0
    retrieval_accuracy: float = 1.0  # 0-1
    information_loss: float = 0.0     # 0-1
    user_satisfaction: float = 0.5    # 0-1
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def calculate_reward(self, profile: RewardProfile) -> float:
        """
        Calculate reward based on outcome and user's priority profile
        """
        weights = RewardFunction.PROFILES[profile]

        # 1. Token savings (cost reduction)
        # BUGFIX: Removed tiny pricing multiplier, use direct token count with scaling
        token_reward = (self.tokens_saved / 10) * weights['token_weight']

        # 2. Retrieval accuracy (quality)
        quality_reward = self.retrieval_accuracy * 50 * weights['quality_weight']

        # 3. Information loss penalty
        loss_penalty = self.information_loss * 100 * weights['loss_penalty']

        # 4. User satisfaction bonus
        satisfaction_bonus = self.user_satisfaction * 30

        total_reward = token_reward + quality_reward - loss_penalty + satisfaction_bonus

        return total_reward


@dataclass
class Experience:
    """
    One learning experience: (state, action, reward, next_state)
    The fundamental unit of learning
    """
    state: MemoryState
    action: Action
    reward: float
    next_state: MemoryState
    timestamp: datetime = None
    
    # Additional metadata
    outcome: Optional[Outcome] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class RewardFunction:
    """
    Configurable reward calculation
    Users can choose their priority: cost vs. quality
    """
    
    PROFILES = {
        RewardProfile.BALANCED: {
            'token_weight': 1.0,
            'quality_weight': 1.0,
            'loss_penalty': 2.0,
        },
        RewardProfile.COST_FOCUSED: {
            'token_weight': 3.0,  # BUGFIX: Increased to properly favor token savings
            'quality_weight': 0.5,
            'loss_penalty': 0.5,  # BUGFIX: Decreased to tolerate more information loss
        },
        RewardProfile.QUALITY_FOCUSED: {
            'token_weight': 0.3,  # BUGFIX: Decreased to de-prioritize cost savings
            'quality_weight': 2.0,
            'loss_penalty': 5.0,  # BUGFIX: Increased to strongly penalize information loss
        }
    }


class ExperienceBuffer:
    """
    Stores experiences for learning
    File-based storage (JSONL format)
    
    Philosophy: "Memory of memories"
    """
    
    def __init__(self, max_size: int = 10000, storage_dir: str = "~/.vidurai"):
        self.max_size = max_size
        self.storage_path = Path(storage_dir).expanduser() / "experiences.jsonl"
        self.buffer: List[Experience] = []
        
        # Create storage directory
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing experiences
        self.load_from_disk()
    
    def add(self, experience: Experience):
        """Add experience to buffer and persist"""
        self.buffer.append(experience)
        
        # Maintain max size
        if len(self.buffer) > self.max_size:
            self.buffer.pop(0)
        
        # Persist to disk
        self._save_experience(experience)
    
    def sample(self, batch_size: int = 32) -> List[Experience]:
        """Sample random batch for learning"""
        if len(self.buffer) < batch_size:
            return self.buffer.copy()
        return random.sample(self.buffer, batch_size)
    
    def _save_experience(self, exp: Experience):
        """Append experience to JSONL file"""
        data = {
            'state': asdict(exp.state),
            'action': exp.action.value,
            'reward': exp.reward,
            'next_state': asdict(exp.next_state),
            'timestamp': exp.timestamp.isoformat(),
        }
        
        with open(self.storage_path, 'a') as f:
            f.write(json.dumps(data) + '\n')
    
    def load_from_disk(self):
        """Load past experiences from disk"""
        if not self.storage_path.exists():
            return
        
        try:
            with open(self.storage_path, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    data = json.loads(line)
                    
                    # Reconstruct experience
                    exp = Experience(
                        state=MemoryState(**data['state']),
                        action=Action(data['action']),
                        reward=data['reward'],
                        next_state=MemoryState(**data['next_state']),
                        timestamp=datetime.fromisoformat(data['timestamp'])
                    )
                    
                    self.buffer.append(exp)
                    
                    # Don't exceed max size
                    if len(self.buffer) >= self.max_size:
                        break
        
        except Exception as e:
            print(f"Warning: Could not load experiences: {e}")


class QLearningPolicy:
    """
    Q-Learning Policy with decaying epsilon
    
    Philosophy:
    "From youthful exploration to mature exploitation"
    
    Q(s,a) ← Q(s,a) + α[r + γ·max Q(s',a') - Q(s,a)]
    """
    
    def __init__(
        self,
        epsilon_max: float = 0.3,
        epsilon_min: float = 0.05,
        epsilon_decay: float = 0.003,
        alpha: float = 0.1,
        gamma: float = 0.9,
        storage_dir: str = "~/.vidurai"
    ):
        """
        Initialize Q-learning policy
        
        Args:
            epsilon_max: Initial exploration rate (youth)
            epsilon_min: Final exploration rate (maturity)
            epsilon_decay: How quickly to mature
            alpha: Learning rate
            gamma: Discount factor (future rewards)
        """
        self.epsilon_max = epsilon_max
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.alpha = alpha
        self.gamma = gamma
        
        # Q-table: state_hash → action → expected_reward
        # NOTE: Using regular dict instead of defaultdict for pickle compatibility
        self.q_table: Dict[str, Dict[Action, float]] = {}
        
        # Learning statistics
        self.episodes = 0
        self.total_reward = 0.0
        
        # Storage
        self.storage_path = Path(storage_dir).expanduser() / "q_table.json"
        self.load_q_table()

    def _get_or_create_state(self, state_hash: str) -> Dict[Action, float]:
        """
        Get Q-values for a state, creating empty dict if needed.

        This replaces the defaultdict pattern to enable pickle serialization.
        Lambda functions in defaultdict prevent pickling, so we use explicit
        dict creation instead.

        Args:
            state_hash: Discretized state identifier from MemoryState.to_hash()

        Returns:
            Dictionary mapping actions to Q-values for this state
        """
        if state_hash not in self.q_table:
            self.q_table[state_hash] = {}
        return self.q_table[state_hash]

    def get_epsilon(self) -> float:
        """
        Calculate current epsilon (exploration rate)
        Decays exponentially from max to min
        
        ε(t) = ε_min + (ε_max - ε_min) × e^(-λt)
        """
        epsilon = self.epsilon_min + (self.epsilon_max - self.epsilon_min) * \
                  math.exp(-self.epsilon_decay * self.episodes)
        return epsilon
    
    def select_action(self, state: MemoryState) -> Action:
        """
        ε-greedy action selection
        Balances exploration and exploitation
        """
        epsilon = self.get_epsilon()
        
        if random.random() < epsilon:
            # Explore: random action
            return random.choice(list(Action))
        else:
            # Exploit: best known action
            return self._best_action(state)
    
    def _best_action(self, state: MemoryState) -> Action:
        """Get action with highest Q-value for state"""
        state_hash = state.to_hash()

        # Use helper method to get or create state entry
        q_values = self._get_or_create_state(state_hash)

        if not q_values:
            return Action.DO_NOTHING  # Default when no learned Q-values

        # Get action with max Q-value
        best_action = max(q_values.items(), key=lambda x: x[1])[0]
        return best_action
    
    def learn(self, experience: Experience):
        """
        Update Q-values from experience

        Q(s,a) ← Q(s,a) + α[r + γ·max Q(s',a') - Q(s,a)]
        """
        state_hash = experience.state.to_hash()
        next_state_hash = experience.next_state.to_hash()

        # Get current Q-value (use helper method for safe access)
        state_q_values = self._get_or_create_state(state_hash)
        current_q = state_q_values.get(experience.action, 0.0)

        # Best future Q-value
        next_q_values = self._get_or_create_state(next_state_hash)
        max_future_q = max(next_q_values.values()) if next_q_values else 0.0

        # Q-learning update
        new_q = current_q + self.alpha * (
            experience.reward + self.gamma * max_future_q - current_q
        )

        # Update Q-table
        state_q_values[experience.action] = new_q

        # Update statistics
        self.total_reward += experience.reward
    
    def end_episode(self):
        """Mark end of episode (triggers epsilon decay)"""
        self.episodes += 1
        
        # Periodically save Q-table
        if self.episodes % 50 == 0:
            self.save_q_table()
    
    def save_q_table(self):
        """Persist Q-table to disk"""
        # Convert to JSON-serializable format
        serializable = {}
        for state_hash, actions in self.q_table.items():
            serializable[state_hash] = {
                action.value: q_value
                for action, q_value in actions.items()
            }
        
        data = {
            'q_table': serializable,
            'episodes': self.episodes,
            'total_reward': self.total_reward,
            'epsilon': self.get_epsilon(),
        }
        
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_q_table(self):
        """Load Q-table from disk"""
        if not self.storage_path.exists():
            return
        
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
            
            # Restore Q-table
            for state_hash, actions in data['q_table'].items():
                for action_str, q_value in actions.items():
                    action = Action(action_str)
                    self.q_table[state_hash][action] = q_value
            
            # Restore statistics
            self.episodes = data.get('episodes', 0)
            self.total_reward = data.get('total_reward', 0.0)
            
            print(f"✅ Loaded Q-table with {len(self.q_table)} states, {self.episodes} episodes")
        
        except Exception as e:
            print(f"Warning: Could not load Q-table: {e}")

    def __getstate__(self):
        """
        Prepare QLearningPolicy for pickling.

        Since we replaced defaultdict with regular dict, the q_table is now
        fully picklable without any modifications. This method documents the
        pickle protocol for clarity and future maintainability.

        Returns:
            Dictionary of serializable state
        """
        return self.__dict__.copy()

    def __setstate__(self, state):
        """
        Restore QLearningPolicy from pickled state.

        Handles edge cases and ensures proper restoration of all attributes.

        Args:
            state: Pickled state dictionary
        """
        self.__dict__.update(state)

        # Ensure storage_path is a Path object (handles edge cases where
        # it might be deserialized as a string in some scenarios)
        if hasattr(self, 'storage_path') and isinstance(self.storage_path, str):
            self.storage_path = Path(self.storage_path)

    def get_statistics(self) -> Dict[str, Any]:
        """Get learning statistics"""
        return {
            'episodes': self.episodes,
            'total_reward': self.total_reward,
            'avg_reward_per_episode': self.total_reward / max(self.episodes, 1),
            'epsilon': self.get_epsilon(),
            'q_table_size': len(self.q_table),
            'maturity': min((self.episodes / 1000) * 100, 100),  # % mature
        }


class VismritiRLAgent:
    """
    The Reinforcement Learning Brain of Vidurai
    
    Philosophy:
    "Intelligence emerges from experience, not from rules"
    
    Learns optimal policies for:
    - When to compress
    - When to decay
    - What thresholds to use
    """
    
    def __init__(
        self,
        reward_profile: RewardProfile = RewardProfile.BALANCED,
        storage_dir: str = "~/.vidurai"
    ):
        """
        Initialize RL Agent
        
        Args:
            reward_profile: User's priority (cost vs. quality)
            storage_dir: Where to store experiences and Q-table
        """
        self.reward_profile = reward_profile
        
        # Core components
        self.policy = QLearningPolicy(storage_dir=storage_dir)
        self.experience_buffer = ExperienceBuffer(storage_dir=storage_dir)
        
        # Current episode state
        self.current_state: Optional[MemoryState] = None
        self.current_action: Optional[Action] = None
        
        # Statistics
        self.actions_taken = 0
        
        print(f"✅ Vismriti RL Agent initialized")
        print(f"   Reward profile: {reward_profile.value}")
        print(f"   Episodes: {self.policy.episodes}")
        print(f"   Epsilon: {self.policy.get_epsilon():.3f}")
    
    def observe(self, memory_system) -> MemoryState:
        """
        Observe current state of memory system
        """
        # Calculate metrics
        total_tokens = sum(
            len(m.content) // 4  # Rough estimate
            for m in memory_system.working.memories
        )
        
        # Calculate average entropy (if Module 2 available)
        avg_entropy = 0.5  # Default
        try:
            from .intelligent_decay_v2 import EntropyCalculator
            entropies = [
                EntropyCalculator.calculate_combined(m.content)
                for m in list(memory_system.working.memories)[:10]
            ]
            avg_entropy = sum(entropies) / len(entropies) if entropies else 0.5
        except:
            pass
        
        # Calculate average importance
        importances = [m.importance for m in memory_system.working.memories]
        avg_importance = sum(importances) / len(importances) if importances else 0.5
        
        # Messages since last compression
        msg_since_compression = getattr(
            memory_system, 
            '_messages_since_compression', 
            len(memory_system.working.memories)
        )
        
        state = MemoryState(
            working_memory_count=len(memory_system.working.memories),
            episodic_memory_count=len(memory_system.episodic.memories),
            total_tokens=total_tokens,
            average_entropy=avg_entropy,
            average_importance=avg_importance,
            messages_since_last_compression=msg_since_compression,
        )
        
        return state
    
    def decide(self, state: MemoryState) -> Action:
        """
        Decide what action to take
        Uses ε-greedy policy
        """
        action = self.policy.select_action(state)
        
        # Store for learning
        self.current_state = state
        self.current_action = action
        self.actions_taken += 1
        
        return action
    
    def learn(self, outcome: Outcome, next_state: MemoryState):
        """
        Learn from outcome of action
        
        Args:
            outcome: Result of the action
            next_state: State after action
        """
        if self.current_state is None or self.current_action is None:
            return
        
        # Calculate reward based on user's priority
        reward = outcome.calculate_reward(self.reward_profile)
        
        # Create experience
        experience = Experience(
            state=self.current_state,
            action=self.current_action,
            reward=reward,
            next_state=next_state,
            outcome=outcome
        )
        
        # Store experience
        self.experience_buffer.add(experience)
        
        # Update policy
        self.policy.learn(experience)
        
        # Reset for next decision
        self.current_state = None
        self.current_action = None
    
    def end_episode(self):
        """Mark end of episode (conversation)"""
        self.policy.end_episode()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        policy_stats = self.policy.get_statistics()
        
        return {
            **policy_stats,
            'reward_profile': self.reward_profile.value,
            'actions_taken': self.actions_taken,
            'experiences_stored': len(self.experience_buffer.buffer),
        }


# Example usage
if __name__ == "__main__":
    print("=" * 70)
    print("🧠 VIDURAI RL AGENT - EXAMPLE")
    print("=" * 70)
    
    # Create agent with balanced profile
    agent = VismritiRLAgent(reward_profile=RewardProfile.BALANCED)
    
    # Simulate a decision cycle
    print("\n📊 Simulating decision cycle...\n")
    
    # 1. Observe state
    state = MemoryState(
        working_memory_count=10,
        episodic_memory_count=100,
        total_tokens=500,
        average_entropy=0.6,
        average_importance=0.7,
        messages_since_last_compression=8
    )
    print(f"State: {state.working_memory_count} working memories, {state.total_tokens} tokens")
    
    # 2. Decide action
    action = agent.decide(state)
    print(f"Decision: {action.value}")
    
    # 3. Simulate outcome
    outcome = Outcome(
        action=action,
        tokens_saved=50,
        retrieval_accuracy=0.95,
        information_loss=0.05,
        user_satisfaction=0.8
    )
    reward = outcome.calculate_reward(RewardProfile.BALANCED)
    print(f"Outcome: saved {outcome.tokens_saved} tokens, reward={reward:.2f}")
    
    # 4. Learn
    next_state = MemoryState(
        working_memory_count=6,
        episodic_memory_count=101,
        total_tokens=300,
        average_entropy=0.6,
        average_importance=0.7,
        messages_since_last_compression=0
    )
    agent.learn(outcome, next_state)
    print(f"Learning: Q-table updated")
    
    # Show statistics
    stats = agent.get_statistics()
    print(f"\n📈 Agent Statistics:")
    print(f"   Episodes: {stats['episodes']}")
    print(f"   Epsilon (exploration rate): {stats['epsilon']:.3f}")
    print(f"   Maturity: {stats['maturity']:.1f}%")
    print(f"   Q-table size: {stats['q_table_size']} states")
    
    print("\n" + "=" * 70)
    print("✅ RL Agent working correctly!")
    print("=" * 70)