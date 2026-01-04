"""
Stabilizer Module - Daemon-side Event Processing

Provides debouncing, deduplication, and rate limiting for events
received from VS Code extension via IPC.

Features:
- Debouncing: Coalesces rapid events into single processing
- Deduplication: Prevents duplicate event processing
- Rate Limiting: Caps event processing rate
- Smart Filtering: Ignores low-value events
- Batch Processing: Groups events for efficient storage
"""

from .stabilizer import (
    Stabilizer,
    StabilizerOptions,
    StabilizedEvent,
    StabilizerStats,
    get_stabilizer,
    reset_stabilizer,
    should_ignore_file,
)

__all__ = [
    'Stabilizer',
    'StabilizerOptions',
    'StabilizedEvent',
    'StabilizerStats',
    'get_stabilizer',
    'reset_stabilizer',
    'should_ignore_file',
]
