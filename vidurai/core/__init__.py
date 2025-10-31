"""
Vidurai Core Module
Contains memory architecture and intelligent compression
"""

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

# Public API
__all__ = [
    # Data structures
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
    # Compression
    'SemanticCompressor',
    'LLMClient',
    'MockLLMClient',
]