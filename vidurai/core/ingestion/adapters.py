"""
Streaming Adapters for Knowledge Ingestion
Sprint 2 - "Ghost in the Shell"

Streaming adapters for various AI conversation export formats.
All adapters use ijson generators - NEVER load full JSON into memory.

Supported formats:
- OpenAI (ChatGPT): conversations.json
- Anthropic (Claude): history.json / conversations.json
- Google Gemini: Google Takeout JSON
"""

import ijson
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Generator, Optional, BinaryIO, Any
from loguru import logger


@dataclass
class ViduraiEvent:
    """
    Standardized event from any AI conversation source.

    All adapters must yield ViduraiEvent objects with:
    - content: The actual message/text content
    - timestamp: Original creation time (for remember(created_at=...))
    - role: Who sent the message (user/assistant/system)
    - source: Which AI service (openai/anthropic/gemini)
    - conversation_id: Optional ID to group related messages
    - metadata: Any additional source-specific data
    """
    content: str
    timestamp: datetime
    role: str  # 'user', 'assistant', 'system'
    source: str  # 'openai', 'anthropic', 'gemini'
    conversation_id: Optional[str] = None
    conversation_title: Optional[str] = None
    metadata: Optional[dict] = None


class BaseAdapter(ABC):
    """
    Abstract base class for streaming adapters.

    All adapters MUST:
    1. Use ijson generators (never load full file)
    2. Yield ViduraiEvent objects
    3. Handle malformed data gracefully
    4. Extract original timestamps (not use 'now')
    """

    SOURCE_NAME: str = "unknown"

    @abstractmethod
    def stream_events(self, file_handle: BinaryIO) -> Generator[ViduraiEvent, None, None]:
        """
        Stream events from file handle.

        Args:
            file_handle: Binary file handle opened with 'rb'

        Yields:
            ViduraiEvent objects

        Note:
            MUST use ijson for streaming. Never load full file into memory.
        """
        pass

    @classmethod
    def can_handle(cls, file_path: Path, sample_bytes: bytes = None) -> bool:
        """
        Check if this adapter can handle the given file.

        Args:
            file_path: Path to the file
            sample_bytes: Optional first bytes of file for content detection

        Returns:
            True if this adapter should handle this file
        """
        return False

    def _parse_timestamp(self, value: Any, format_hint: str = None) -> Optional[datetime]:
        """
        Parse timestamp from various formats.

        Args:
            value: Timestamp value (Unix epoch, ISO string, etc.)
            format_hint: Optional format hint

        Returns:
            datetime object or None if parsing fails
        """
        if value is None:
            return None

        try:
            # Unix epoch (float, int, or Decimal from ijson)
            if isinstance(value, (int, float, Decimal)):
                float_val = float(value)
                # Handle both seconds and milliseconds
                if float_val > 1e12:  # Milliseconds
                    return datetime.fromtimestamp(float_val / 1000.0)
                return datetime.fromtimestamp(float_val)

            # String that looks like a number (Unix epoch)
            if isinstance(value, str) and value.replace('.', '', 1).replace('-', '', 1).isdigit():
                float_val = float(value)
                if float_val > 1e12:  # Milliseconds
                    return datetime.fromtimestamp(float_val / 1000.0)
                return datetime.fromtimestamp(float_val)

            # ISO 8601 string
            if isinstance(value, str):
                # Try common formats
                for fmt in [
                    "%Y-%m-%dT%H:%M:%S.%fZ",
                    "%Y-%m-%dT%H:%M:%SZ",
                    "%Y-%m-%dT%H:%M:%S.%f",
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%d %H:%M:%S.%f",
                    "%Y-%m-%d %H:%M:%S",
                ]:
                    try:
                        return datetime.strptime(value.replace("+00:00", "Z").rstrip("Z") + "Z", fmt.replace("Z", "") + "Z" if "Z" in fmt else fmt)
                    except ValueError:
                        continue

                # Fallback: fromisoformat (Python 3.7+)
                try:
                    # Handle 'Z' suffix
                    clean_value = value.replace("Z", "+00:00")
                    return datetime.fromisoformat(clean_value)
                except ValueError:
                    pass

            logger.warning(f"Could not parse timestamp: {value}")
            return None

        except Exception as e:
            logger.warning(f"Timestamp parsing error: {e}")
            return None


