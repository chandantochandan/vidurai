"""
Vidurai Knowledge Ingestion System
Sprint 2 - "Ghost in the Shell"

Streaming ingestion of historical AI conversations from:
- OpenAI (ChatGPT exports)
- Anthropic (Claude exports)
- Google Gemini (Takeout exports)

Features:
- ijson streaming for >500MB files
- PII sanitization before storage
- Historical timestamp preservation
- Progress tracking with tqdm
"""

from vidurai.core.ingestion.sanitizer import PIISanitizer
from vidurai.core.ingestion.adapters import (
    BaseAdapter,
    OpenAIAdapter,
    AnthropicAdapter,
    GeminiAdapter,
    ViduraiEvent,
    detect_adapter
)
from vidurai.core.ingestion.manager import IngestionManager

__all__ = [
    'PIISanitizer',
    'BaseAdapter',
    'OpenAIAdapter',
    'AnthropicAdapter',
    'GeminiAdapter',
    'ViduraiEvent',
    'detect_adapter',
    'IngestionManager'
]
