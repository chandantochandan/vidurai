"""
Project Brain - Automatic Multi-Project Context Manager
Zero-config project detection and intelligent context building
"""

from .scanner import ProjectScanner
from .error_watcher import ErrorWatcher
from .context_builder import ContextBuilder
from .memory_store import MemoryStore

__all__ = ['ProjectScanner', 'ErrorWatcher', 'ContextBuilder', 'MemoryStore']
