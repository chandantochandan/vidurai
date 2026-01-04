"""
Vidurai Controllers - The Brain Layer (Glass Box Protocols)

Controllers are the SINGLE source of business logic.
API routes are DUMB wrappers that only call Controllers.

Prime Directive: No Split Brains
- Logic NEVER lives in API routes
- All logic MUST exist in controllers

@version 2.1.0-Guardian
"""

from vidurai.core.controllers.search_controller import (
    get_context,
    get_context_for_audience,
    SearchController,
)

__all__ = [
    'get_context',
    'get_context_for_audience',
    'SearchController',
]
