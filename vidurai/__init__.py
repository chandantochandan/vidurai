"""
Vidurai - Teaching AI the Art of Memory and Forgetting
A Vedantic approach to AI memory management

विस्मृति भी विद्या है (Forgetting too is knowledge)
"""

# Legacy API (v1.5.x)
from vidurai.core.koshas import ViduraiMemory, Memory
from vidurai.core.vismriti import VismritiEngine, ForgettingPolicy
from vidurai.core.viveka import VivekaEngine

# New API (v1.6.0 - Vismriti Architecture)
from vidurai.vismriti_memory import VismritiMemory
from vidurai.core.data_structures_v3 import (
    Memory as VismritiMemoryObject,
    SalienceLevel,
    MemoryStatus
)

__version__ = "1.6.1"  # Patch: Added pandas dependency
__author__ = "Vidurai Team"

# Export main classes
__all__ = [
    # Legacy v1.5.x (still supported)
    "ViduraiMemory",
    "Memory",
    "VismritiEngine",
    "ForgettingPolicy",
    "VivekaEngine",
    "create_memory_system",

    # New v1.6.0 (Vismriti Architecture)
    "VismritiMemory",
    "VismritiMemoryObject",
    "SalienceLevel",
    "MemoryStatus",
]

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
    memory = ViduraiMemory()
    memory.working.capacity = working_capacity
    memory.episodic.capacity = episodic_capacity
    
    # Configure forgetting engine
    memory.vismriti = VismritiEngine(aggressive=aggressive_forgetting)
    
    # Configure conscience layer
    memory.viveka = VivekaEngine()
    
    return memory


# LangChain Integration (optional import)
try:
    from vidurai.integrations.langchain import ViduraiMemory as LangChainViduraiMemory, ViduraiConversationChain
    __all__.extend(["LangChainViduraiMemory", "ViduraiConversationChain"])
except ImportError:
    # LangChain not installed - integrations not available
    pass