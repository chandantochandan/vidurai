"""
The Vismriti Engine - Strategic Forgetting
Teaching AI the wisdom of what to forget
"""

from enum import Enum
from typing import List, Dict, Any
from datetime import datetime, timedelta
import time
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
        
        # ✨ NEW: Time thresholds in SECONDS for aggressive forgetting
        if aggressive:
            self.time_thresholds = {
                "very_low": 5,      # < 0.3 importance: forget in 5 seconds
                "low": 10,          # < 0.5 importance: forget in 10 seconds  
                "medium": 30,       # < 0.7 importance: forget in 30 seconds
                "high": 300         # >= 0.7 importance: keep for 5 minutes
            }
        else:
            self.time_thresholds = {
                "very_low": 30,     # < 0.3 importance: forget in 30 seconds
                "low": 120,         # < 0.5 importance: forget in 2 minutes
                "medium": 300,      # < 0.7 importance: forget in 5 minutes
                "high": 3600        # >= 0.7 importance: keep for 1 hour
            }
        
        self.stats = {
            "total_evaluated": 0,
            "total_forgotten": 0,
            "by_policy": {p.value: 0 for p in ForgettingPolicy}
        }
        logger.info(f"Initialized Vismriti Engine with policies={[p.value for p in self.policies]}, aggressive={aggressive}")
    
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
        """
        Time Gate - Forget old memories based on importance
        ✨ ENHANCED: Now uses seconds-based thresholds tied to importance
        """
        # Calculate age in seconds - FIX: Handle datetime properly
        current_time = time.time()
        
        # Convert memory timestamp to float if it's a datetime
        if hasattr(memory.timestamp, 'timestamp'):
            memory_timestamp = memory.timestamp.timestamp()
        else:
            memory_timestamp = memory.timestamp
        
        age_seconds = current_time - memory_timestamp
        
        # Determine threshold based on importance
        if memory.importance < 0.3:
            threshold = self.time_thresholds["very_low"]
        elif memory.importance < 0.5:
            threshold = self.time_thresholds["low"]
        elif memory.importance < 0.7:
            threshold = self.time_thresholds["medium"]
        else:
            threshold = self.time_thresholds["high"]
        
        should_forget = age_seconds > threshold
        
        if should_forget:
            logger.debug(
                f"Temporal gate: Memory age={age_seconds:.1f}s, "
                f"threshold={threshold}s, importance={memory.importance:.2f}"
            )
        
        return should_forget
    
    def _check_relevance(self, memory: Memory, context: Dict) -> bool:
        """
        Relevance Gate - Forget unimportant memories
        ✨ ENHANCED: More aggressive thresholds
        """
        # More aggressive threshold based on mode
        threshold = 0.4 if self.aggressive else 0.3
        
        should_forget = memory.importance < threshold
        
        if should_forget:
            logger.debug(
                f"Relevance gate: importance={memory.importance:.2f} < threshold={threshold}"
            )
        
        return should_forget
    
    def _check_redundancy(self, memory: Memory, context: Dict) -> bool:
        """Redundancy Gate - Forget duplicate information"""
        existing_memories = context.get("existing_memories", [])
        
        # Simple duplicate check for now
        # TODO: Implement semantic similarity
        for existing in existing_memories:
            if memory.content == existing.content:
                logger.debug(f"Redundancy gate: Duplicate content found")
                return True
        
        return False
    
    def _check_contradiction(self, memory: Memory, context: Dict) -> bool:
        """Contradiction Gate - Forget outdated/contradicted info"""
        # TODO: Implement contradiction detection
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Return forgetting statistics"""
        forget_rate = self.stats["total_forgotten"] / max(self.stats["total_evaluated"], 1)
        
        return {
            **self.stats,
            "forget_rate": forget_rate,
            "aggressive_mode": self.aggressive,
            "time_thresholds": self.time_thresholds
        }