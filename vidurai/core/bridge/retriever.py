"""
Vidurai Retriever - LangChain Bridge

The Nervous System's connection to external LLM frameworks.
Transforms Vidurai context into LangChain-compatible Documents.

Glass Box Protocol: Inheritance Trap
- DO NOT import langchain at module level
- Use TYPE_CHECKING for type hints
- Wrap BaseRetriever inheritance in try/except
- Graceful degradation if langchain not installed

@version 2.1.0-Guardian
"""

from typing import TYPE_CHECKING, List, Dict, Any, Optional
from loguru import logger

# TYPE_CHECKING block - imports only during static analysis, not at runtime
if TYPE_CHECKING:
    from langchain_core.documents import Document
    from langchain_core.retrievers import BaseRetriever


# =============================================================================
# LANGCHAIN AVAILABILITY CHECK
# =============================================================================

_LANGCHAIN_AVAILABLE: Optional[bool] = None


def _check_langchain() -> bool:
    """
    Check if langchain is available (lazy, cached).

    Glass Box Protocol: Inheritance Trap
    - Only check once, cache result
    - Don't crash if missing
    """
    global _LANGCHAIN_AVAILABLE

    if _LANGCHAIN_AVAILABLE is None:
        try:
            import langchain_core  # noqa: F401
            _LANGCHAIN_AVAILABLE = True
        except ImportError:
            _LANGCHAIN_AVAILABLE = False
            logger.debug("LangChain not installed - ViduraiRetriever will use duck typing")

    return _LANGCHAIN_AVAILABLE


# =============================================================================
# DOCUMENT WRAPPER
# =============================================================================

