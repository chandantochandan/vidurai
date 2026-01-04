"""
Vidurai Intelligence Module - Vector Brain & ML Components

Glass Box Protocol: Heavy ML Rule
- All ML imports (sentence-transformers, torch) are LAZY LOADED
- Import happens inside methods, not at module level
- Daemon starts instantly; ML warms up in background

@version 2.1.0-Guardian
"""

from vidurai.core.intelligence.vector_brain import VectorEngine

__all__ = ['VectorEngine']
