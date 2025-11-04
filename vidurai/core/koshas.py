"""
The Three-Kosha Memory Architecture
Inspired by Vedantic philosophy of consciousness layers

✨ v2.0: Now with Intelligent Semantic Compression & RL Agent
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from collections import deque
import hashlib
import json
import time
from loguru import logger

# ✨ NEW: Import v2 compression module
try:
    from .semantic_compressor_v2 import SemanticCompressor, MockLLMClient
    from .data_structures_v2 import Message as V2Message, estimate_tokens
    COMPRESSION_AVAILABLE = True
except ImportError:
    COMPRESSION_AVAILABLE = False
    logger.warning("Semantic compression module not available")

# ✨ RL AGENT: Import reinforcement learning brain
try:
    from .rl_agent_v2 import VismritiRLAgent, Action, Outcome, RewardProfile
    RL_AGENT_AVAILABLE = True
except ImportError:
    RL_AGENT_AVAILABLE = False
    logger.warning("RL Agent module not available")


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
    def age_seconds(self) -> float:
        """✨ NEW: Age in seconds (for Vismriti compatibility)"""
        return (datetime.now() - self.timestamp).total_seconds()
    
    @property
    def timestamp_float(self) -> float:
        """✨ NEW: Timestamp as float (for Vismriti compatibility)"""
        return self.timestamp.timestamp()
    
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
    
    def remove(self, memory: Memory):
        """✨ NEW: Remove specific memory"""
        try:
            self.memories.remove(memory)
            logger.debug(f"Removed memory {memory.memory_id} from working layer")
        except ValueError:
            pass  # Memory not in deque


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
    
    def remove(self, memory: Memory):
        """✨ NEW: Remove specific memory"""
        memory_id = memory.memory_id
        if memory_id in self.memories:
            del self.memories[memory_id]
            logger.debug(f"Removed memory {memory_id} from episodic layer")


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
    
    ✨ v2.0: Now with Intelligent Semantic Compression & RL Agent
    """
    
    def __init__(
        self,
        enable_compression: bool = True,
        llm_client=None,
        enable_rl_agent: bool = True,
        reward_profile: Optional[RewardProfile] = None,
        decay_rate: float = 0.95,
        enable_decay: bool = True
    ):
        """
        Initialize Vidurai Memory System

        Args:
            enable_compression: Enable semantic compression (default: True)
            llm_client: LLM client for compression (default: MockLLMClient)
            enable_rl_agent: Enable RL Agent for intelligent decisions (default: True)
            reward_profile: User's priority (cost vs. quality)
            decay_rate: Importance decay rate for episodic memory (default: 0.95)
            enable_decay: Enable importance decay (default: True, set False for high-threshold recall)
        """
        self.working = AnnamayaKosha()
        # Pass decay configuration to episodic memory
        self.episodic = ManomayaKosha(
            decay_rate=decay_rate if enable_decay else 1.0
        )
        self.archival = VijnanamayaKosha()
        self.vismriti = None  # Will be set by create_memory_system()
        
        # ✨ NEW: Semantic Compression
        self.compression_enabled = enable_compression and COMPRESSION_AVAILABLE
        self.compressor = None
        self.compression_history = []  # Track compressed memories
        
        if self.compression_enabled:
            # Use mock client if no real client provided (for testing)
            if llm_client is None and COMPRESSION_AVAILABLE:
                llm_client = MockLLMClient()
            
            if COMPRESSION_AVAILABLE:
                self.compressor = SemanticCompressor(
                    llm_client=llm_client,
                    compression_threshold=5,  # Compress after 5 messages
                    min_tokens_to_compress=50
                )
                logger.info("✨ Semantic compression enabled")
        
        # ✨ RL AGENT: The intelligent decision-making brain
        self.rl_agent_enabled = enable_rl_agent and RL_AGENT_AVAILABLE
        self.rl_agent = None
        self._messages_since_compression = 0
        self._messages_since_last_action = 0
        
        if self.rl_agent_enabled:
            self.rl_agent = VismritiRLAgent(
                reward_profile=reward_profile or RewardProfile.BALANCED
            )
            logger.info("✨ RL Agent enabled - intelligent memory management active")
        
        logger.info("Initialized Vidurai Three-Kosha Memory System")
    
    def remember(self, content: str, importance: float = None, **metadata):
        """
        Add memory to appropriate layers
        ✨ v2.0: RL Agent decides when to compress/decay
        """
        memory = Memory(
            content=content,
            importance=importance or self._calculate_importance(content),
            metadata=metadata
        )
        
        # Add to working memory always
        self.working.add(memory)
        self._messages_since_compression += 1
        self._messages_since_last_action += 1
        
        # Add to episodic if important enough
        if memory.importance > 0.3:
            self.episodic.add(memory)
        
        # Add to archival if very important
        if memory.importance > 0.7:
            self.archival.add(memory)
        
        # ✨ RL AGENT: Ask intelligent agent what to do
        if self.rl_agent_enabled and self.rl_agent:
            self._rl_agent_decision()
        elif self.compression_enabled and self.compressor:
            # Fallback: simple rule-based compression
            self._try_compress()
        
        return memory
    
    def _rl_agent_decision(self):
        """
        ✨ RL AGENT: Let the intelligent agent decide optimal action
        
        The agent observes state, decides action, executes, and learns from outcome.
        This is where intelligence emerges from experience.
        """
        if not self.rl_agent:
            return
        
        # 1. Observe current state
        state = self.rl_agent.observe(self)
        
        # 2. Agent decides action (ε-greedy policy)
        action = self.rl_agent.decide(state)
        
        # 3. Execute the chosen action
        outcome = self._execute_rl_action(action)
        
        # 4. Observe next state
        next_state = self.rl_agent.observe(self)
        
        # 5. Agent learns from outcome
        self.rl_agent.learn(outcome, next_state)
        
        # Reset counter if action was taken
        if action != Action.DO_NOTHING:
            self._messages_since_last_action = 0
    
    def _execute_rl_action(self, action: Action) -> Outcome:
        """
        ✨ RL AGENT: Execute the action chosen by RL agent
        
        Returns Outcome for learning
        """
        tokens_saved = 0
        retrieval_accuracy = 1.0  # Default, can be measured in production
        information_loss = 0.0
        
        # Execute based on action type
        if action == Action.COMPRESS_NOW:
            # Standard compression
            result = self._try_compress()
            if result and result.get('success'):
                tokens_saved = result.get('tokens_saved', 0)
                information_loss = 0.05  # Small loss from compression
        
        elif action == Action.COMPRESS_AGGRESSIVE:
            # More aggressive compression (smaller keep_recent)
            result = self._try_compress(keep_recent=2, importance=0.5)
            if result and result.get('success'):
                tokens_saved = result.get('tokens_saved', 0)
                information_loss = 0.15  # Higher loss
        
        elif action == Action.COMPRESS_CONSERVATIVE:
            # Conservative compression (larger keep_recent)
            result = self._try_compress(keep_recent=5, importance=0.7)
            if result and result.get('success'):
                tokens_saved = result.get('tokens_saved', 0)
                information_loss = 0.02  # Lower loss
        
        elif action == Action.DO_NOTHING:
            # Intentionally wait - agent learning patience
            pass
        
        # Create outcome for learning
        outcome = Outcome(
            action=action,
            tokens_saved=tokens_saved,
            retrieval_accuracy=retrieval_accuracy,
            information_loss=information_loss,
            user_satisfaction=0.8,  # Default, can be updated with user feedback
        )
        
        return outcome
    
    def _try_compress(self, keep_recent: int = 3, importance: float = 0.6) -> Optional[Dict[str, Any]]:
        """
        ✨ NEW: Try to compress old working memory
        Automatically triggered when working memory fills up
        
        Args:
            keep_recent: Number of recent messages to keep uncompressed
            importance: Importance score for compressed memory
        
        Returns:
            Dict with success, tokens_saved, etc. or None
        """
        if not self.compressor:
            return None
        
        # Convert working memories to Message format for compression
        messages = self._memories_to_messages(list(self.working.memories))
        
        if len(messages) < 5:
            return None  # Not enough to compress
        
        # Detect compressible window
        window = self.compressor.detect_compressible_window(messages, keep_recent=keep_recent)
        
        if window:
            # Compress the window
            result = self.compressor.compress_window(window, importance=importance)
            
            if result.success:
                logger.info(f"✨ Compressed {window.message_count} messages: "
                          f"saved {result.tokens_saved} tokens ({result.compression_ratio:.1%})")

                # Remove compressed memories from working layer AND episodic layer
                # This is CRITICAL to prevent token accumulation!
                for msg in window.messages:
                    # Find and remove corresponding memory from both layers
                    for mem in list(self.working.memories):
                        if mem.content == msg.content:
                            self.working.remove(mem)
                            # BUGFIX: Also remove from episodic to prevent accumulation
                            self.episodic.remove(mem)
                            break
                
                # Store compressed summary in episodic layer
                compressed_memory = Memory(
                    content=result.compressed_memory.content,
                    importance=result.compressed_memory.importance,
                    metadata={
                        'compressed': True,
                        'original_count': result.compressed_memory.original_count,
                        'tokens_saved': result.tokens_saved,
                        'compression_ratio': result.compression_ratio,
                        'facts': result.compressed_memory.facts
                    }
                )
                self.episodic.add(compressed_memory)
                
                # Track compression history
                self.compression_history.append(result)
                
                # Reset counter
                self._messages_since_compression = 0
                
                return {
                    'success': True,
                    'tokens_saved': result.tokens_saved,
                    'compression_ratio': result.compression_ratio
                }
            else:
                logger.warning(f"Compression failed: {result.error}")
                return {'success': False, 'error': result.error}
        
        return None
    
    def _memories_to_messages(self, memories: List[Memory]) -> List:
        """
        ✨ NEW: Convert Memory objects to v2 Message format
        """
        if not COMPRESSION_AVAILABLE:
            return []
        
        messages = []
        for mem in memories:
            # Determine role based on metadata or heuristic
            role = mem.metadata.get('role', 'user')
            
            msg = V2Message(
                role=role,
                content=mem.content,
                timestamp=mem.timestamp,
                tokens=estimate_tokens(mem.content)
            )
            messages.append(msg)
        
        return messages
    
    def get_compression_stats(self) -> Dict[str, Any]:
        """
        ✨ NEW: Get compression statistics
        """
        if not self.compressor:
            return {
                'enabled': False,
                'total_compressions': 0,
                'total_tokens_saved': 0
            }
        
        stats = self.compressor.get_statistics()
        stats['enabled'] = True
        stats['compression_history'] = len(self.compression_history)
        
        return stats
    
    def get_rl_agent_stats(self) -> Dict[str, Any]:
        """
        ✨ RL AGENT: Get RL agent learning statistics
        """
        if not self.rl_agent:
            return {
                'enabled': False,
                'episodes': 0,
                'epsilon': 0.0
            }
        
        stats = self.rl_agent.get_statistics()
        stats['enabled'] = True
        
        return stats
    
    def end_conversation(self):
        """
        ✨ RL AGENT: Mark end of conversation (episode)
        Triggers epsilon decay
        """
        if self.rl_agent:
            self.rl_agent.end_episode()
            logger.debug("Conversation episode ended, agent maturity increased")
    
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
    
    def recall(self, query: str = "", limit: int = 10, min_importance: float = 0.5) -> List[Memory]:
        """
        ✨ ENHANCED: Intelligent recall with optional importance filtering
        
        Args:
            query: Search query (optional)
            limit: Maximum memories to return
            min_importance: Minimum importance threshold (default 0.5, set to 0.0 for testing)
        """
        # Step 1: Clean up forgotten memories using Vismriti
        if self.vismriti:
            self._cleanup_forgotten()
        
        # Step 2: Get all active memories
        all_memories = []
        all_memories.extend(self.working.get_active())
        all_memories.extend(self.episodic.memories.values())
        all_memories.extend(self.archival.memories.values())
        
        # Step 3: Remove duplicates
        seen_ids = set()
        unique_memories = []
        for m in all_memories:
            if m.memory_id not in seen_ids:
                unique_memories.append(m)
                seen_ids.add(m.memory_id)
        
        # Step 4: Filter by importance (optional)
        if min_importance > 0:
            important_memories = [m for m in unique_memories if m.importance >= min_importance]
        else:
            important_memories = unique_memories
        
        # If no important memories, return top N by importance anyway
        if not important_memories and unique_memories:
            important_memories = sorted(
                unique_memories, 
                key=lambda m: m.importance, 
                reverse=True
            )[:limit]
        
        # Step 5: Sort by importance
        important_memories.sort(key=lambda m: m.importance, reverse=True)
        
        # Step 6: Query filter if provided
        if query:
            relevant = [m for m in important_memories if query.lower() in m.content.lower()]
            if relevant:
                logger.debug(f"Filtered {len(relevant)} memories matching query: '{query}'")
                return relevant[:limit]
        
        # Step 7: Return results
        result = important_memories[:limit]
        logger.debug(f"Recalled {len(result)} memories (min_importance={min_importance}, limit={limit})")
        return result
    
    def _cleanup_forgotten(self):
        """
        ✨ NEW: Actually REMOVE forgotten memories from storage using Vismriti
        """
        if not self.vismriti:
            return
        
        forgotten_count = 0
        
        # Check working memory
        working_to_remove = []
        for memory in list(self.working.memories):
            if self.vismriti.should_forget(memory):
                working_to_remove.append(memory)
        
        for memory in working_to_remove:
            self.working.remove(memory)
            forgotten_count += 1
        
        # Check episodic memory
        episodic_to_remove = []
        for memory in list(self.episodic.memories.values()):
            if self.vismriti.should_forget(memory):
                episodic_to_remove.append(memory)
        
        for memory in episodic_to_remove:
            self.episodic.remove(memory)
            forgotten_count += 1
        
        # Archival memory is NEVER forgotten (as per philosophy)
        
        if forgotten_count > 0:
            logger.info(f"Cleanup: Forgot {forgotten_count} memories based on Vismriti policies")