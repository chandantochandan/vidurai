"""
The Vismriti Engine - Strategic Forgetting
Teaching AI the wisdom of what to forget
"""

from enum import Enum
from typing import List, Dict, Any
from datetime import datetime, timedelta
from loguru import logger
from .koshas import Memory

class ForgettingPolicy(Enum):
    """The Four Gates of Forgetting"""
    TEMPORAL = "kala_dvara"  # Time-based
    RELEVANCE = "artha_dvara"  # Importance-based  
    REDUNDANCY = "punarukti_dvara"  # Duplication-based
    CONTRADICTION = "virodha_dvara"  # Conflict-based

class VismritiEngine:
    """
    The Art of Strategic Forgetting
    Implements the four gates through which memories must pass
    """
    
    def __init__(self, 
                 policies: List[ForgettingPolicy] = None,
                 aggressive: bool = False):
        self.policies = policies or list(ForgettingPolicy)
        self.aggressive = aggressive
        self.stats = {
            "total_evaluated": 0,
            "total_forgotten": 0,
            "by_policy": {p.value: 0 for p in ForgettingPolicy}
        }
        logger.info(f"Initialized Vismriti Engine with policies={[p.value for p in self.policies]}")
    
    def should_forget(self, memory: Memory, context: Dict[str, Any] = None) -> bool:
        """
        Determine if a memory should be forgotten
        Uses the Four Gates of Forgetting
        """
        self.stats["total_evaluated"] += 1
        context = context or {}
        
        # Check each gate
        for policy in self.policies:
            if self._check_gate(memory, policy, context):
                self.stats["total_forgotten"] += 1
                self.stats["by_policy"][policy.value] += 1
                logger.debug(f"Memory {memory.memory_id} forgotten by {policy.value}")
                return True
        
        return False
    
    def _check_gate(self, memory: Memory, policy: ForgettingPolicy, context: Dict) -> bool:
        """Check if memory should pass through a specific gate"""
        
        if policy == ForgettingPolicy.TEMPORAL:
            return self._check_temporal(memory, context)
        elif policy == ForgettingPolicy.RELEVANCE:
            return self._check_relevance(memory, context)
        elif policy == ForgettingPolicy.REDUNDANCY:
            return self._check_redundancy(memory, context)
        elif policy == ForgettingPolicy.CONTRADICTION:
            return self._check_contradiction(memory, context)
        
        return False
    
    def _check_temporal(self, memory: Memory, context: Dict) -> bool:
        """Time Gate - Forget old memories"""
        max_age = context.get("max_age", timedelta(days=7))
        if self.aggressive:
            max_age = max_age / 2
        
        return memory.age > max_age
    
    def _check_relevance(self, memory: Memory, context: Dict) -> bool:
        """Relevance Gate - Forget unimportant memories"""
        threshold = 0.3 if self.aggressive else 0.2
        return memory.importance < threshold
    
    def _check_redundancy(self, memory: Memory, context: Dict) -> bool:
        """Redundancy Gate - Forget duplicate information"""
        existing_memories = context.get("existing_memories", [])
        
        # Simple duplicate check for now
        # TODO: Implement semantic similarity
        for existing in existing_memories:
            if memory.content == existing.content:
                return True
        
        return False
    
    def _check_contradiction(self, memory: Memory, context: Dict) -> bool:
        """Contradiction Gate - Forget outdated/contradicted info"""
        # TODO: Implement contradiction detection
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Return forgetting statistics"""
        return {
            **self.stats,
            "forget_rate": self.stats["total_forgotten"] / max(self.stats["total_evaluated"], 1)
        }