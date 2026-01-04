"""
Archiver Module - Storage Lifecycle Management

Provides tiered storage with automatic archival from JSONL to Parquet.

Architecture:
- Hot Storage: JSONL files for recent events (fast append)
- Cold Storage: Parquet files for archived data (efficient queries)
- Retention: Configurable policies for data lifecycle

Features:
- Automatic rotation from hot to cold storage
- Efficient columnar storage for analytics
- Compression for space efficiency
- Date-based partitioning
- Query interface for both tiers
"""

from .archiver import (
    Archiver,
    ArchiverOptions,
    StorageStats,
    EventRecord,
    get_archiver,
    reset_archiver,
)

__all__ = [
    'Archiver',
    'ArchiverOptions',
    'StorageStats',
    'EventRecord',
    'get_archiver',
    'reset_archiver',
]
