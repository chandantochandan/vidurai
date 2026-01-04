"""
Dream Cycle - Offline RL Training Loop

The Awakening's learning brain.
Processes archived memories with outcomes to train the RL agent.

Glass Box Protocol: Dream Cycle Safety
- Runs in background thread
- Must capture ALL exceptions (never kill main Daemon)
- Wrap entire run() in try/except

Philosophy:
"Dreams are where we consolidate memories into wisdom"

@version 2.1.0-Guardian
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger


# =============================================================================
# DREAM CYCLE
# =============================================================================

class DreamCycle:
    """
    Offline training loop for the RL Agent.

    Uses archived memories with outcomes to train the Q-learning agent.
    Runs in background without blocking the daemon.

    Glass Box Protocol: Dream Cycle Safety
    - All exceptions captured
    - Never crashes the daemon
    - Logs all errors for debugging

    Usage:
        dreamer = DreamCycle()
        stats = dreamer.run()  # Process archived training data
        print(f"Trained on {stats['episodes']} episodes")
    """

    def __init__(
        self,
        batch_size: int = 100,
        max_episodes: int = 1000
    ):
        """
        Initialize DreamCycle.

        Args:
            batch_size: Number of memories to process per batch
            max_episodes: Maximum training episodes per run
        """
        self.batch_size = batch_size
        self.max_episodes = max_episodes
        self.last_run: Optional[datetime] = None

        logger.debug("DreamCycle initialized")

    def run(self) -> Dict[str, Any]:
        """
        Execute one dream cycle (offline training).

        Glass Box Protocol: Dream Cycle Safety
        - Entire method wrapped in try/except
        - Never raises exceptions to caller
        - Returns stats dict even on error

        Returns:
            Dict with training statistics
        """
        stats = {
            'success': False,
            'episodes': 0,
            'positive_rewards': 0,
            'negative_rewards': 0,
            'total_reward': 0.0,
            'error': None,
            'started_at': datetime.now().isoformat(),
            'completed_at': None,
        }

        try:
            # Import dependencies (lazy loading)
            from vidurai.core.analytics import RepoAnalyst
            from vidurai.core.rl_agent_v2 import (
                VismritiRLAgent,
                MemoryState,
                Outcome,
                Action,
                RewardProfile
            )

            logger.info("[DreamCycle] Starting offline training...")

            # Get training data from archive
            analyst = RepoAnalyst()
            training_data = analyst.get_training_data(limit=self.max_episodes)

            if not training_data:
                logger.info("[DreamCycle] No training data available")
                stats['success'] = True
                stats['completed_at'] = datetime.now().isoformat()
                self.last_run = datetime.now()
                return stats

            logger.info(f"[DreamCycle] Found {len(training_data)} training samples")

            # Get or create RL agent
            # Note: We create a new agent instance for training
            # The daemon's agent should be updated separately
            agent = VismritiRLAgent(reward_profile=RewardProfile.BALANCED)

            # Process each memory with outcome
            for memory in training_data:
                try:
                    # Extract fields - EXPLICIT TYPE CAST to prevent str > float errors
                    raw_outcome = memory.get('outcome', 0)
                    outcome_value = int(raw_outcome) if raw_outcome is not None else 0
                    if outcome_value == 0:
                        continue  # Skip neutral outcomes

                    # Create a synthetic state from memory metadata
                    state = self._create_state_from_memory(memory)
                    next_state = self._create_next_state(state, outcome_value)

                    # Determine action that led to this outcome
                    # (In real usage, this would be logged; here we infer)
                    action = self._infer_action(memory)

                    # Create outcome
                    outcome = Outcome(
                        action=action,
                        tokens_saved=0,  # Not tracked in archive
                        retrieval_accuracy=1.0 if outcome_value > 0 else 0.5,
                        information_loss=0.0 if outcome_value > 0 else 0.3,
                        user_satisfaction=1.0 if outcome_value > 0 else 0.0,
                    )

                    # Set up agent state for learning
                    agent.current_state = state
                    agent.current_action = action

                    # Learn from this experience
                    agent.learn(outcome, next_state)

                    # Update stats
                    stats['episodes'] += 1
                    reward = outcome.calculate_reward(agent.reward_profile)
                    stats['total_reward'] += reward

                    if outcome_value > 0:
                        stats['positive_rewards'] += 1
                    else:
                        stats['negative_rewards'] += 1

                except Exception as e:
                    # Glass Box: Capture individual episode errors
                    logger.debug(f"[DreamCycle] Episode error (non-fatal): {e}")
                    continue

            # End training episode
            agent.end_episode()

            # Save updated Q-table
            agent.policy.save_q_table()

            stats['success'] = True
            logger.info(
                f"[DreamCycle] Training complete: {stats['episodes']} episodes, "
                f"reward={stats['total_reward']:.2f}"
            )

        except ImportError as e:
            # Missing dependencies
            stats['error'] = f"Missing dependency: {e}"
            logger.warning(f"[DreamCycle] Import error: {e}")

        except Exception as e:
            # Glass Box: Dream Cycle Safety - catch ALL exceptions
            stats['error'] = str(e)
            logger.error(f"[DreamCycle] Error (daemon safe): {e}")

        finally:
            stats['completed_at'] = datetime.now().isoformat()
            self.last_run = datetime.now()

        return stats

    def _create_state_from_memory(self, memory: Dict[str, Any]) -> 'MemoryState':
        """
        Create a MemoryState from archived memory data.

        Since we don't have full state snapshots in archive,
        we create a reasonable approximation.
        """
        from vidurai.core.rl_agent_v2 import MemoryState

        # Estimate tokens from verbatim content
        verbatim = memory.get('verbatim', '') or ''
        gist = memory.get('gist', '') or ''
        tokens = (len(verbatim) + len(gist)) // 4  # Rough estimate

        # Map salience string to float importance
        salience_map = {
            'critical': 1.0,
            'high': 0.8,
            'medium': 0.5,
            'low': 0.3,
            'noise': 0.1,
        }
        salience_str = memory.get('salience', 'medium') or 'medium'
        importance = salience_map.get(salience_str.lower(), 0.5)

        return MemoryState(
            working_memory_count=10,  # Default
            episodic_memory_count=100,  # Default
            total_tokens=tokens,
            average_entropy=0.5,  # Unknown
            average_importance=importance,
            messages_since_last_compression=5,  # Default
        )

    def _create_next_state(
        self,
        state: 'MemoryState',
        outcome: int
    ) -> 'MemoryState':
        """
        Create next state based on outcome.

        Positive outcome: Memory was useful (system improved)
        Negative outcome: Memory caused issues (system should adapt)
        """
        from vidurai.core.rl_agent_v2 import MemoryState

        # Adjust state based on outcome
        if outcome > 0:
            # Positive: System improved
            return MemoryState(
                working_memory_count=max(1, state.working_memory_count - 2),
                episodic_memory_count=state.episodic_memory_count + 1,
                total_tokens=max(100, state.total_tokens - 50),
                average_entropy=state.average_entropy,
                average_importance=min(1.0, state.average_importance + 0.1),
                messages_since_last_compression=0,
            )
        else:
            # Negative: System should adapt
            return MemoryState(
                working_memory_count=state.working_memory_count + 2,
                episodic_memory_count=state.episodic_memory_count,
                total_tokens=state.total_tokens + 50,
                average_entropy=state.average_entropy,
                average_importance=max(0.0, state.average_importance - 0.1),
                messages_since_last_compression=state.messages_since_last_compression + 1,
            )

    def _infer_action(self, memory: Dict[str, Any]) -> 'Action':
        """
        Infer what action led to this memory being archived.

        In real usage, actions would be logged with memories.
        Here we make reasonable inferences.
        """
        from vidurai.core.rl_agent_v2 import Action

        # EXPLICIT TYPE CAST - outcome may be str from DuckDB
        raw_outcome = memory.get('outcome', 0)
        outcome = int(raw_outcome) if raw_outcome is not None else 0

        # Salience is stored as string ('critical', 'high', etc.)
        # Convert to numeric importance for comparison
        salience_map = {
            'critical': 1.0,
            'high': 0.8,
            'medium': 0.5,
            'low': 0.3,
            'noise': 0.1,
        }
        salience_str = memory.get('salience', 'medium') or 'medium'
        salience = salience_map.get(str(salience_str).lower(), 0.5)

        raw_access = memory.get('access_count', 0)
        access_count = int(raw_access) if raw_access is not None else 0

        # High salience + positive outcome = compression worked well
        if salience > 0.7 and outcome > 0:
            return Action.COMPRESS_CONSERVATIVE

        # Low salience + archived = decay was appropriate
        if salience < 0.3:
            return Action.DECAY_LOW_VALUE

        # Default: some form of compression
        return Action.COMPRESS_NOW

    def get_last_run(self) -> Optional[datetime]:
        """Get timestamp of last run."""
        return self.last_run


# =============================================================================
# MODULE-LEVEL CONVENIENCE
# =============================================================================

_default_dreamer: Optional[DreamCycle] = None


def get_dreamer(
    batch_size: int = 100,
    max_episodes: int = 1000
) -> DreamCycle:
    """Get or create the default DreamCycle instance."""
    global _default_dreamer
    if _default_dreamer is None:
        _default_dreamer = DreamCycle(
            batch_size=batch_size,
            max_episodes=max_episodes
        )
    return _default_dreamer


def run_dream_cycle() -> Dict[str, Any]:
    """Convenience function to run dream cycle."""
    return get_dreamer().run()


# =============================================================================
# CLI TEST INTERFACE
# =============================================================================

def _test_cli():
    """
    Test function for manual verification.

    Usage:
        python -m vidurai.core.rl.dreamer --test
    """
    import argparse

    parser = argparse.ArgumentParser(description="Dream Cycle Test")
    parser.add_argument("--test", action="store_true", help="Run test cases")
    parser.add_argument("--run", action="store_true", help="Run dream cycle")

    args = parser.parse_args()

    if args.run:
        print("\n[DreamCycle] Running offline training...")
        dreamer = DreamCycle()
        stats = dreamer.run()
        print(f"\n=== Dream Cycle Results ===")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        return

    if args.test:
        print("\n=== Dream Cycle Test Cases ===\n")

        # Test 1: Create dreamer
        try:
            d = DreamCycle()
            print("[PASS] Create dreamer")
        except Exception as e:
            print(f"[FAIL] Create dreamer: {e}")
            return

        # Test 2: Run (should not crash even with no data)
        try:
            stats = d.run()
            print(f"[PASS] Run dream cycle: success={stats['success']}")
            if stats['error']:
                print(f"       Error: {stats['error']}")
        except Exception as e:
            print(f"[FAIL] Run dream cycle (should never raise): {e}")

        # Test 3: Get last run
        try:
            last = d.get_last_run()
            print(f"[PASS] Get last run: {last}")
        except Exception as e:
            print(f"[FAIL] Get last run: {e}")

        print()


if __name__ == "__main__":
    _test_cli()
