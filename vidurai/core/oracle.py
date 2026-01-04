"""
Context Oracle - Read API for Current State

Provides formatted context about current file states for different audiences:
- Developer: Human-readable list of files with errors
- AI: XML-structured context for AI assistants
- Manager: High-level summary for status reports (with optional "WOW" narrative via Whisperer)

Queries the active_state table to provide "Current Truth" -
only active errors, no zombies from the past.

@version 2.1.0
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, TYPE_CHECKING, Protocol, Union
from dataclasses import dataclass
from pathlib import Path

if TYPE_CHECKING:
    from vidurai.storage.database import MemoryDatabase

logger = logging.getLogger("vidurai.oracle")


# =============================================================================
# WHISPERER PROTOCOL (Cross-Package Rule: Use Protocol for type hints)
# =============================================================================

class WhispererProtocol(Protocol):
    """Protocol for HumanAIWhisperer - allows dependency injection without import."""
    def create_wow_context(self, user_input: str, recent_activity: Dict) -> str: ...


# =============================================================================
# TYPES
# =============================================================================

@dataclass
class OracleContext:
    """Context response from Oracle"""
    audience: str
    formatted: str
    files_with_errors: int
    total_errors: int
    total_warnings: int
    timestamp: str
    raw_data: Optional[List[Dict]] = None


# =============================================================================
# ORACLE CLASS
# =============================================================================

class Oracle:
    """
    Context Oracle - queries active_state and formats for different audiences.

    The Oracle answers one question: "What is the current state of my project?"

    v2.5: Audience Profiles Architecture
    ------------------------------------
    Instead of guessing flags, the Oracle defines a Data Requirement Profile
    for each audience persona:

    - Developer: Needs Current Reality (Active Errors + Pins). No History.
    - Manager: Needs Narrative History (Recent Memories + Summary). No Stack Traces.
    - AI: Needs Everything (History + Errors + Pins + Code).

    Example:
        oracle = Oracle(brain_instance=vismriti_brain)

        # For developers (human-readable)
        ctx = oracle.get_context('developer')
        print(ctx.formatted)

        # For AI assistants (XML format)
        ctx = oracle.get_context('ai')
        print(ctx.formatted)  # <context>...</context>

        # For managers (WOW narrative via Whisperer)
        ctx = oracle.get_context('manager')
        print(ctx.formatted)  # Story-style summary
    """

    # =========================================================================
    # v2.5: AUDIENCE PROFILES - The Smart Selector
    # =========================================================================
    # Each profile defines what data to fetch for each persona.
    # Client can override with explicit include_memories=True/False (Rule I: User Veto)
    #
    # Keys:
    #   memories: bool - Fetch recent memories from DB
    #   errors: bool - Fetch active errors from active_state
    #   pins: bool - Fetch pinned memories
    #   salience: str - Minimum salience level for memory queries ('HIGH', 'MEDIUM', 'LOW')
    # =========================================================================
    AUDIENCE_PROFILES: Dict[str, Dict[str, Any]] = {
        'developer': {'memories': False, 'errors': True,  'pins': True,  'salience': 'HIGH'},
        'manager':   {'memories': True,  'errors': False, 'pins': True,  'salience': 'MEDIUM'},
        'ai':        {'memories': True,  'errors': True,  'pins': True,  'salience': 'LOW'},
        'default':   {'memories': False, 'errors': True,  'pins': True,  'salience': 'MEDIUM'}
    }

    def __init__(
        self,
        brain_instance: Optional[Any] = None,
        project_path: Optional[str] = None,
        whisperer: Optional[WhispererProtocol] = None,
        pin_manager: Optional[Any] = None,
        database: Optional['MemoryDatabase'] = None  # Deprecated, use brain_instance
    ):
        """
        Initialize Oracle.

        Args:
            brain_instance: VismritiMemory instance for dynamic DB access
            project_path: Default project path for queries
            whisperer: Optional HumanAIWhisperer instance for narrative generation
                      (Cross-Package Rule: Injected from daemon, not imported here)
            pin_manager: Optional MemoryPinManager instance for fetching pins
                        (Cross-Package Rule: Injected from daemon)
            database: DEPRECATED - Use brain_instance instead
        """
        self._brain = brain_instance
        self._db = database  # Fallback for backwards compatibility
        self._project_path = project_path
        self._whisperer = whisperer  # Injected, not imported (Cross-Package Rule)
        self._pin_manager = pin_manager  # v2.5: Injected for Audience Profiles

    @property
    def db(self) -> 'MemoryDatabase':
        """Dynamic access to current project DB via brain instance"""
        if self._brain is not None and hasattr(self._brain, 'db'):
            return self._brain.db
        return self._fallback_db

    @property
    def _fallback_db(self) -> 'MemoryDatabase':
        """Fallback database when brain not available"""
        if self._db is None:
            from vidurai.storage.database import MemoryDatabase
            self._db = MemoryDatabase()
        return self._db

    @property
    def database(self) -> 'MemoryDatabase':
        """Get or lazy-load database (uses db property for dynamic access)"""
        return self.db

    @property
    def project_path(self) -> Optional[str]:
        """Dynamic access to current project path via brain instance"""
        if self._brain is not None and hasattr(self._brain, 'project_path'):
            return self._brain.project_path
        return self._project_path

    # -------------------------------------------------------------------------
    # v2.5 Vision Fix: Memory Access
    # -------------------------------------------------------------------------

    def _fetch_memories(
        self,
        limit: int = 50,
        min_salience: str = 'LOW'
    ) -> List[Dict[str, Any]]:
        """
        Fetch recent memories for context inclusion.

        Uses brain's project_path for correct project scoping.
        Falls back gracefully if brain not available.

        Args:
            limit: Maximum memories to fetch
            min_salience: Minimum salience level ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'NOISE')

        Returns:
            List of memory dicts with gist, salience, file_path
        """
        try:
            # Get project_path from brain (auto-refreshed on context switch)
            project_path = self.project_path  # Uses property that checks brain first

            if not project_path:
                logger.debug("No project_path available for memory fetch")
                return []

            # Rule II: Cast salience string to SalienceLevel Enum
            from vidurai.storage.database import SalienceLevel
            try:
                salience_enum = SalienceLevel[min_salience.upper()]
            except KeyError:
                logger.warning(f"Invalid salience '{min_salience}', defaulting to MEDIUM")
                salience_enum = SalienceLevel.MEDIUM

            memories = self.database.recall_memories(
                project_path=project_path,
                min_salience=salience_enum,
                limit=limit
            )

            logger.debug(f"Fetched {len(memories)} memories (salience>={min_salience}, project={project_path})")
            return memories

        except Exception as e:
            # Do No Harm: Log and return empty list
            logger.warning(f"Error fetching memories for context: {e}")
            return []

    def _fetch_pins(self, project_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch pinned memories for context inclusion.

        Args:
            project_path: Project path (uses default if None)

        Returns:
            List of pinned memory dicts
        """
        try:
            project = project_path or self.project_path
            if not project:
                logger.debug("No project_path available for pin fetch")
                return []

            if not self._pin_manager:
                logger.debug("No pin_manager available")
                return []

            pins = self._pin_manager.get_pinned_memories(project)
            logger.debug(f"Fetched {len(pins)} pinned memories (project={project})")
            return pins

        except Exception as e:
            # Do No Harm: Log and return empty list
            logger.warning(f"Error fetching pins for context: {e}")
            return []

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def get_context(
        self,
        audience: str = 'developer',
        project_path: Optional[str] = None,
        include_raw: bool = False,
        include_memories: Optional[bool] = None,
        memory_limit: int = 50
    ) -> OracleContext:
        """
        Get context formatted for a specific audience.

        v2.5: Audience Profiles Architecture
        ------------------------------------
        The Oracle now uses AUDIENCE_PROFILES to determine what data to fetch
        based on the audience. Client can override with explicit include_memories.

        Args:
            audience: Target audience ('developer', 'ai', 'manager')
            project_path: Project to query (uses default if None)
            include_raw: Include raw file data in response
            include_memories: Override profile default for memories
                             None = use profile default
                             True/False = explicit override (Rule I: User Veto)
            memory_limit: Max memories to include when fetching memories

        Returns:
            OracleContext with formatted output
        """
        project = project_path or self.project_path

        # =====================================================================
        # 1. LOAD PROFILE (The Smart Selector)
        # =====================================================================
        profile = self.AUDIENCE_PROFILES.get(audience, self.AUDIENCE_PROFILES['default'])

        # Rule I (User Veto): Client override > Profile default
        fetch_memories = include_memories if include_memories is not None else profile['memories']
        fetch_errors = profile['errors']
        fetch_pins = profile['pins']
        min_salience = profile['salience']

        logger.debug(
            f"[Oracle] Profile '{audience}': memories={fetch_memories}, "
            f"errors={fetch_errors}, pins={fetch_pins}, salience={min_salience}"
        )

        # =====================================================================
        # 2. GATHER DATA (Profile-Driven)
        # =====================================================================
        context_data: Dict[str, Any] = {
            'errors': [],
            'pins': [],
            'memories': [],
            'summary': {'files_with_errors': 0, 'total_errors': 0, 'total_warnings': 0}
        }

        # A. Active State (Errors) - Always fetch summary for response stats
        summary = self.database.get_active_state_summary(project)
        context_data['summary'] = summary

        if fetch_errors:
            context_data['errors'] = self.database.get_files_with_errors(project)

        # B. Pins (Control)
        if fetch_pins:
            context_data['pins'] = self._fetch_pins(project)

        # C. Memories (History)
        if fetch_memories:
            context_data['memories'] = self._fetch_memories(
                limit=memory_limit,
                min_salience=min_salience
            )

        # =====================================================================
        # 3. FORMAT OUTPUT (Audience-Specific Rendering)
        # =====================================================================
        if audience == 'ai':
            formatted = self._format_for_ai(
                context_data['errors'],
                context_data['summary'],
                context_data['memories'],
                context_data['pins']
            )
        elif audience == 'manager':
            formatted = self._format_for_manager(
                context_data['errors'],
                context_data['summary'],
                context_data['memories']
            )
        else:  # developer (default)
            formatted = self._format_for_developer(
                context_data['errors'],
                context_data['summary'],
                context_data['pins']
            )

        return OracleContext(
            audience=audience,
            formatted=formatted,
            files_with_errors=summary['files_with_errors'],
            total_errors=summary['total_errors'],
            total_warnings=summary['total_warnings'],
            timestamp=datetime.now().isoformat(),
            raw_data=context_data['errors'] if include_raw else None
        )

    def get_file_context(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get context for a specific file.

        Args:
            file_path: Path to the file

        Returns:
            File state dict or None if no active issues
        """
        return self.database.get_file_state(file_path)

    def get_summary(self, project_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Get quick summary without formatting.

        Args:
            project_path: Project to query

        Returns:
            Summary dict with counts
        """
        return self.database.get_active_state_summary(
            project_path or self.project_path
        )

    def get_dashboard_summary(
        self,
        project_path: Optional[str] = None,
        pin_manager: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Get dashboard summary for Glass Box UI.

        Returns data formatted for the VS Code Context Dashboard:
        - pinned: List of pinned files with paths and reasons
        - active_errors: List of files with error counts
        - token_budget: Estimated token usage

        Args:
            project_path: Project to query
            pin_manager: MemoryPinManager instance for getting pins

        Returns:
            Dashboard summary dict matching UI spec
        """
        project = project_path or self.project_path

        # Get pinned files
        pinned_items = []
        if pin_manager:
            try:
                pinned_memories = pin_manager.get_pinned_memories(project or '')
                for mem in pinned_memories:
                    pinned_items.append({
                        'file_path': mem.get('file_path', ''),
                        'reason': mem.get('reason', 'pinned'),
                        'pinned_at': mem.get('pinned_at', '')
                    })
            except Exception as e:
                logger.warning(f"Error getting pinned memories: {e}")

        # Get active errors from active_state table
        active_errors = []
        try:
            files_with_errors = self.database.get_files_with_errors(project)
            for f in files_with_errors:
                active_errors.append({
                    'file_path': f.get('file_path', ''),
                    'error_count': f.get('error_count', 0),
                    'warning_count': f.get('warning_count', 0),
                    'error_summary': f.get('error_summary', '')
                })
        except Exception as e:
            logger.warning(f"Error getting active errors: {e}")

        # Calculate rough token budget (estimate 100 tokens per item)
        pinned_tokens = len(pinned_items) * 100
        error_tokens = len(active_errors) * 100
        used_tokens = pinned_tokens + error_tokens

        return {
            'pinned': pinned_items,
            'active_errors': active_errors,
            'token_budget': {
                'used': used_tokens,
                'total': 8000  # Default budget
            }
        }

    # -------------------------------------------------------------------------
    # Formatting Methods
    # -------------------------------------------------------------------------

    def _format_for_developer(
        self,
        files: List[Dict[str, Any]],
        summary: Dict[str, Any],
        pins: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Format context for developers (human-readable).

        v2.5: Now includes pinned files section.

        Output:
            Project Status: 3 files with errors (5 errors, 2 warnings)

            Pinned Files (2):
            - src/config.ts (pinned)
            - src/constants.ts (pinned)

            Files with issues:
            - src/auth.ts: 2 errors - "Type error in JWT validation"
            - src/api.ts: 1 error, 1 warning - "Missing return type"
        """
        pins = pins or []
        lines = []

        # Header
        error_count = summary.get('total_errors', 0)
        warning_count = summary.get('total_warnings', 0)
        file_count = summary.get('files_with_errors', 0)

        if not files and not pins:
            return "Project Status: All clear! No active errors or warnings."

        if files:
            header_parts = []
            if error_count > 0:
                header_parts.append(f"{error_count} error{'s' if error_count != 1 else ''}")
            if warning_count > 0:
                header_parts.append(f"{warning_count} warning{'s' if warning_count != 1 else ''}")

            lines.append(f"Project Status: {file_count} file{'s' if file_count != 1 else ''} with issues ({', '.join(header_parts)})")
        else:
            lines.append("Project Status: No active errors")

        # Pinned files section
        if pins:
            lines.append("")
            lines.append(f"Pinned Files ({len(pins)}):")
            for pin in pins[:10]:  # Limit to 10 pins
                file_path = pin.get('file_path', '')
                file_name = Path(file_path).name if file_path else 'Unknown'
                lines.append(f"  - {file_name} (pinned)")
            if len(pins) > 10:
                lines.append(f"  ... and {len(pins) - 10} more pinned files")

        # Files with errors
        if files:
            lines.append("")
            lines.append("Files with issues:")

            for f in files[:20]:  # Limit to 20 files
                file_name = Path(f['file_path']).name
                errors = f.get('error_count', 0)
                warnings = f.get('warning_count', 0)
                summary_text = f.get('error_summary', '')[:60] or 'Unknown issue'

                issue_parts = []
                if errors > 0:
                    issue_parts.append(f"{errors} error{'s' if errors != 1 else ''}")
                if warnings > 0:
                    issue_parts.append(f"{warnings} warning{'s' if warnings != 1 else ''}")

                lines.append(f"  - {file_name}: {', '.join(issue_parts)} - \"{summary_text}\"")

            if len(files) > 20:
                lines.append(f"  ... and {len(files) - 20} more files")

        return "\n".join(lines)

    def _format_for_ai(
        self,
        files: List[Dict[str, Any]],
        summary: Dict[str, Any],
        memories: Optional[List[Dict[str, Any]]] = None,
        pins: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Format context for AI assistants (XML structure).

        v2.5 Audience Profiles: Now includes memories and pins when provided.

        Output:
            <context type="current_state" timestamp="...">
              <summary>
                <files_with_errors>3</files_with_errors>
                <total_errors>5</total_errors>
                <total_warnings>2</total_warnings>
              </summary>
              <pinned count="2">
                <pin file="src/config.ts">Critical configuration</pin>
              </pinned>
              <errors>
                <file path="src/auth.ts" errors="2" warnings="0">
                  Type error in JWT validation
                </file>
              </errors>
              <memories count="10">
                <memory salience="HIGH" file="src/auth.ts">
                  JWT validation requires refresh token handling
                </memory>
              </memories>
            </context>
        """
        timestamp = datetime.now().isoformat()
        memories = memories or []
        pins = pins or []

        if not files and not memories and not pins:
            return f'''<context type="current_state" timestamp="{timestamp}">
  <summary>
    <files_with_errors>0</files_with_errors>
    <total_errors>0</total_errors>
    <total_warnings>0</total_warnings>
    <status>clean</status>
  </summary>
</context>'''

        lines = [f'<context type="current_state" timestamp="{timestamp}">']
        lines.append('  <summary>')
        lines.append(f'    <files_with_errors>{summary.get("files_with_errors", 0)}</files_with_errors>')
        lines.append(f'    <total_errors>{summary.get("total_errors", 0)}</total_errors>')
        lines.append(f'    <total_warnings>{summary.get("total_warnings", 0)}</total_warnings>')
        lines.append(f'    <status>{"has_issues" if files else "clean"}</status>')
        lines.append('  </summary>')

        # v2.5: Pinned files section (comes first - highest priority)
        if pins:
            lines.append(f'  <pinned count="{len(pins)}">')
            for pin in pins[:20]:  # Limit to 20 pins
                file_path = pin.get('file_path', '')
                gist = self._escape_xml(pin.get('gist', '') or pin.get('reason', 'pinned'))
                pinned = pin.get('pinned', 1)

                if file_path:
                    lines.append(f'    <pin file="{file_path}" pinned="{pinned}">')
                    lines.append(f'      {gist}')
                    lines.append('    </pin>')

            if len(pins) > 20:
                lines.append(f'    <!-- {len(pins) - 20} more pins omitted -->')
            lines.append('  </pinned>')

        # Errors section
        if files:
            lines.append('  <errors>')
            for f in files[:30]:  # Limit to 30 files for token efficiency
                file_path = f['file_path']
                errors = f.get('error_count', 0)
                warnings = f.get('warning_count', 0)
                summary_text = self._escape_xml(f.get('error_summary', '') or 'Unknown')

                lines.append(f'    <file path="{file_path}" errors="{errors}" warnings="{warnings}">')
                lines.append(f'      {summary_text}')
                lines.append('    </file>')

            if len(files) > 30:
                lines.append(f'    <!-- {len(files) - 30} more files omitted -->')
            lines.append('  </errors>')

        # Memories section
        if memories:
            lines.append(f'  <memories count="{len(memories)}">')
            for mem in memories[:50]:  # Limit to 50 memories for token efficiency
                salience = mem.get('salience', 'MEDIUM')
                file_path = mem.get('file_path', '')
                gist = self._escape_xml(mem.get('gist', '') or mem.get('verbatim', '')[:100] or 'No description')

                file_attr = f' file="{file_path}"' if file_path else ''
                lines.append(f'    <memory salience="{salience}"{file_attr}>')
                lines.append(f'      {gist}')
                lines.append('    </memory>')

            if len(memories) > 50:
                lines.append(f'    <!-- {len(memories) - 50} more memories omitted -->')
            lines.append('  </memories>')

        lines.append('</context>')

        return "\n".join(lines)

    def _format_for_manager(
        self,
        files: List[Dict[str, Any]],
        summary: Dict[str, Any],
        memories: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Format context for managers (high-level summary).

        v2.5 Audience Profiles: Manager gets memories for narrative context.

        If Whisperer is available, generates a "WOW" narrative using memories.
        Falls back to raw format if Whisperer fails (Do No Harm Rule).

        Output (with Whisperer):
            👋 Welcome back! Here's what's happening in your project...
            (narrative style with context from recent memories)

        Output (fallback):
            Code Health Report
            -----------------
            Status: Needs Attention
            3 files have active issues
        """
        memories = memories or []

        # Try Whisperer narrative first (Do No Harm Fallback Rule)
        if self._whisperer:
            try:
                # v2.5: Include memories in activity for richer narrative
                recent_memories = [
                    {'gist': m.get('gist', ''), 'file': m.get('file_path', '')}
                    for m in memories[:10]
                ]

                # Build activity dict for Whisperer
                activity = {
                    'current_project': self.project_path or 'unknown',
                    'recent_errors': [
                        {'file': f['file_path'], 'count': f.get('error_count', 0)}
                        for f in files[:5] if f.get('error_count', 0) > 0
                    ],
                    'recent_files_changed': [
                        {'file': f['file_path'], 'time': datetime.now().timestamp()}
                        for f in files[:5]
                    ],
                    'recent_memories': recent_memories,  # v2.5: Memory context for narrative
                    'user_state': 'debugging' if summary.get('total_errors', 0) > 0 else 'building'
                }

                # Generate narrative using Whisperer
                narrative = self._whisperer.create_wow_context(
                    user_input="Give me a manager report on the current project status",
                    recent_activity=activity
                )

                # v2.5 Fault Tolerance: Check for empty/whitespace-only narrative
                if narrative and narrative.strip():
                    # Append summary stats to narrative
                    narrative += f"\n\n📊 Quick Stats: {summary.get('files_with_errors', 0)} files, "
                    narrative += f"{summary.get('total_errors', 0)} errors, {summary.get('total_warnings', 0)} warnings"
                    if memories:
                        narrative += f", {len(memories)} recent memories"
                    return narrative
                else:
                    # Graceful Degradation: Whisperer returned empty, fall back to raw
                    logger.warning("Whisperer returned empty narrative, using raw format")

            except Exception as e:
                # Do No Harm: Log error and fall back to raw format
                logger.error(f"Whisperer failed (falling back to raw format): {e}")

        # FALLBACK: Raw format (always available)
        return self._format_manager_raw(files, summary, memories)

    def _format_manager_raw(
        self,
        files: List[Dict[str, Any]],
        summary: Dict[str, Any],
        memories: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Raw format for manager reports (fallback when Whisperer unavailable).

        v2.5 Audience Profiles: Now includes recent activity from memories.

        Output:
            Code Health Report
            -----------------
            Status: Needs Attention

            3 files have active issues
            - 5 errors (blocking)
            - 2 warnings (non-blocking)

            Most critical: src/auth.ts (2 errors)

            Recent Activity:
            - Fixed authentication flow
            - Updated API endpoints
        """
        memories = memories or []
        lines = ["Code Health Report", "-----------------"]

        error_count = summary.get('total_errors', 0)
        warning_count = summary.get('total_warnings', 0)
        file_count = summary.get('files_with_errors', 0)

        if not files and not memories:
            return """Code Health Report
-----------------
Status: Healthy

No active errors or warnings.
All checks passing."""

        # Status
        if error_count > 0:
            lines.append("Status: Needs Attention")
        elif warning_count > 0:
            lines.append("Status: Minor Issues")
        else:
            lines.append("Status: Healthy")

        lines.append("")

        # Summary
        if files:
            lines.append(f"{file_count} file{'s' if file_count != 1 else ''} have active issues")
            if error_count > 0:
                lines.append(f"  - {error_count} error{'s' if error_count != 1 else ''} (blocking)")
            if warning_count > 0:
                lines.append(f"  - {warning_count} warning{'s' if warning_count != 1 else ''} (non-blocking)")

            # Most critical file
            critical = max(files, key=lambda x: x.get('error_count', 0))
            if critical.get('error_count', 0) > 0:
                lines.append("")
                lines.append(f"Most critical: {Path(critical['file_path']).name} ({critical['error_count']} errors)")

        # v2.5: Recent Activity from memories (for manager narrative)
        if memories:
            lines.append("")
            lines.append("Recent Activity:")
            for mem in memories[:5]:  # Top 5 recent memories
                gist = mem.get('gist', '')[:60] or mem.get('verbatim', '')[:60] or 'Activity recorded'
                lines.append(f"  - {gist}")
            if len(memories) > 5:
                lines.append(f"  ... and {len(memories) - 5} more activities")

        return "\n".join(lines)

    def _escape_xml(self, text: str) -> str:
        """Escape special XML characters"""
        return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&apos;'))


# =============================================================================
# SINGLETON
# =============================================================================

_default_oracle: Optional[Oracle] = None


def get_oracle(
    brain_instance: Optional[Any] = None,
    project_path: Optional[str] = None,
    whisperer: Optional[WhispererProtocol] = None,
    pin_manager: Optional[Any] = None,
    database: Optional['MemoryDatabase'] = None  # Deprecated
) -> Oracle:
    """
    Get or create the default Oracle instance.

    Args:
        brain_instance: VismritiMemory instance for dynamic DB access
        project_path: Default project path for queries
        whisperer: Optional HumanAIWhisperer for narrative generation
                  (injected from daemon, not imported)
        pin_manager: Optional MemoryPinManager for fetching pins
                    (injected from daemon for Audience Profiles)
        database: DEPRECATED - Use brain_instance instead

    Note:
        If an Oracle already exists, updates brain/whisperer/pin_manager if provided.
        This allows daemon to inject new instances on context switch.
    """
    global _default_oracle
    if _default_oracle is None:
        _default_oracle = Oracle(
            brain_instance=brain_instance,
            project_path=project_path,
            whisperer=whisperer,
            pin_manager=pin_manager,
            database=database
        )
    else:
        # Update injected dependencies if provided (allows dynamic injection)
        if brain_instance is not None:
            _default_oracle._brain = brain_instance
        if whisperer is not None:
            _default_oracle._whisperer = whisperer
        if pin_manager is not None:
            _default_oracle._pin_manager = pin_manager
    return _default_oracle


def reset_oracle() -> None:
    """Reset the default Oracle instance"""
    global _default_oracle
    _default_oracle = None
