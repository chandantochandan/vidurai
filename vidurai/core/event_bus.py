"""
Vidurai Event Bus - Local Telemetry Core
Phase 6.1: Passive & Automatic Memory Capture

A lightweight, in-process event bus for capturing developer activity
across all Vidurai subsystems (terminal, AI, editor).

Philosophy: विस्मृति भी विद्या है - Memories that build themselves

Design:
- Local-only (no external network or telemetry)
- Thread-safe pub/sub pattern
- Ring buffer for debugging (last N events)
- Zero dependencies on external message queues
"""

import uuid
import threading
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field, asdict
from collections import deque
from loguru import logger


@dataclass
class ViduraiEvent:
    """
    Represents a single event in the Vidurai system

    Events are emitted by various sources (terminal, AI, editor) and
    consumed by episode builders, auto-memory policies, and hint generators.

    Examples:
        Terminal command executed:
            ViduraiEvent(
                type="terminal.command",
                source="daemon",
                project_path="/path/to/project",
                payload={"command": "npm test", "exit_code": 0}
            )

        AI message sent:
            ViduraiEvent(
                type="ai.user_message",
                source="browser",
                project_path="/path/to/project",
                payload={"tool": "claude", "text": "How to fix auth bug?"}
            )

        File saved in editor:
            ViduraiEvent(
                type="editor.file_save",
                source="vscode",
                project_path="/path/to/project",
                payload={"file_path": "auth.py", "language": "python"}
            )
    """

    # Core fields
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = ""  # e.g., "terminal.command", "ai.user_message", "editor.file_save"
    timestamp: datetime = field(default_factory=datetime.now)

    # Context
    source: str = ""  # "daemon", "vscode", "browser", "cli"
    project_path: Optional[str] = None

    # Event-specific data
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

    def __str__(self) -> str:
        """Human-readable representation"""
        project = self.project_path or "unknown"
        return f"[{self.source}] {self.type} @ {project}"