class ViduraiDocument:
    """
    LangChain-compatible Document wrapper.

    If langchain is installed, this can be converted to a real Document.
    If not, this provides the same interface for duck typing.
    """

    def __init__(self, page_content: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize document.

        Args:
            page_content: The text content of the document
            metadata: Optional metadata dictionary
        """
        self.page_content = page_content
        self.metadata = metadata or {}

    def to_langchain_document(self) -> 'Document':
        """
        Convert to actual LangChain Document.

        Raises:
            ImportError: If langchain is not installed
        """
        from langchain_core.documents import Document
        return Document(
            page_content=self.page_content,
            metadata=self.metadata
        )

    def __repr__(self) -> str:
        content_preview = self.page_content[:50] + "..." if len(self.page_content) > 50 else self.page_content
        return f"ViduraiDocument(page_content='{content_preview}')"


# =============================================================================
# VIDURAI RETRIEVER
# =============================================================================

class ViduraiRetriever:
    """
    LangChain-compatible retriever for Vidurai context.

    Glass Box Protocol: Inheritance Trap
    - Uses duck typing instead of direct inheritance
    - If langchain is available, can be used as a retriever
    - If not, provides standalone functionality

    LangChain Integration:
    - Implements get_relevant_documents() interface
    - Returns List[Document] when langchain is available
    - Returns List[ViduraiDocument] when not

    Usage (with LangChain):
        from vidurai.core.bridge import ViduraiRetriever

        retriever = ViduraiRetriever()
        docs = retriever.get_relevant_documents("authentication")

        # Use with LangChain chain
        from langchain.chains import RetrievalQA
        qa = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)

    Usage (standalone):
        retriever = ViduraiRetriever()
        docs = retriever.invoke("authentication")
        for doc in docs:
            print(doc.page_content)
    """

    def __init__(
        self,
        audience: str = 'ai',
        include_memories: bool = True,
        memory_limit: int = 50,
        project_path: Optional[str] = None
    ):
        """
        Initialize ViduraiRetriever.

        Args:
            audience: Target audience for context ('developer', 'ai', 'manager')
            include_memories: Whether to include memories in context
            memory_limit: Max memories to include
            project_path: Project path to query
        """
        self.audience = audience
        self.include_memories = include_memories
        self.memory_limit = memory_limit
        self.project_path = project_path

        # Lazy-loaded controller
        self._controller = None

        logger.debug(f"ViduraiRetriever initialized (audience={audience})")

    @property
    def controller(self):
        """
        Lazy-load SearchController.

        Glass Box Protocol: Lazy Loading
        - Don't import at module level
        - Only load when needed
        """
        if self._controller is None:
            from vidurai.core.controllers.search_controller import get_controller
            self._controller = get_controller(project_path=self.project_path)
        return self._controller

    def _get_context_response(self, query: Optional[str] = None):
        """
        Get context from SearchController.

        Args:
            query: Optional query string (reserved for future semantic search)

        Returns:
            ContextResponse from SearchController
        """
        return self.controller.get_context(
            audience=self.audience,
            query=query,
            project_path=self.project_path,
            include_memories=self.include_memories,
            memory_limit=self.memory_limit
        )

    def _context_to_documents(
        self,
        context_response,
        query: Optional[str] = None
    ) -> List[ViduraiDocument]:
        """
        Transform ContextResponse into a list of Documents.

        Args:
            context_response: ContextResponse from SearchController
            query: The query used to retrieve context

        Returns:
            List of ViduraiDocument objects
        """
        documents = []

        if not context_response.success:
            logger.warning(f"Context retrieval failed: {context_response.error}")
            return documents

        # Main context document
        if context_response.formatted:
            doc = ViduraiDocument(
                page_content=context_response.formatted,
                metadata={
                    'source': 'vidurai',
                    'audience': context_response.audience,
                    'type': 'context',
                    'query': query,
                    'files_with_errors': context_response.files_with_errors,
                    'total_errors': context_response.total_errors,
                    'total_warnings': context_response.total_warnings,
                    'timestamp': context_response.timestamp,
                }
            )
            documents.append(doc)

        return documents

    def get_relevant_documents(self, query: str) -> List[Any]:
        """
        Get relevant documents for a query.

        This is the LangChain BaseRetriever interface.

        Args:
            query: The query string

        Returns:
            List of Document objects (LangChain or ViduraiDocument)
        """
        context_response = self._get_context_response(query)
        vidurai_docs = self._context_to_documents(context_response, query)

        # Convert to LangChain Documents if available
        if _check_langchain():
            try:
                return [doc.to_langchain_document() for doc in vidurai_docs]
            except Exception as e:
                logger.warning(f"Failed to convert to LangChain Documents: {e}")
                return vidurai_docs

        return vidurai_docs

    def invoke(self, input: str, **kwargs) -> List[Any]:
        """
        Invoke the retriever (LangChain Runnable interface).

        Args:
            input: The query string
            **kwargs: Additional arguments (ignored)

        Returns:
            List of Document objects
        """
        return self.get_relevant_documents(input)

    async def ainvoke(self, input: str, **kwargs) -> List[Any]:
        """
        Async invoke (LangChain Runnable interface).

        Note: Current implementation is synchronous.
        """
        return self.invoke(input, **kwargs)

    def _get_relevant_documents(self, query: str) -> List[Any]:
        """
        Internal method for BaseRetriever compatibility.

        Some LangChain versions call this instead of get_relevant_documents.
        """
        return self.get_relevant_documents(query)

    async def _aget_relevant_documents(self, query: str) -> List[Any]:
        """
        Async version for BaseRetriever compatibility.
        """
        return self.get_relevant_documents(query)

    def get_stats(self) -> Dict[str, Any]:
        """Get retriever statistics."""
        return {
            'audience': self.audience,
            'include_memories': self.include_memories,
            'memory_limit': self.memory_limit,
            'project_path': self.project_path,
            'langchain_available': _check_langchain(),
        }


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_retriever(
    audience: str = 'ai',
    **kwargs
) -> ViduraiRetriever:
    """
    Factory function to create a ViduraiRetriever.

    Usage:
        from vidurai.core.bridge.retriever import create_retriever

        retriever = create_retriever(audience='developer')
        docs = retriever.get_relevant_documents("authentication")
    """
    return ViduraiRetriever(audience=audience, **kwargs)


# =============================================================================
# CLI TEST INTERFACE
# =============================================================================

def _test_cli():
    """
    Test function for manual verification.

    Usage:
        python -m vidurai.core.bridge.retriever --test
    """
    import argparse

    parser = argparse.ArgumentParser(description="Vidurai Retriever Test")
    parser.add_argument("--test", action="store_true", help="Run test cases")
    parser.add_argument("--query", type=str, default="project context", help="Query to test")
    parser.add_argument("--stats", action="store_true", help="Show retriever stats")

    args = parser.parse_args()

    retriever = ViduraiRetriever()

    if args.stats:
        stats = retriever.get_stats()
        print("\n=== Retriever Statistics ===")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        return

    if args.test:
        print("\n=== Vidurai Retriever Test Cases ===\n")

        # Test 1: Check LangChain availability
        langchain_ok = _check_langchain()
        print(f"[{'PASS' if True else 'FAIL'}] LangChain check: {'available' if langchain_ok else 'not installed'}")

        # Test 2: Create retriever
        try:
            r = ViduraiRetriever(audience='ai')
            print("[PASS] Create retriever")
        except Exception as e:
            print(f"[FAIL] Create retriever: {e}")
            return

        # Test 3: Get stats
        stats = r.get_stats()
        print(f"[{'PASS' if stats else 'FAIL'}] Get stats: audience={stats.get('audience')}")

        # Test 4: Get documents (may fail if no DB)
        try:
            docs = r.get_relevant_documents(args.query)
            print(f"[PASS] Get documents: {len(docs)} document(s)")
            if docs:
                print(f"       First doc type: {type(docs[0]).__name__}")
                preview = docs[0].page_content[:100] if docs[0].page_content else "(empty)"
                print(f"       Preview: {preview}...")
        except Exception as e:
            print(f"[WARN] Get documents failed (expected if no DB): {e}")

        # Test 5: Invoke interface
        try:
            docs = r.invoke(args.query)
            print(f"[PASS] Invoke interface: {len(docs)} document(s)")
        except Exception as e:
            print(f"[WARN] Invoke failed: {e}")

        print()


if __name__ == "__main__":
    _test_cli()