class OpenAIAdapter(BaseAdapter):
    """
    Adapter for OpenAI ChatGPT exports.

    File format: conversations.json
    Structure:
        [
            {
                "title": "Conversation Title",
                "create_time": 1699000000.0,  # Unix epoch
                "mapping": {
                    "<node_id>": {
                        "message": {
                            "author": {"role": "user" | "assistant" | "system"},
                            "content": {
                                "parts": ["Message text here"]
                            },
                            "create_time": 1699000000.0
                        }
                    }
                }
            }
        ]
    """

    SOURCE_NAME = "openai"

    def stream_events(self, file_handle: BinaryIO) -> Generator[ViduraiEvent, None, None]:
        """Stream events from OpenAI export."""
        try:
            # Stream top-level array items
            for conversation in ijson.items(file_handle, 'item'):
                conv_id = conversation.get('id') or conversation.get('conversation_id')
                conv_title = conversation.get('title', 'Untitled')
                conv_create_time = conversation.get('create_time')

                # Get mapping (contains all messages)
                mapping = conversation.get('mapping', {})

                for node_id, node in mapping.items():
                    message = node.get('message')
                    if not message:
                        continue

                    # Extract author/role
                    author = message.get('author', {})
                    role = author.get('role', 'unknown')

                    # Skip system messages and tool calls if desired
                    if role not in ('user', 'assistant', 'system'):
                        continue

                    # Extract content
                    content_obj = message.get('content', {})
                    parts = content_obj.get('parts', [])

                    # Combine all parts
                    content_text = ""
                    for part in parts:
                        if isinstance(part, str):
                            content_text += part + "\n"
                        elif isinstance(part, dict):
                            # Handle structured content (images, etc.)
                            text = part.get('text', '')
                            if text:
                                content_text += text + "\n"

                    content_text = content_text.strip()
                    if not content_text:
                        continue

                    # Extract timestamp
                    msg_time = message.get('create_time') or conv_create_time
                    timestamp = self._parse_timestamp(msg_time)

                    if timestamp is None:
                        timestamp = datetime.now()
                        logger.debug(f"Using current time for message (no timestamp found)")

                    yield ViduraiEvent(
                        content=content_text,
                        timestamp=timestamp,
                        role=role,
                        source=self.SOURCE_NAME,
                        conversation_id=conv_id,
                        conversation_title=conv_title,
                        metadata={
                            'node_id': node_id,
                            'model': message.get('metadata', {}).get('model_slug')
                        }
                    )

        except ijson.JSONError as e:
            logger.error(f"JSON parsing error in OpenAI export: {e}")
            raise
        except Exception as e:
            logger.error(f"Error streaming OpenAI export: {e}")
            raise

    @classmethod
    def can_handle(cls, file_path: Path, sample_bytes: bytes = None) -> bool:
        """Check if this is an OpenAI export."""
        name = file_path.name.lower()
        if 'conversations' in name and name.endswith('.json'):
            # Check content for OpenAI signature
            if sample_bytes:
                sample_str = sample_bytes.decode('utf-8', errors='ignore')
                if 'mapping' in sample_str and 'create_time' in sample_str:
                    return True
            return True
        return False


class AnthropicAdapter(BaseAdapter):
    """
    Adapter for Anthropic Claude exports.

    File format: history.json or conversations.json
    Structure:
        [
            {
                "uuid": "conv-uuid",
                "name": "Conversation Title",
                "created_at": "2024-01-15T10:30:00Z",
                "chat_messages": [
                    {
                        "uuid": "msg-uuid",
                        "text": "Message content",
                        "sender": "human" | "assistant",
                        "created_at": "2024-01-15T10:30:00Z"
                    }
                ]
            }
        ]
    """

    SOURCE_NAME = "anthropic"

    def stream_events(self, file_handle: BinaryIO) -> Generator[ViduraiEvent, None, None]:
        """Stream events from Anthropic export."""
        try:
            for conversation in ijson.items(file_handle, 'item'):
                conv_id = conversation.get('uuid') or conversation.get('id')
                conv_title = conversation.get('name', 'Untitled')
                conv_created = conversation.get('created_at')

                # Get chat messages
                chat_messages = conversation.get('chat_messages', [])

                for msg in chat_messages:
                    text = msg.get('text', '').strip()
                    if not text:
                        continue

                    # Map sender to role
                    sender = msg.get('sender', 'unknown')
                    role_map = {
                        'human': 'user',
                        'user': 'user',
                        'assistant': 'assistant',
                        'ai': 'assistant',
                        'system': 'system'
                    }
                    role = role_map.get(sender.lower(), 'user')

                    # Extract timestamp
                    msg_time = msg.get('created_at') or conv_created
                    timestamp = self._parse_timestamp(msg_time)

                    if timestamp is None:
                        timestamp = datetime.now()

                    yield ViduraiEvent(
                        content=text,
                        timestamp=timestamp,
                        role=role,
                        source=self.SOURCE_NAME,
                        conversation_id=conv_id,
                        conversation_title=conv_title,
                        metadata={
                            'message_uuid': msg.get('uuid'),
                            'index': msg.get('index')
                        }
                    )

        except ijson.JSONError as e:
            logger.error(f"JSON parsing error in Anthropic export: {e}")
            raise
        except Exception as e:
            logger.error(f"Error streaming Anthropic export: {e}")
            raise

    @classmethod
    def can_handle(cls, file_path: Path, sample_bytes: bytes = None) -> bool:
        """Check if this is an Anthropic export."""
        name = file_path.name.lower()
        if name in ('history.json', 'claude_conversations.json'):
            return True
        if sample_bytes:
            sample_str = sample_bytes.decode('utf-8', errors='ignore')
            if 'chat_messages' in sample_str and ('human' in sample_str or 'sender' in sample_str):
                return True
        return False


