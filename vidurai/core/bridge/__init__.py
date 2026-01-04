"""
Vidurai Bridge Module - LangChain Integration

Provides ViduraiRetriever for seamless LangChain RAG integration.

Glass Box Protocol: Inheritance Trap
- LangChain BaseRetriever wrapped in TYPE_CHECKING
- Graceful degradation if langchain not installed
- Lazy loading of heavy dependencies

@version 2.1.0-Guardian
"""

from vidurai.core.bridge.retriever import ViduraiRetriever

__all__ = ['ViduraiRetriever']
