"""
The Three-Kosha Memory Architecture
Inspired by Vedantic philosophy of consciousness layers
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from collections import deque
import hashlib
import json
from loguru import logger

@dataclass
class Memory:
    """Base memory unit with philosophical grounding"""
    content: str
    embedding: Optional[List[float]] = None
    importance: float = 0.5
    timestamp: datetime = None
    access_count: int = 0
    dharma_score: float = 1.0  # Ethical alignment
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def age(self) -> timedelta:
        """Age of the memory"""
        return datetime.now() - self.timestamp
    
    @property
    def memory_id(self) -> str:
        """Unique identifier for the memory"""
        return hashlib.md5(self.content.encode()).hexdigest()[:8]


class AnnamayaKosha:
    """
    Working Memory (Physical Layer)
    - Holds last N messages
    - Forgets quickly (minutes)
    - Sliding window approach
    """
    
    def __init__(self, capacity: int = 10, ttl_seconds: int = 300):
        self.capacity = capacity
        self.ttl = timedelta(seconds=ttl_seconds)
        self.memories: deque = deque(maxlen=capacity)
        logger.info(f"Initialized AnnamayaKosha with capacity={capacity}, ttl={ttl_seconds}s")
    
    def add(self, memory: Memory):
        """Add memory to working layer"""
        self.memories.append(memory)
        logger.debug(f"Added memory {memory.memory_id} to working layer")
    
    def get_active(self) -> List[Memory]:
        """Get non-expired memories"""
        now = datetime.now()
        active = [m for m in self.memories if (now - m.timestamp) < self.ttl]
        logger.debug(f"Retrieved {len(active)} active memories from working layer")
        return active
    
    def clear_expired(self):
        """Remove expired memories"""
        active = self.get_active()
        self.memories = deque(active, maxlen=self.capacity)


class ManomayaKosha:
    """
    Episodic Memory (Mental Layer)
    - Recent interactions
    - Forgets gradually (days/weeks)
    - LRU with importance decay
    """
    
    def __init__(self, capacity: int = 1000, decay_rate: float = 0.95):
        self.capacity = capacity
        self.decay_rate = decay_rate
        self.memories: Dict[str, Memory] = {}
        self.access_order: deque = deque(maxlen=capacity)
        logger.info(f"Initialized ManomayaKosha with capacity={capacity}, decay={decay_rate}")
    
    def add(self, memory: Memory):
        """Add memory with importance scoring"""
        memory_id = memory.memory_id
        
        # Apply importance decay to existing memories
        for existing in self.memories.values():
            existing.importance *= self.decay_rate
        
        # Add new memory
        self.memories[memory_id] = memory
        self.access_order.append(memory_id)
        
        # Enforce capacity with importance-based eviction
        if len(self.memories) > self.capacity:
            self._evict_least_important()
        
        logger.debug(f"Added memory {memory_id} to episodic layer")
    
    def _evict_least_important(self):
        """Remove memory with lowest importance"""
        if not self.memories:
            return
        
        min_id = min(self.memories.keys(), 
                    key=lambda k: self.memories[k].importance)
        del self.memories[min_id]
        logger.debug(f"Evicted memory {min_id} from episodic layer")
    
    def get(self, memory_id: str) -> Optional[Memory]:
        """Retrieve and update access stats"""
        if memory_id in self.memories:
            memory = self.memories[memory_id]
            memory.access_count += 1
            memory.importance *= 1.1  # Boost importance on access
            return memory
        return None


class VijnanamayaKosha:
    """
    Archival Memory (Wisdom Layer)
    - Core knowledge
    - Never forgets (only updates)
    - Compressed summaries
    """
    
    def __init__(self, compression_enabled: bool = True):
        self.compression = compression_enabled
        self.memories: Dict[str, Memory] = {}
        self.knowledge_graph: Dict[str, List[str]] = {}  # Connections
        logger.info(f"Initialized VijnanamayaKosha with compression={compression_enabled}")
    
    def add(self, memory: Memory, connections: List[str] = None):
        """Add eternal memory with knowledge graph connections"""
        memory_id = memory.memory_id
        
        # Compress if similar memory exists
        if self.compression:
            similar_id = self._find_similar(memory)
            if similar_id:
                self._merge_memories(similar_id, memory)
                return
        
        # Add to archive
        self.memories[memory_id] = memory
        
        # Build knowledge connections
        if connections:
            self.knowledge_graph[memory_id] = connections
        
        logger.info(f"Archived memory {memory_id} in wisdom layer")
    
    def _find_similar(self, memory: Memory) -> Optional[str]:
        """Find similar existing memory for merging"""
        # TODO: Implement semantic similarity using embeddings
        return None
    
    def _merge_memories(self, existing_id: str, new_memory: Memory):
        """Merge new memory into existing"""
        existing = self.memories[existing_id]
        existing.importance = max(existing.importance, new_memory.importance)
        existing.access_count += 1
        logger.debug(f"Merged memory into {existing_id}")


class ViduraiMemory:
    """
    The complete Three-Kosha Memory System
    Orchestrates all three layers with wisdom
    """
    
    def __init__(self):
        self.working = AnnamayaKosha()
        self.episodic = ManomayaKosha()
        self.archival = VijnanamayaKosha()
        logger.info("Initialized Vidurai Three-Kosha Memory System")
    
    def remember(self, content: str, importance: float = None, **metadata):
        """Add memory to appropriate layers"""
        memory = Memory(
            content=content,
            importance=importance or self._calculate_importance(content),
            metadata=metadata
        )
        
        # Add to working memory always
        self.working.add(memory)
        
        # Add to episodic if important enough
        if memory.importance > 0.3:
            self.episodic.add(memory)
        
        # Add to archival if very important
        if memory.importance > 0.7:
            self.archival.add(memory)
        
        return memory
    
    def _calculate_importance(self, content: str) -> float:
        """Calculate importance using Viveka (discrimination)"""
        # TODO: Implement sophisticated importance scoring
        # For now, basic heuristic
        score = 0.5
        
        # Boost for questions
        if "?" in content:
            score += 0.2
        
        # Boost for personal info
        if any(word in content.lower() for word in ["i", "my", "me"]):
            score += 0.1
        
        return min(score, 1.0)
    
    def recall(self, query: str = None) -> List[Memory]:
        """Retrieve relevant memories from all layers"""
        memories = []
        
        # Get from all layers
        memories.extend(self.working.get_active())
        memories.extend(self.episodic.memories.values())
        memories.extend(self.archival.memories.values())
        
        # TODO: Implement semantic search with query
        # For now, return all sorted by importance
        return sorted(memories, key=lambda m: m.importance, reverse=True)