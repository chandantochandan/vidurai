"""
Vidurai Shared Event Schema - v1

Unified event model for all Vidurai components with multi-audience support.

Schema Version: vidurai-events-v1

Usage:
    from vidurai.shared import ViduraiEvent, EventSource, EventKind

    event = ViduraiEvent(
        event_id="uuid-here",
        timestamp="2025-11-25T10:30:00.000Z",
        source=EventSource.VSCODE,
        channel=EventChannel.HUMAN,
        kind=EventKind.FILE_EDIT,
        payload={"file_path": "auth.py"}
    )

Philosophy: विस्मृति भी विद्या है - Unified events for unified memory
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid as uuid_module

from pydantic import BaseModel, Field


# =============================================================================
# ENUMS
# =============================================================================

class EventSource(str, Enum):
    """
    Source system that generated the event
    """
    VSCODE = "vscode"
    BROWSER = "browser"
    PROXY = "proxy"
    DAEMON = "daemon"
    CLI = "cli"


class EventChannel(str, Enum):
    """
    Channel through which the event was generated

    - HUMAN: Direct human action (typing, clicking, running commands)
    - AI: AI-generated content or response
    - SYSTEM: Automated system events (file sync, background jobs)
    """
    HUMAN = "human"
    AI = "ai"
    SYSTEM = "system"


class EventKind(str, Enum):
    """
    Type of event

    Categorizes events by their semantic meaning, not just their source.
    """
    # Editor/IDE events
    FILE_EDIT = "file_edit"
    TERMINAL_COMMAND = "terminal_command"
    DIAGNOSTIC = "diagnostic"

    # AI interaction events
    AI_MESSAGE = "ai_message"
    AI_RESPONSE = "ai_response"

    # System events
    ERROR_REPORT = "error_report"
    MEMORY_EVENT = "memory_event"
    HINT_EVENT = "hint_event"
    METRIC_EVENT = "metric_event"
    SYSTEM_EVENT = "system_event"


# =============================================================================
# BASE MODELS
# =============================================================================

class BasePayload(BaseModel):
    """
    Base class for all event payloads

    Extend this for specific payload types. Currently a placeholder.
    """

    class Config:
        extra = "forbid"  # Enforce strict schema validation


class ViduraiEvent(BaseModel):
    """
    Core event model for all Vidurai events

    This is the canonical schema for events flowing through the Vidurai ecosystem.
    All components (SDK, Daemon, VS Code, Browser) should emit events in this format.

    Schema version: vidurai-events-v1

    Example:
        ViduraiEvent(
            event_id="550e8400-e29b-41d4-a716-446655440000",
            timestamp="2025-11-25T10:30:00.000Z",
            source=EventSource.VSCODE,
            channel=EventChannel.HUMAN,
            kind=EventKind.FILE_EDIT,
            project_root="/home/user/myproject",
            payload={"file_path": "auth.py", "change_type": "save"}
        )
    """

    # Schema identification
    schema_version: str = Field(
        default="vidurai-events-v1",
        description="Event schema version for compatibility"
    )

    # Core fields
    event_id: str = Field(
        default_factory=lambda: str(uuid_module.uuid4()),
        description="Unique identifier for this event (UUID)"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="ISO 8601 UTC timestamp"
    )

    # Event classification
    source: EventSource = Field(
        description="Source system that generated this event"
    )
    channel: EventChannel = Field(
        description="Channel (human/ai/system)"
    )
    kind: EventKind = Field(
        description="Type of event"
    )
    subtype: Optional[str] = Field(
        default=None,
        description="Optional subtype for more granular classification"
    )

    # Context
    project_root: Optional[str] = Field(
        default=None,
        description="Root path of the project"
    )
    project_id: Optional[str] = Field(
        default=None,
        description="Optional project identifier (hash or name)"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Optional session identifier for grouping related events"
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Optional request identifier for tracing"
    )

    # Event-specific data
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Event-specific payload data"
    )

    class Config:
        use_enum_values = True  # Serialize enums as strings
        extra = "forbid"  # Enforce strict schema validation


# =============================================================================
# SPECIALIZED PAYLOADS
# =============================================================================

class HintEventPayload(BasePayload):
    """
    Payload for hint events with multi-audience support

    Hints can be targeted at different audiences:
    - developer: Technical hints (code suggestions, debugging tips)
    - ai: Context for AI assistants (relevant memories, patterns)
    - manager: High-level progress summaries
    - product: Feature/requirement insights
    - stakeholder: Business impact summaries

    Example:
        HintEventPayload(
            hint_id="hint-123",
            hint_type="relevant_context",
            text="Similar auth bug was fixed in commit abc123",
            target="human",
            audience="developer",
            surface="vscode"
        )
    """

    hint_id: str = Field(
        description="Unique identifier for this hint"
    )
    hint_type: str = Field(
        description="Type of hint: relevant_context, follow_up, warning, suggestion"
    )
    text: str = Field(
        description="Human-readable hint text"
    )
    target: str = Field(
        description="Target recipient: human or ai"
    )
    audience: str = Field(
        description="Audience: developer, ai, manager, product, stakeholder"
    )
    surface: str = Field(
        description="Delivery surface: vscode, browser, cli, dashboard"
    )
    accepted: Optional[bool] = Field(
        default=None,
        description="Whether the hint was accepted/used"
    )
    latency_ms: Optional[int] = Field(
        default=None,
        description="Time taken to generate this hint in milliseconds"
    )


class FileEditPayload(BasePayload):
    """
    Payload for file edit events
    """

    file_path: str = Field(
        description="Path to the edited file"
    )
    language: Optional[str] = Field(
        default=None,
        description="Programming language of the file"
    )
    change_type: str = Field(
        description="Type of change: open, save, modify, rename, delete"
    )
    old_path: Optional[str] = Field(
        default=None,
        description="Previous path for rename operations"
    )
    line_count: Optional[int] = Field(
        default=None,
        description="Number of lines in the file"
    )
    hash_before: Optional[str] = Field(
        default=None,
        description="Content hash before change"
    )
    hash_after: Optional[str] = Field(
        default=None,
        description="Content hash after change"
    )
    content_excerpt: Optional[str] = Field(
        default=None,
        description="Brief excerpt of changed content"
    )
    editor: Optional[str] = Field(
        default=None,
        description="Editor used (vscode, vim, etc.)"
    )


class TerminalCommandPayload(BasePayload):
    """
    Payload for terminal command events
    """

    command: str = Field(
        description="The command that was executed"
    )
    exit_code: Optional[int] = Field(
        default=None,
        description="Exit code of the command"
    )
    cwd: Optional[str] = Field(
        default=None,
        description="Working directory"
    )
    shell: Optional[str] = Field(
        default=None,
        description="Shell used (bash, zsh, etc.)"
    )
    duration_ms: Optional[int] = Field(
        default=None,
        description="Command execution time in milliseconds"
    )
    output_excerpt: Optional[str] = Field(
        default=None,
        description="Brief excerpt of command output"
    )
    error_excerpt: Optional[str] = Field(
        default=None,
        description="Brief excerpt of error output"
    )


class DiagnosticPayload(BasePayload):
    """
    Payload for diagnostic events (errors, warnings from IDE)
    """

    file_path: str = Field(
        description="Path to the file with diagnostic"
    )
    severity: str = Field(
        description="Severity: error, warning, info, hint"
    )
    message: str = Field(
        description="Diagnostic message"
    )
    line: Optional[int] = Field(
        default=None,
        description="Line number"
    )
    column: Optional[int] = Field(
        default=None,
        description="Column number"
    )
    source: Optional[str] = Field(
        default=None,
        description="Source of diagnostic (typescript, eslint, etc.)"
    )
    code: Optional[str] = Field(
        default=None,
        description="Diagnostic code"
    )


class AIMessagePayload(BasePayload):
    """
    Payload for AI message events (user prompts and AI responses)
    """

    platform: str = Field(
        description="AI platform: chatgpt, claude, gemini, etc."
    )
    message_type: str = Field(
        description="Type: user_prompt, ai_response, system_message"
    )
    text: Optional[str] = Field(
        default=None,
        description="Message text (may be truncated for privacy)"
    )
    text_length: Optional[int] = Field(
        default=None,
        description="Full length of message in characters"
    )
    model: Optional[str] = Field(
        default=None,
        description="Model used (gpt-4, claude-3, etc.)"
    )
    tokens_in: Optional[int] = Field(
        default=None,
        description="Input tokens (if available)"
    )
    tokens_out: Optional[int] = Field(
        default=None,
        description="Output tokens (if available)"
    )
    context_injected: Optional[bool] = Field(
        default=None,
        description="Whether Vidurai context was injected"
    )


class ErrorReportPayload(BasePayload):
    """
    Payload for error report events
    """

    error_type: str = Field(
        description="Type of error (TypeError, SyntaxError, etc.)"
    )
    error_message: str = Field(
        description="Error message"
    )
    stack_trace: Optional[str] = Field(
        default=None,
        description="Stack trace if available"
    )
    file_path: Optional[str] = Field(
        default=None,
        description="File where error occurred"
    )
    line: Optional[int] = Field(
        default=None,
        description="Line number"
    )
    context: Optional[str] = Field(
        default=None,
        description="Surrounding code context"
    )


class MemoryEventPayload(BasePayload):
    """
    Payload for memory-related events (creation, recall, forget, consolidation)
    """

    action: str = Field(
        description="Action: create, recall, forget, consolidate, pin, unpin"
    )
    memory_id: Optional[str] = Field(
        default=None,
        description="Memory identifier"
    )
    memory_ids: Optional[List[str]] = Field(
        default=None,
        description="Multiple memory identifiers (for batch operations)"
    )
    salience: Optional[str] = Field(
        default=None,
        description="Salience level: critical, high, medium, low, noise"
    )
    gist: Optional[str] = Field(
        default=None,
        description="Brief summary of the memory"
    )
    reason: Optional[str] = Field(
        default=None,
        description="Reason for the action"
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_event(
    kind: EventKind,
    source: EventSource,
    channel: EventChannel = EventChannel.HUMAN,
    project_root: Optional[str] = None,
    **payload_kwargs
) -> ViduraiEvent:
    """
    Convenience function to create a ViduraiEvent

    Args:
        kind: Event type
        source: Source system
        channel: Channel (default: HUMAN)
        project_root: Optional project path
        **payload_kwargs: Payload fields

    Returns:
        ViduraiEvent instance

    Example:
        event = create_event(
            EventKind.FILE_EDIT,
            EventSource.VSCODE,
            project_root="/home/user/project",
            file_path="auth.py",
            change_type="save"
        )
    """
    return ViduraiEvent(
        source=source,
        channel=channel,
        kind=kind,
        project_root=project_root,
        payload=payload_kwargs
    )
