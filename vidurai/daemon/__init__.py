"""
Vidurai Daemon Package

The background service that powers Vidurai's memory infrastructure.

Usage:
    python -m vidurai.daemon

Components:
    - server: Main daemon server (FastAPI + IPC)
    - ipc: Named pipe/Unix socket IPC layer
    - intelligence: Context mediation and memory bridge
    - project_brain: Project scanning and error watching

@version 2.2.0-Guardian
"""

from pathlib import Path

# Package version
__version__ = "2.2.0"

# Data directory (Path Safety Rule: ALWAYS use home directory)
DATA_DIR = Path.home() / ".vidurai"
SOCKET_PATH = DATA_DIR / "vidurai.sock"  # or /tmp for cross-user access

__all__ = [
    "__version__",
    "DATA_DIR",
    "SOCKET_PATH",
]
