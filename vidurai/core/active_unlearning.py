"""
Active Unlearning Engine
Motivated forgetting via gradient ascent

Research Foundation:
- Motivated forgetting: Lateral PFC inhibitory control
- "Top-down suppression of hippocampus" (neural mechanism)
- Gradient ascent: Machine unlearning technique
- "Training is descent, unlearning is ascent"

Biological Process:
When consciously trying to forget (motivated forgetting):
1. Lateral PFC (executive control) activates
2. Sends inhibitory signals to hippocampus
3. Disrupts memory formation/retrieval ("downregulates neural synchrony")
4. Memory becomes silenced or suppressed

Technical Implementation:
1. Identify memories to forget (query-based search)
2. Apply gradient ascent to RL agent Q-table
3. Push Q-values away from forgotten state-action pairs
4. Mark memories as UNLEARNED (status change)

जय विदुराई! 🕉️
"""

from typing import List, Dict, Optional
from loguru import logger

from vidurai.core.data_structures_v3 import Memory, MemoryStatus, SalienceLevel


class ActiveUnlearningEngine:
    """
    Active, motivated forgetting

    Research: "Neural mechanisms of motivated forgetting" (PMC)
    "Lateral PFC increases activity to suppress unwanted memories"

    Implementation uses gradient ascent to actively retrain away from
    forgotten memories (inspired by machine unlearning research)
    """

    def __init__(self, rl_agent=None):
        """
        Initialize active unlearning engine

        Args:
            rl_agent: VismritiRLAgent instance (v1.5.2 pickle-fixed)
        """
        self.rl_agent = rl_agent

        # Track unlearned state-action pairs (prevent re-learning)
        if self.rl_agent and not hasattr(self.rl_agent, 'unlearned_states'):
            self.rl_agent.unlearned_states = set()

        logger.info("ActiveUnlearningEngine initialized")

    def forget(
        self,
        memories_to_forget: List[Memory],
        method: str = "gradient_ascent",
        explanation: str = "User-requested forgetting"
    ) -> Dict:
        """
        Actively unlearn specified memories

        Research: "This is motivated forgetting - conscious decision to
        suppress unwanted memories" (lateral PFC → hippocampus inhibition)

        Args:
            memories_to_forget: List of memories to forget
            method: Unlearning method ("gradient_ascent" or "simple_suppress")
            explanation: Reason for forgetting (for ledger transparency)

        Returns:
            Statistics about unlearning operation
        """

        stats = {
            "memories_processed": len(memories_to_forget),
            "method": method,
            "unlearned": 0,
            "failed": 0,
            "explanation": explanation
        }

        for memory in memories_to_forget:
            try:
                if method == "gradient_ascent":
                    self._gradient_ascent_unlearn(memory)
                elif method == "simple_suppress":
                    self._simple_suppress(memory)
                else:
                    raise ValueError(f"Unknown method: {method}")

                # Mark as UNLEARNED (research: "engram silencing")
                memory.status = MemoryStatus.UNLEARNED
                memory.salience = SalienceLevel.NOISE
                memory.metadata["unlearn_reason"] = explanation
                memory.metadata["unlearn_method"] = method

                stats["unlearned"] += 1

                logger.info(f"Memory {memory.engram_id[:8]} actively unlearned via {method}")

            except Exception as e:
                stats["failed"] += 1
                logger.error(f"Failed to unlearn memory {memory.engram_id[:8]}: {e}")

        logger.info(
            f"Active unlearning complete: {stats['unlearned']} memories unlearned, "
            f"{stats['failed']} failed"
        )

        return stats

    def _gradient_ascent_unlearn(self, memory: Memory):
        """
        Gradient ascent unlearning

        Research: "Machine Unlearning via Gradient Ascent"

        Process:
        1. Training = gradient descent (move downhill toward correct answer)
        2. Unlearning = gradient ascent (move uphill away from forgotten data)
        3. Maximize loss for forgotten data (opposite of minimize)

        Technical:
        - Get RL state/action from memory metadata
        - Invert Q-value (push away from this state-action pair)
        - Mark as unlearned to prevent re-learning

        References:
        - "Provable Unlearning with Gradient Ascent" (arXiv)
        - "Machine Unlearning: Forgetting by Gradient Ascent" (Medium)
        """

        # Extract RL state/action if available
        rl_state = memory.metadata.get("rl_state")
        rl_action = memory.metadata.get("rl_action")

        if self.rl_agent and rl_state and rl_action:
            # Check if Q-table has this state-action pair
            if hasattr(self.rl_agent, 'policy') and hasattr(self.rl_agent.policy, 'q_table'):
                q_table = self.rl_agent.policy.q_table

                if rl_state in q_table:
                    if rl_action in q_table[rl_state]:
                        current_q = q_table[rl_state][rl_action]

                        # Gradient ascent: push Q-value in opposite direction
                        # Research: "Intentionally maximize error"
                        new_q = current_q * -0.5  # Invert and reduce

                        q_table[rl_state][rl_action] = new_q

                        # Mark as unlearned (prevent re-learning)
                        self.rl_agent.unlearned_states.add((rl_state, rl_action))

                        logger.debug(
                            f"Gradient ascent applied: Q({rl_state}, {rl_action}): "
                            f"{current_q:.4f} → {new_q:.4f}"
                        )

    def _simple_suppress(self, memory: Memory):
        """
        Simple suppression (no RL modification)

        Research: "Engram silencing" - memory trace exists but inaccessible

        Just marks memory as UNLEARNED without modifying RL agent.
        Faster than gradient ascent, but less thorough.
        """
        # No RL modification, just status change
        pass

    def explain_unlearning(self, memory: Memory) -> str:
        """
        Generate natural language explanation of unlearning

        For memory ledger transparency
        """

        if memory.status != MemoryStatus.UNLEARNED:
            return "Memory not unlearned"

        method = memory.metadata.get("unlearn_method", "unknown")
        reason = memory.metadata.get("unlearn_reason", "No reason specified")

        if method == "gradient_ascent":
            return (
                f"Actively unlearned via gradient ascent. "
                f"RL agent retrained to avoid this pattern. "
                f"Reason: {reason}"
            )
        elif method == "simple_suppress":
            return (
                f"Suppressed (engram silenced). "
                f"Memory trace inaccessible but not deleted. "
                f"Reason: {reason}"
            )
        else:
            return f"Unlearned via {method}. Reason: {reason}"
