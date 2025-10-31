"""
Vidurai v2.0 - Core Data Structures
Intelligent Vismriti Engine
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum
import uuid


class MemoryType(Enum):
    """Types of memories in the Three Koshas"""
    WORKING = "working"  # Annamaya Kosha
    EPISODIC = "episodic"  # Manomaya Kosha
    ARCHIVAL = "archival"  # Vijnanamaya Kosha
    COMPRESSED = "compressed"  # Special type for compressed memories


@dataclass
class Memory:
    """
    Base memory unit in Vidurai
    """
    content: str
    memory_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    memory_type: MemoryType = MemoryType.WORKING
    importance: float = 0.5
    timestamp: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    
    # Decay tracking
    decay_score: float = 0.0  # 0 = no decay, 1 = fully decayed
    entropy_score: float = 0.5  # Information entropy
    relevance_score: float = 0.5  # Relevance to current context
    
    @property
    def age_seconds(self) -> float:
        """Age of memory in seconds"""
        return (datetime.now() - self.timestamp).total_seconds()
    
    @property
    def age_minutes(self) -> float:
        """Age of memory in minutes"""
        return self.age_seconds / 60
    
    @property
    def age_days(self) -> float:
        """Age of memory in days"""
        return self.age_seconds / 86400
    
    def mark_accessed(self):
        """Mark this memory as accessed"""
        self.access_count += 1
        self.last_accessed = datetime.now()
        
        # Accessing reinforces the memory (reduces decay)
        self.decay_score = max(0, self.decay_score - 0.1)


@dataclass
class CompressedMemory(Memory):
    """
    A memory that has been semantically compressed
    Contains summary of multiple original memories
    """
    memory_type: MemoryType = MemoryType.COMPRESSED
    
    # Compression metadata
    original_memories: List[str] = field(default_factory=list)  # IDs of original memories
    original_count: int = 0  # How many memories were compressed
    original_tokens: int = 0  # Token count before compression
    compressed_tokens: int = 0  # Token count after compression
    compression_ratio: float = 0.0  # Savings ratio
    compression_timestamp: datetime = field(default_factory=datetime.now)
    
    # Extracted structured facts
    facts: List[Dict[str, str]] = field(default_factory=list)
    
    @property
    def tokens_saved(self) -> int:
        """How many tokens were saved by compression"""
        return self.original_tokens - self.compressed_tokens
    
    @property
    def savings_percentage(self) -> float:
        """Percentage of tokens saved"""
        if self.original_tokens == 0:
            return 0.0
        return (self.tokens_saved / self.original_tokens) * 100


@dataclass
class Message:
    """
    A conversational message (used for compression windows)
    """
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    tokens: int = 0
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def __str__(self):
        return f"[{self.role}]: {self.content}"


@dataclass
class CompressionWindow:
    """
    A window of messages to be compressed
    """
    messages: List[Message]
    start_index: int
    end_index: int
    total_tokens: int
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def message_count(self) -> int:
        return len(self.messages)
    
    def to_text(self) -> str:
        """Convert window to text format for LLM"""
        lines = []
        for msg in self.messages:
            lines.append(f"{msg.role.upper()}: {msg.content}")
        return "\n".join(lines)


@dataclass
class CompressionResult:
    """
    Result of a compression operation
    """
    success: bool
    compressed_memory: Optional[CompressedMemory] = None
    error: Optional[str] = None
    processing_time: float = 0.0
    
    # Statistics
    original_tokens: int = 0
    compressed_tokens: int = 0
    tokens_saved: int = 0
    compression_ratio: float = 0.0


@dataclass
class ConsolidationReport:
    """
    Report from a memory consolidation (sleep cycle)
    """
    clusters_found: int = 0
    merges_completed: int = 0
    promotions: int = 0  # Promoted to archival
    deletions: int = 0
    duration_seconds: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __str__(self):
        return (
            f"Consolidation Report:\n"
            f"  Clusters: {self.clusters_found}\n"
            f"  Merges: {self.merges_completed}\n"
            f"  Promotions: {self.promotions}\n"
            f"  Deletions: {self.deletions}\n"
            f"  Duration: {self.duration_seconds:.2f}s"
        )


@dataclass
class Outcome:
    """
    Outcome of a Vismriti action (for RL agent)
    """
    action: str  # "compress", "decay", "consolidate"
    tokens_saved: int = 0
    retrieval_accuracy: float = 0.0  # 0-1
    information_loss: float = 0.0  # 0-1
    user_satisfaction: float = 0.5  # 0-1
    timestamp: datetime = field(default_factory=datetime.now)
    
    def calculate_reward(self) -> float:
        """
        Calculate reward for RL agent
        Reward = token_savings + retrieval_accuracy - information_loss
        """
        reward = 0.0
        
        # Token savings reward (normalize to $0.01 per 1000 tokens)
        reward += (self.tokens_saved / 1000) * 10
        
        # Retrieval accuracy reward
        reward += self.retrieval_accuracy * 50
        
        # Information loss penalty
        reward -= self.information_loss * 100
        
        # User satisfaction bonus
        reward += self.user_satisfaction * 20
        
        return reward


@dataclass
class VismritiStats:
    """
    Statistics for Vismriti engine
    """
    total_compressions: int = 0
    total_tokens_saved: int = 0
    total_memories_decayed: int = 0
    total_consolidations: int = 0
    average_compression_ratio: float = 0.0
    average_reward: float = 0.0
    uptime_seconds: float = 0.0
    
    def __str__(self):
        return (
            f"Vismriti Statistics:\n"
            f"  Compressions: {self.total_compressions}\n"
            f"  Tokens Saved: {self.total_tokens_saved:,}\n"
            f"  Avg Compression: {self.average_compression_ratio:.1%}\n"
            f"  Memories Decayed: {self.total_memories_decayed}\n"
            f"  Consolidations: {self.total_consolidations}\n"
            f"  Avg Reward: {self.average_reward:.2f}\n"
            f"  Uptime: {self.uptime_seconds/3600:.1f}h"
        )


# Token estimation utilities
def estimate_tokens(text: str) -> int:
    """
    Rough token estimation (1 token ≈ 4 characters)
    For production, use tiktoken or similar
    """
    return len(text) // 4


def calculate_compression_ratio(original_tokens: int, compressed_tokens: int) -> float:
    """
    Calculate compression ratio as a percentage saved
    """
    if original_tokens == 0:
        return 0.0
    saved = original_tokens - compressed_tokens
    return saved / original_tokens