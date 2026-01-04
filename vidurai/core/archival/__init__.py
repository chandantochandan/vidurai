"""
Vidurai Archival Module - Tiered Storage Lifecycle

Moves ARCHIVED memories from SQLite (Hot) to Parquet (Cold).

Glass Box Protocol: Atomic Archiver
- Select rows → Write Parquet → VERIFY exists → DELETE from SQLite
- Never delete from SQLite before Parquet write is confirmed

@version 2.1.0-Guardian
"""

from vidurai.core.archival.archiver import MemoryArchiver

__all__ = ['MemoryArchiver']
