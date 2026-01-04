"""
Vidurai State Module - Focus Tracking & Context Resolution

The State Linker tracks user's active context:
- Current file being edited
- Cursor position and selection
- Recent file history

Glass Box Protocol: Reality Grounding
- Trust No One: Validate all paths exist on disk
- Never pollute state with hallucinated paths

@version 2.1.0-Guardian
"""

from vidurai.core.state.linker import StateLinker

__all__ = ['StateLinker']