class EventBus:
    """
    Thread-safe, in-process event bus for Vidurai

    Implements a simple pub/sub pattern where:
    - Publishers emit events via publish()
    - Subscribers register handlers via subscribe()
    - Ring buffer maintains last N events for debugging

    Thread Safety:
    - Uses threading.Lock for all shared state
    - Handlers are called synchronously (consider async in v2)

    Usage:
        # Subscribe to events
        def handle_terminal_event(event: ViduraiEvent):
            if event.type == "terminal.error":
                print(f"Error detected: {event.payload}")

        EventBus.subscribe(handle_terminal_event)

        # Publish events
        EventBus.publish(ViduraiEvent(
            type="terminal.error",
            source="daemon",
            payload={"error": "TypeError in auth.py"}
        ))

        # Debug: inspect recent events
        recent = EventBus.get_recent_events(limit=10)
    """

    # Class-level state (singleton pattern)
    _handlers: List[Callable[[ViduraiEvent], None]] = []
    _event_buffer: deque = deque(maxlen=500)  # Ring buffer: last 500 events
    _lock: threading.Lock = threading.Lock()
    _enabled: bool = True  # Can be disabled for testing

    @classmethod
    def publish(cls, event: ViduraiEvent) -> None:
        """
        Publish an event to all subscribers

        Thread-safe. Handlers are called synchronously in order of subscription.
        If a handler raises an exception, it's logged but doesn't affect other handlers.

        Args:
            event: The event to publish

        Example:
            EventBus.publish(ViduraiEvent(
                type="terminal.command",
                source="daemon",
                project_path="/home/user/project",
                payload={"command": "pytest", "exit_code": 0}
            ))
        """
        if not cls._enabled:
            return

        with cls._lock:
            # Add to ring buffer
            cls._event_buffer.append(event)

            # Copy handlers to avoid holding lock during callbacks
            handlers = cls._handlers.copy()

        # Call handlers outside lock to prevent deadlocks
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(
                    f"Event handler error for {event.type}: {e}",
                    exc_info=True
                )

    @classmethod
    def subscribe(cls, handler: Callable[[ViduraiEvent], None]) -> None:
        """
        Subscribe to all events

        The handler will be called for every published event.
        Handlers can filter events by checking event.type or other fields.

        Thread-safe.

        Args:
            handler: Callback function that takes a ViduraiEvent

        Example:
            def my_handler(event: ViduraiEvent):
                if event.type.startswith("terminal."):
                    print(f"Terminal event: {event}")

            EventBus.subscribe(my_handler)
        """
        with cls._lock:
            if handler not in cls._handlers:
                cls._handlers.append(handler)
                logger.debug(f"Subscribed handler: {handler.__name__}")

    @classmethod
    def unsubscribe(cls, handler: Callable[[ViduraiEvent], None]) -> None:
        """
        Unsubscribe a handler

        Thread-safe.

        Args:
            handler: The handler to remove
        """
        with cls._lock:
            if handler in cls._handlers:
                cls._handlers.remove(handler)
                logger.debug(f"Unsubscribed handler: {handler.__name__}")

    @classmethod
    def get_recent_events(cls, limit: int = 100) -> List[ViduraiEvent]:
        """
        Get recent events from ring buffer

        Useful for debugging and inspection.

        Thread-safe.

        Args:
            limit: Maximum number of events to return (default: 100)

        Returns:
            List of recent events, newest first
        """
        with cls._lock:
            events = list(cls._event_buffer)

        # Return newest first
        events.reverse()
        return events[:limit]

    @classmethod
    def clear_buffer(cls) -> None:
        """
        Clear the event buffer

        Useful for testing.

        Thread-safe.
        """
        with cls._lock:
            cls._event_buffer.clear()
            logger.debug("Event buffer cleared")

    @classmethod
    def clear_handlers(cls) -> None:
        """
        Clear all handlers

        Useful for testing.

        Thread-safe.
        """
        with cls._lock:
            cls._handlers.clear()
            logger.debug("All handlers cleared")

    @classmethod
    def reset(cls) -> None:
        """
        Reset EventBus to initial state

        Clears handlers and buffer. Useful for testing.

        Thread-safe.
        """
        with cls._lock:
            cls._handlers.clear()
            cls._event_buffer.clear()
            cls._enabled = True
            logger.debug("EventBus reset")

    @classmethod
    def enable(cls) -> None:
        """Enable event publishing"""
        with cls._lock:
            cls._enabled = True

    @classmethod
    def disable(cls) -> None:
        """Disable event publishing (for testing)"""
        with cls._lock:
            cls._enabled = False

    @classmethod
    def get_statistics(cls) -> Dict[str, Any]:
        """
        Get EventBus statistics

        Thread-safe.

        Returns:
            Dict with handler count, buffer size, event type counts
        """
        with cls._lock:
            events = list(cls._event_buffer)
            handler_count = len(cls._handlers)

        # Count by event type
        type_counts = {}
        for event in events:
            type_counts[event.type] = type_counts.get(event.type, 0) + 1

        # Count by source
        source_counts = {}
        for event in events:
            source_counts[event.source] = source_counts.get(event.source, 0) + 1

        return {
            'enabled': cls._enabled,
            'handler_count': handler_count,
            'buffer_size': len(events),
            'buffer_max_size': cls._event_buffer.maxlen,
            'event_types': type_counts,
            'event_sources': source_counts,
        }


# Convenience function for quick event publishing
def publish_event(
    event_type: str,
    source: str,
    project_path: Optional[str] = None,
    **payload
) -> ViduraiEvent:
    """
    Convenience function to create and publish an event

    Args:
        event_type: Type of event (e.g., "terminal.command")
        source: Source system (e.g., "daemon", "vscode")
        project_path: Optional project path
        **payload: Event-specific data as keyword arguments

    Returns:
        The created event

    Example:
        publish_event(
            "terminal.error",
            source="daemon",
            project_path="/path/to/project",
            error="TypeError",
            file="auth.py",
            line=42
        )
    """
    event = ViduraiEvent(
        type=event_type,
        source=source,
        project_path=project_path,
        payload=payload
    )
    EventBus.publish(event)
    return event
