"""
Vidurai Core Module
Contains memory architecture and intelligent compression
"""

# Import main classes from koshas (THE CORE!)
from .koshas import (
    ViduraiMemory,
    Memory as KoshaMemory,  # Renamed to avoid conflict with data_structures_v2.Memory
    AnnamayaKosha,
    ManomayaKosha,
    VijnanamayaKosha,
)

# Import v2 data structures
from .data_structures_v2 import (
    Memory,
    CompressedMemory,
    Message,
    CompressionWindow,
    CompressionResult,
    ConsolidationReport,
    Outcome,
    VismritiStats,
    MemoryType,
    estimate_tokens,
    calculate_compression_ratio,
)

# Import v2 semantic compressor
from .semantic_compressor_v2 import (
    SemanticCompressor,
    LLMClient,
    MockLLMClient,
)

# Import v2 RL agent
from .rl_agent_v2 import (
    VismritiRLAgent,
    Action,
    RewardProfile,
    MemoryState,
)

# Public API
__all__ = [
    # CORE CLASSES (v1 - MOST IMPORTANT!)
    'ViduraiMemory',
    'KoshaMemory',
    'AnnamayaKosha',
    'ManomayaKosha',
    'VijnanamayaKosha',
    # Data structures (v2)
    'Memory',
    'CompressedMemory',
    'Message',
    'CompressionWindow',
    'CompressionResult',
    'ConsolidationReport',
    'Outcome',
    'VismritiStats',
    'MemoryType',
    'estimate_tokens',
    'calculate_compression_ratio',
    # Compression (v2)
    'SemanticCompressor',
    'LLMClient',
    'MockLLMClient',
    # RL Agent (v2)
    'VismritiRLAgent',
    'Action',
    'RewardProfile',
    'MemoryState',
]