class GeminiAdapter(BaseAdapter):
    """
    Adapter for Google Gemini exports (Google Takeout).

    File format: Various JSON files from Takeout
    Structure:
        {
            "conversations": [
                {
                    "id": "conv-id",
                    "title": "Conversation Title",
                    "createTime": "2024-01-15T10:30:00Z",
                    "events": [
                        {
                            "eventTime": "2024-01-15T10:30:00Z",
                            "author": "USER" | "MODEL",
                            "parts": [
                                {"text": "Message content"}
                            ]
                        }
                    ]
                }
            ]
        }
    """

    SOURCE_NAME = "gemini"

    def stream_events(self, file_handle: BinaryIO) -> Generator[ViduraiEvent, None, None]:
        """Stream events from Gemini/Google Takeout export."""
        try:
            # Try conversations.item path first (nested structure)
            for conversation in ijson.items(file_handle, 'conversations.item'):
                yield from self._process_conversation(conversation)

        except ijson.JSONError:
            # Fallback: try top-level array
            file_handle.seek(0)
            try:
                for conversation in ijson.items(file_handle, 'item'):
                    yield from self._process_conversation(conversation)
            except ijson.JSONError as e:
                logger.error(f"JSON parsing error in Gemini export: {e}")
                raise

    def _process_conversation(self, conversation: dict) -> Generator[ViduraiEvent, None, None]:
        """Process a single conversation object."""
        conv_id = conversation.get('id')
        conv_title = conversation.get('title', 'Untitled')
        conv_created = conversation.get('createTime') or conversation.get('create_time')

        # Get events/messages
        events = conversation.get('events', [])
        if not events:
            # Try alternative structure
            events = conversation.get('messages', [])

        for event in events:
            # Extract parts/text
            parts = event.get('parts', [])
            content_text = ""

            for part in parts:
                if isinstance(part, dict):
                    text = part.get('text', '')
                    if text:
                        content_text += text + "\n"
                elif isinstance(part, str):
                    content_text += part + "\n"

            content_text = content_text.strip()
            if not content_text:
                continue

            # Map author to role
            author = event.get('author', 'USER')
            role_map = {
                'USER': 'user',
                'MODEL': 'assistant',
                'SYSTEM': 'system',
                'user': 'user',
                'model': 'assistant',
            }
            role = role_map.get(author.upper(), 'user')

            # Extract timestamp
            event_time = event.get('eventTime') or event.get('event_time') or conv_created
            timestamp = self._parse_timestamp(event_time)

            if timestamp is None:
                timestamp = datetime.now()

            yield ViduraiEvent(
                content=content_text,
                timestamp=timestamp,
                role=role,
                source=self.SOURCE_NAME,
                conversation_id=conv_id,
                conversation_title=conv_title,
                metadata={
                    'event_type': event.get('eventType')
                }
            )

    @classmethod
    def can_handle(cls, file_path: Path, sample_bytes: bytes = None) -> bool:
        """Check if this is a Gemini/Google Takeout export."""
        name = file_path.name.lower()
        if 'gemini' in name or 'bard' in name:
            return True
        if sample_bytes:
            sample_str = sample_bytes.decode('utf-8', errors='ignore')
            if 'conversations' in sample_str and ('eventTime' in sample_str or 'MODEL' in sample_str):
                return True
        return False


def detect_adapter(file_path: Path) -> Optional[BaseAdapter]:
    """
    Auto-detect the appropriate adapter for a file.

    Args:
        file_path: Path to the export file

    Returns:
        Appropriate adapter instance, or None if unknown
    """
    file_path = Path(file_path)

    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return None

    # Read first 8KB for content detection
    try:
        with open(file_path, 'rb') as f:
            sample = f.read(8192)
    except Exception as e:
        logger.error(f"Could not read file for detection: {e}")
        return None

    # Try each adapter
    adapters = [OpenAIAdapter, AnthropicAdapter, GeminiAdapter]

    for adapter_class in adapters:
        if adapter_class.can_handle(file_path, sample):
            logger.info(f"Detected {adapter_class.SOURCE_NAME} format for {file_path.name}")
            return adapter_class()

    logger.warning(f"Could not detect format for {file_path.name}")
    return None


def get_adapter(source_type: str) -> Optional[BaseAdapter]:
    """
    Get adapter by explicit source type.

    Args:
        source_type: 'openai', 'anthropic', 'gemini'

    Returns:
        Appropriate adapter instance
    """
    adapters = {
        'openai': OpenAIAdapter,
        'chatgpt': OpenAIAdapter,
        'anthropic': AnthropicAdapter,
        'claude': AnthropicAdapter,
        'gemini': GeminiAdapter,
        'google': GeminiAdapter,
        'bard': GeminiAdapter,
    }

    adapter_class = adapters.get(source_type.lower())
    if adapter_class:
        return adapter_class()

    logger.error(f"Unknown source type: {source_type}")
    return None
