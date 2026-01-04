"""
Search Controller - The SINGLE Entry Point for Context Retrieval

Glass Box Protocol: No Split Brains
- This is the ONLY place where Oracle.get_context() should be called
- API routes, daemon handlers, CLI commands all use THIS controller
- Logic centralization prevents divergent behavior

@version 2.1.0-Guardian
"""

import logging
from typing import Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass, asdict

if TYPE_CHECKING:
    from vidurai.core.oracle import Oracle
    from vidurai.vismriti_memory import VismritiMemory

logger = logging.getLogger("vidurai.controller.search")


# =============================================================================
# RESPONSE TYPES
# =============================================================================

@dataclass
class ContextResponse:
    """
    Standardized context response from SearchController.

    All consumers (daemon, proxy, CLI) receive this same structure.
    """
    success: bool
    audience: str
    formatted: str
    files_with_errors: int
    total_errors: int
    total_warnings: int
    timestamp: str
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


# =============================================================================
# SEARCH CONTROLLER
# =============================================================================

class SearchController:
    """
    The Brain for Context Retrieval.

    Glass Box Protocol:
    - SINGLE entry point for all context queries
    - Wraps Oracle with standardized error handling
    - Provides consistent response format across all consumers

    Usage:
        # Daemon
        controller = SearchController(brain_instance=vismriti_brain)
        result = controller.get_context('ai')

        # Or use module-level convenience function
        from vidurai.core.controllers import get_context
        result = get_context('developer', brain_instance=brain)
    """

    def __init__(
        self,
        brain_instance: Optional['VismritiMemory'] = None,
        project_path: Optional[str] = None,
        whisperer: Optional[Any] = None,
        pin_manager: Optional[Any] = None
    ):
        """
        Initialize SearchController.

        Args:
            brain_instance: VismritiMemory instance for dynamic DB access
            project_path: Default project path
            whisperer: Optional HumanAIWhisperer for narrative generation
            pin_manager: Optional MemoryPinManager for pins
        """
        self._brain = brain_instance
        self._project_path = project_path
        self._whisperer = whisperer
        self._pin_manager = pin_manager
        self._oracle: Optional['Oracle'] = None

    @property
    def oracle(self) -> 'Oracle':
        """
        Lazy-load Oracle instance.

        Glass Box Protocol: Lazy Loading
        - Heavy imports only when needed
        - Startup time < 200ms requirement
        """
        if self._oracle is None:
            # Lazy import (Glass Box: No heavy imports at module level)
            from vidurai.core.oracle import Oracle

            self._oracle = Oracle(
                brain_instance=self._brain,
                project_path=self._project_path,
                whisperer=self._whisperer,
                pin_manager=self._pin_manager
            )
        return self._oracle

    def update_brain(self, brain_instance: 'VismritiMemory') -> None:
        """
        Update brain instance (for context switching).

        Called by daemon when project context changes.
        """
        self._brain = brain_instance
        if self._oracle:
            self._oracle._brain = brain_instance

    def update_dependencies(
        self,
        whisperer: Optional[Any] = None,
        pin_manager: Optional[Any] = None
    ) -> None:
        """
        Update optional dependencies.

        Called by daemon to inject whisperer/pin_manager.
        """
        if whisperer is not None:
            self._whisperer = whisperer
            if self._oracle:
                self._oracle._whisperer = whisperer

        if pin_manager is not None:
            self._pin_manager = pin_manager
            if self._oracle:
                self._oracle._pin_manager = pin_manager

    def get_context(
        self,
        audience: str = 'developer',
        query: Optional[str] = None,
        project_path: Optional[str] = None,
        include_memories: Optional[bool] = None,
        memory_limit: int = 50,
        include_raw: bool = False
    ) -> ContextResponse:
        """
        Get context for a specific audience.

        This is the SINGLE entry point for context retrieval.
        All API routes, daemon handlers, CLI commands use this method.

        Args:
            audience: Target audience ('developer', 'ai', 'manager')
            query: Optional query to filter context (future use)
            project_path: Project to query (uses default if None)
            include_memories: Override profile default for memories
            memory_limit: Max memories to include
            include_raw: Include raw data in response

        Returns:
            ContextResponse with standardized format
        """
        try:
            # Get context from Oracle (the actual logic)
            oracle_ctx = self.oracle.get_context(
                audience=audience,
                project_path=project_path,
                include_raw=include_raw,
                include_memories=include_memories,
                memory_limit=memory_limit
            )

            return ContextResponse(
                success=True,
                audience=oracle_ctx.audience,
                formatted=oracle_ctx.formatted,
                files_with_errors=oracle_ctx.files_with_errors,
                total_errors=oracle_ctx.total_errors,
                total_warnings=oracle_ctx.total_warnings,
                timestamp=oracle_ctx.timestamp,
                error=None
            )

        except Exception as e:
            logger.error(f"SearchController.get_context failed: {e}")

            # Return error response (never throw, always return)
            return ContextResponse(
                success=False,
                audience=audience,
                formatted=f"Error retrieving context: {str(e)}",
                files_with_errors=0,
                total_errors=0,
                total_warnings=0,
                timestamp="",
                error=str(e)
            )

    def get_dashboard_summary(
        self,
        project_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get dashboard summary for Glass Box UI.

        Returns data formatted for VS Code Context Dashboard.
        """
        try:
            return self.oracle.get_dashboard_summary(
                project_path=project_path,
                pin_manager=self._pin_manager
            )
        except Exception as e:
            logger.error(f"SearchController.get_dashboard_summary failed: {e}")
            return {
                'pinned': [],
                'active_errors': [],
                'token_budget': {'used': 0, 'total': 8000},
                'error': str(e)
            }

    def get_summary(self, project_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Get quick summary without formatting.
        """
        try:
            return self.oracle.get_summary(project_path)
        except Exception as e:
            logger.error(f"SearchController.get_summary failed: {e}")
            return {
                'files_with_errors': 0,
                'total_errors': 0,
                'total_warnings': 0,
                'error': str(e)
            }


# =============================================================================
# MODULE-LEVEL CONVENIENCE FUNCTIONS
# =============================================================================

# Singleton controller instance
_default_controller: Optional[SearchController] = None


def get_controller(
    brain_instance: Optional['VismritiMemory'] = None,
    project_path: Optional[str] = None,
    whisperer: Optional[Any] = None,
    pin_manager: Optional[Any] = None
) -> SearchController:
    """
    Get or create the default SearchController instance.

    Updates dependencies if provided (allows dynamic injection).
    """
    global _default_controller

    if _default_controller is None:
        _default_controller = SearchController(
            brain_instance=brain_instance,
            project_path=project_path,
            whisperer=whisperer,
            pin_manager=pin_manager
        )
    else:
        # Update dependencies if provided
        if brain_instance is not None:
            _default_controller.update_brain(brain_instance)
        _default_controller.update_dependencies(
            whisperer=whisperer,
            pin_manager=pin_manager
        )

    return _default_controller


def get_context(
    audience: str = 'developer',
    query: Optional[str] = None,
    brain_instance: Optional['VismritiMemory'] = None,
    project_path: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Convenience function for getting context.

    This is the recommended entry point for most use cases.

    Args:
        audience: Target audience ('developer', 'ai', 'manager')
        query: Optional query string (future use)
        brain_instance: VismritiMemory instance
        project_path: Project path
        **kwargs: Additional arguments passed to controller

    Returns:
        Dict with context data (ContextResponse.to_dict())

    Example:
        from vidurai.core.controllers import get_context

        ctx = get_context('ai', brain_instance=brain)
        print(ctx['formatted'])
    """
    controller = get_controller(
        brain_instance=brain_instance,
        project_path=project_path
    )

    response = controller.get_context(
        audience=audience,
        query=query,
        project_path=project_path,
        **kwargs
    )

    return response.to_dict()


def get_context_for_audience(
    audience: str,
    brain_instance: Optional['VismritiMemory'] = None,
    **kwargs
) -> str:
    """
    Get formatted context string for a specific audience.

    Simplified API for common use case.

    Returns:
        Formatted context string
    """
    result = get_context(
        audience=audience,
        brain_instance=brain_instance,
        **kwargs
    )
    return result.get('formatted', '')


def reset_controller() -> None:
    """Reset the default controller instance."""
    global _default_controller
    _default_controller = None
