"""
Vidurai Analytics Module - Repo Intelligence

Query archived memories using DuckDB for fast analytics.

Glass Box Protocol: Empty Archive Rule
- Check if archive has files before querying
- Return [] if empty (Don't crash)

@version 2.1.0-Guardian
"""

from vidurai.core.analytics.engine import RepoAnalyst

__all__ = ['RepoAnalyst']
