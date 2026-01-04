"""
Memory Bridge
Bridges daemon's ephemeral state with SQL's long-term memory

Philosophy: "The daemon remembers sessions, SQL remembers history"
विस्मृति भी विद्या है (Forgetting too is knowledge)
"""

import os
import re
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger("vidurai.memory_bridge")


class MemoryBridge:
    """
    Bridges daemon's Project Brain (JSON) with main package's Memory Database (SQL)

    Purpose:
    - Pull 3-5 HIGH/CRITICAL salience memories from SQL
    - Provide long-term context hints to daemon
    - Respect strict token budgets
    - Fail-safe: daemon works without SQL

    Example:
        Current error: "AuthenticationError in auth.py"
        SQL hint: "You hit a similar error 3 days ago when JWT secret was misconfigured"
    """

    def __init__(
        self,
        db,  # MemoryDatabase instance
        max_memories: int = 3,
        min_salience: str = "HIGH",
        audience: Optional[str] = None  # Phase 5: Multi-Audience
    ):
        """
        Initialize memory bridge

        Args:
            db: MemoryDatabase instance from vidurai.storage.database
            max_memories: Maximum memories to return (default: 3)
            min_salience: Minimum salience level (default: HIGH)
            audience: Optional audience perspective (developer, ai, manager, personal) - Phase 5
        """
        self.db = db
        self.max_memories = max_memories
        self.min_salience = min_salience
        self.audience = audience  # Phase 5: Multi-Audience

        logger.info(
            f"Memory bridge initialized "
            f"(max_memories: {max_memories}, min_salience: {min_salience}, "
            f"audience: {audience or 'canonical'})"
        )

    def get_relevant_hints(
        self,
        current_project: str,
        current_error: Optional[str] = None,
        current_file: Optional[str] = None,
        user_state: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get relevant long-term memory hints from SQL

        Priority-based querying:
        1. If debugging: Find similar past errors
        2. If working on file: Find past context about that file
        3. General: Find recent high-salience memories

        Args:
            current_project: Project path
            current_error: Current error message (if debugging)
            current_file: Current file being worked on
            user_state: Current user state (debugging, building, etc.)

        Returns:
            List of 0-3 memory dicts with hints
        """
        try:
            hints = []

            # Priority 1: Similar errors (if debugging)
            if current_error and user_state == 'debugging':
                error_hints = self._find_similar_errors(
                    current_project,
                    current_error
                )
                hints.extend(error_hints[:2])  # Max 2 error hints

            # Priority 2: File-specific memories (if working on file)
            if current_file and len(hints) < self.max_memories:
                file_hints = self._find_file_memories(
                    current_project,
                    current_file
                )
                remaining = self.max_memories - len(hints)
                hints.extend(file_hints[:remaining])

            # Priority 3: Recent high-salience memories
            if len(hints) < self.max_memories:
                general_hints = self._find_recent_high_salience(
                    current_project
                )
                remaining = self.max_memories - len(hints)
                hints.extend(general_hints[:remaining])

            # Phase 5: Enrich with audience-specific gists if requested
            if self.audience:
                hints = self._enrich_with_audience_gists(hints)

            logger.debug(f"Found {len(hints)} relevant hints for {current_project}")
            return hints[:self.max_memories]

        except Exception as e:
            logger.warning(f"Failed to get SQL hints: {e}")
            return []  # Fail-safe: return empty list

    def _enrich_with_audience_gists(self, hints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrich hints with audience-specific gists (Phase 5)

        Args:
            hints: List of memory dicts

        Returns:
            Same list but with gists replaced by audience-specific versions
        """
        if not self.audience:
            return hints

        try:
            for hint in hints:
                memory_id = hint.get('id')
                if not memory_id:
                    continue

                # Get audience gist
                audience_gists = self.db.get_audience_gists(
                    memory_id,
                    audiences=[self.audience]
                )

                if self.audience in audience_gists:
                    hint['gist'] = audience_gists[self.audience]
                    hint['_audience'] = self.audience  # Mark as audience-enriched

            logger.debug(
                f"Enriched {len(hints)} hints with {self.audience} perspective"
            )

        except Exception as e:
            logger.warning(f"Failed to enrich with audience gists: {e}")
            # Fail-safe: return original hints

        return hints

    def _find_similar_errors(
        self,
        project_path: str,
        error_message: str
    ) -> List[Dict[str, Any]]:
        """
        Find memories of similar past errors

        Extracts error type and searches for matches
        """
        try:
            # Extract error type from message
            error_type = self._extract_error_type(error_message)

            if not error_type:
                return []

            # Query for similar errors
            results = self.db.recall_memories(
                project_path=project_path,
                query=error_type,
                min_salience=self._salience_to_enum(self.min_salience),
                limit=self.max_memories
            )

            # Filter for actual errors (not solutions)
            error_memories = [
                mem for mem in results
                if self._is_error_memory(mem)
            ]

            logger.debug(
                f"Found {len(error_memories)} similar error memories "
                f"for '{error_type}'"
            )

            return error_memories

        except Exception as e:
            logger.warning(f"Error finding similar errors: {e}")
            return []

    def _find_file_memories(
        self,
        project_path: str,
        file_path: str
    ) -> List[Dict[str, Any]]:
        """
        Find memories related to a specific file

        Args:
            project_path: Project path
            file_path: Full file path or just filename

        Returns:
            List of memories about this file
        """
        try:
            # Extract just the filename
            filename = os.path.basename(file_path)

            # Query database
            results = self.db.recall_memories(
                project_path=project_path,
                query=filename,
                min_salience=self._salience_to_enum(self.min_salience),
                limit=self.max_memories
            )

            # Filter for memories that actually mention this file
            file_memories = [
                mem for mem in results
                if filename in (mem.get('file_path', '') or mem.get('gist', ''))
            ]

            logger.debug(
                f"Found {len(file_memories)} memories about '{filename}'"
            )

            return file_memories

        except Exception as e:
            logger.warning(f"Error finding file memories: {e}")
            return []

    def _find_recent_high_salience(
        self,
        project_path: str
    ) -> List[Dict[str, Any]]:
        """
        Find recent high-salience memories (general context)

        Returns memories that are:
        - HIGH or CRITICAL salience
        - Created or accessed recently
        - Relevant to project
        """
        try:
            results = self.db.recall_memories(
                project_path=project_path,
                query="",  # No specific query, just high salience
                min_salience=self._salience_to_enum(self.min_salience),
                limit=self.max_memories
            )

            logger.debug(
                f"Found {len(results)} recent high-salience memories"
            )

            return results

        except Exception as e:
            logger.warning(f"Error finding recent high-salience: {e}")
            return []

    def _extract_error_type(self, error_message: str) -> Optional[str]:
        """
        Extract error type from error message

        Examples:
        - "TypeError: Cannot read property" → "TypeError"
        - "AuthenticationError in auth.py" → "AuthenticationError"
        - "Error: File not found" → "File not found"
        """
        # Common error patterns
        patterns = [
            r'(\w+Error)',  # PythonError, TypeError, etc.
            r'(\w+Exception)',  # Various exceptions
            r'Error:\s*(.+?)(?:\.|$)',  # "Error: message"
            r'Failed to (.+?)(?:\.|$)',  # "Failed to..."
        ]

        for pattern in patterns:
            match = re.search(pattern, error_message, re.IGNORECASE)
            if match:
                error_type = match.group(1).strip()
                logger.debug(f"Extracted error type: '{error_type}'")
                return error_type

        # Fallback: use first few words
        words = error_message.split()[:3]
        if words:
            return ' '.join(words)

        return None

    def _is_error_memory(self, memory: Dict[str, Any]) -> bool:
        """
        Check if memory is about an error (not a solution)

        Error memories contain keywords like:
        - error, exception, failed, crash
        - But NOT: fixed, solved, resolved
        """
        gist = memory.get('gist', '').lower()
        verbatim = memory.get('verbatim', '').lower()
        combined = f"{gist} {verbatim}"

        # Error indicators
        error_keywords = [
            'error', 'exception', 'failed', 'crash', 'bug',
            'broken', 'issue', 'problem'
        ]

        # Solution indicators (exclude these)
        solution_keywords = [
            'fixed', 'solved', 'resolved', 'solution',
            'fix', 'works now', 'working'
        ]

        has_error = any(kw in combined for kw in error_keywords)
        has_solution = any(kw in combined for kw in solution_keywords)

        # It's an error memory if it mentions errors but not solutions
        return has_error and not has_solution

    def _salience_to_enum(self, salience_str: str):
        """Convert salience string to enum"""
        try:
            from vidurai.storage.database import SalienceLevel
            return SalienceLevel[salience_str.upper()]
        except:
            # Default to HIGH if conversion fails
            from vidurai.storage.database import SalienceLevel
            return SalienceLevel.HIGH

    def format_hint_for_context(
        self,
        hint: Dict[str, Any],
        include_age: bool = True
    ) -> str:
        """
        Format a single hint for natural language context

        Args:
            hint: Memory dict from database
            include_age: Include "X days ago" timestamp

        Returns:
            Formatted string like "Fixed auth bug (3d ago)"
        """
        gist = hint.get('gist', 'Unknown memory')

        # Calculate age
        if include_age:
            try:
                created_at = datetime.fromisoformat(hint['created_at'])
                age = datetime.now() - created_at

                if age.days > 0:
                    age_text = f"{age.days}d ago"
                elif age.seconds >= 3600:
                    hours = age.seconds // 3600
                    age_text = f"{hours}h ago"
                else:
                    mins = age.seconds // 60
                    age_text = f"{mins}m ago"

                return f"{gist} ({age_text})"
            except:
                return gist
        else:
            return gist

    def format_hints_for_context(
        self,
        hints: List[Dict[str, Any]]
    ) -> str:
        """
        Format multiple hints as a natural language string

        Returns formatted string like:
        "From past experience: Fixed auth bug (3d ago); Similar error in login (7d ago)"
        """
        if not hints:
            return ""

        formatted_hints = [
            self.format_hint_for_context(hint)
            for hint in hints
        ]

        return "From past experience: " + "; ".join(formatted_hints)

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about memory bridge usage"""
        try:
            # Get database stats
            db_stats = self.db.get_statistics(".")  # All projects

            return {
                'enabled': True,
                'max_memories': self.max_memories,
                'min_salience': self.min_salience,
                'total_memories_in_db': db_stats.get('total', 0),
                'high_salience_count': db_stats.get('by_salience', {}).get('HIGH', 0),
                'critical_salience_count': db_stats.get('by_salience', {}).get('CRITICAL', 0),
            }
        except Exception as e:
            logger.warning(f"Error getting statistics: {e}")
            return {
                'enabled': False,
                'error': str(e)
            }
