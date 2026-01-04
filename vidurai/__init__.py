"""
Vidurai - Teaching AI the Art of Memory and Forgetting
A Vedantic approach to AI memory management

विस्मृति भी विद्या है (Forgetting too is knowledge)

LAZY LOADING: This module uses lazy imports to ensure CLI startup < 0.5s.
Heavy modules are only loaded when their classes are actually accessed.
"""

# Version - lightweight, safe to import immediately
__version__ = "2.2.0"
__version_info__ = (2, 2, 0)
__author__ = "Vidurai Team"

# Export list (classes are lazy-loaded below)
__all__ = [
    # Legacy v1.5.x (still supported)
    "ViduraiMemory",
    "Memory",
    "VismritiEngine",
    "ForgettingPolicy",
    "VivekaEngine",
    "create_memory_system",

    # New v2.0.0 (Vismriti Architecture)
    "VismritiMemory",
    "VismritiMemoryObject",
    "SalienceLevel",
    "MemoryStatus",
]

# ============================================================================
# LAZY LOADING IMPLEMENTATION
# Classes are only imported when first accessed via __getattr__
# ============================================================================

def __getattr__(name):
    """Lazy load heavy modules only when accessed."""

    # Legacy API (v1.5.x)
    if name == "ViduraiMemory":
        from vidurai.core.koshas import ViduraiMemory
        return ViduraiMemory
    if name == "Memory":
        from vidurai.core.koshas import Memory
        return Memory
    if name == "VismritiEngine":
        from vidurai.core.vismriti import VismritiEngine
        return VismritiEngine
    if name == "ForgettingPolicy":
        from vidurai.core.vismriti import ForgettingPolicy
        return ForgettingPolicy
    if name == "VivekaEngine":
        from vidurai.core.viveka import VivekaEngine
        return VivekaEngine

    # New API (v2.0.0 - Vismriti Architecture)
    if name == "VismritiMemory":
        from vidurai.vismriti_memory import VismritiMemory
        return VismritiMemory
    if name == "VismritiMemoryObject":
        from vidurai.core.data_structures_v3 import Memory as VismritiMemoryObject
        return VismritiMemoryObject
    if name == "SalienceLevel":
        from vidurai.core.data_structures_v3 import SalienceLevel
        return SalienceLevel
    if name == "MemoryStatus":
        from vidurai.core.data_structures_v3 import MemoryStatus
        return MemoryStatus

    # LangChain Integration
    if name == "LangChainViduraiMemory":
        from vidurai.integrations.langchain import ViduraiMemory as LangChainViduraiMemory
        return LangChainViduraiMemory
    if name == "ViduraiConversationChain":
        from vidurai.integrations.langchain import ViduraiConversationChain
        return ViduraiConversationChain

    raise AttributeError(f"module 'vidurai' has no attribute '{name}'")


def create_memory_system(
    working_capacity: int = 10,
    episodic_capacity: int = 1000,
    aggressive_forgetting: bool = False
):
    """
    Factory function to create a complete Vidurai memory system

    Args:
        working_capacity: Size of working memory (default 10)
        episodic_capacity: Size of episodic memory (default 1000)
        aggressive_forgetting: Enable aggressive forgetting (default False)

    Returns:
        Configured ViduraiMemory instance
    """
    # Lazy import when function is called
    from vidurai.core.koshas import ViduraiMemory
    from vidurai.core.vismriti import VismritiEngine
    from vidurai.core.viveka import VivekaEngine

    memory = ViduraiMemory()
    memory.working.capacity = working_capacity
    memory.episodic.capacity = episodic_capacity

    # Configure forgetting engine
    memory.vismriti = VismritiEngine(aggressive=aggressive_forgetting)

    # Configure conscience layer
    memory.viveka = VivekaEngine()

    return memory