"""
Vidurai Shared Module - Cross-Component Event Schema

This module provides the unified event schema used across all Vidurai components:
- Python SDK
- Daemon
- VS Code Extension (via TypeScript equivalent)
- Browser Extension (via TypeScript equivalent)

Schema Version: vidurai-events-v1
"""

from vidurai.shared.events import (
    # Enums
    EventSource,
    EventChannel,
    EventKind,
    # Base Models
    BasePayload,
    ViduraiEvent,
    # Specialized Payloads
    HintEventPayload,
    FileEditPayload,
    TerminalCommandPayload,
    DiagnosticPayload,
    AIMessagePayload,
    ErrorReportPayload,
    MemoryEventPayload,
)

__all__ = [
    # Enums
    "EventSource",
    "EventChannel",
    "EventKind",
    # Base Models
    "BasePayload",
    "ViduraiEvent",
    # Specialized Payloads
    "HintEventPayload",
    "FileEditPayload",
    "TerminalCommandPayload",
    "DiagnosticPayload",
    "AIMessagePayload",
    "ErrorReportPayload",
    "MemoryEventPayload",
]
