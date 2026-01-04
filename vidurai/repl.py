"""
Vidurai Interactive REPL (Read-Eval-Print Loop)
Sprint 3 - The Interaction Layer

Features:
- Hybrid Intent Router for smart query handling
- Syntax-highlighted code display
- Stateful conversation history
- Memory search integration

Usage:
    from vidurai.repl import start_repl
    start_repl("/path/to/project")

Or via CLI:
    vidurai chat --project /path/to/project
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List

from loguru import logger

# Prompt toolkit imports
try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.styles import Style
    from prompt_toolkit.formatted_text import HTML
    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False

# Pygments for syntax highlighting
try:
    from pygments import highlight
    from pygments.lexers import get_lexer_for_filename, get_lexer_by_name, TextLexer
    from pygments.formatters import TerminalTrueColorFormatter, Terminal256Formatter
    from pygments.util import ClassNotFound
    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False

# Vidurai imports
from vidurai.core.intent_router import IntentRouter, IntentType, RoutingResult
from vidurai.vismriti_memory import VismritiMemory
from vidurai.storage.database import SalienceLevel
from vidurai.version import __version__


# REPL styling
REPL_STYLE = Style.from_dict({
    'prompt': '#00aa00 bold',
    'project': '#0088ff',
    'arrow': '#888888',
})


class ViduraiREPL:
    """
    Interactive REPL for Vidurai.

    Provides:
    - Smart intent routing (code vs memory queries)
    - Syntax-highlighted code display
    - Memory search with formatted output
    - Command execution
    - Session history
    """

    def __init__(self, project_path: str = "."):
        """
        Initialize the REPL.

        Args:
            project_path: Path to the project context
        """
        self.project_path = Path(project_path).resolve()
        self.project_name = self.project_path.name

        # Initialize components
        self.router = IntentRouter(project_path=str(self.project_path))
        self.memory = VismritiMemory(project_path=str(self.project_path))

        # Session state
        self.history: List[dict] = []
        self.session_start = datetime.now()

        # Prompt session
        if PROMPT_TOOLKIT_AVAILABLE:
            self.session = PromptSession(
                history=InMemoryHistory(),
                style=REPL_STYLE,
                enable_history_search=True,
            )
        else:
            self.session = None

        logger.debug(f"REPL initialized for project: {self.project_name}")

    def _get_prompt(self) -> str:
        """Generate the REPL prompt."""
        if PROMPT_TOOLKIT_AVAILABLE:
            # Return formatted prompt for prompt_toolkit
            return [
                ('class:prompt', 'vidurai'),
                ('class:arrow', ' ['),
                ('class:project', self.project_name[:20]),
                ('class:arrow', ']> '),
            ]
        else:
            return f"vidurai [{self.project_name[:20]}]> "

    def _highlight_code(self, code: str, filename: str = None) -> str:
        """
        Syntax-highlight code for terminal display.

        Args:
            code: Source code to highlight
            filename: Optional filename for lexer detection

        Returns:
            Highlighted code string
        """
        if not PYGMENTS_AVAILABLE:
            return code

        try:
            # Get lexer based on filename
            if filename:
                try:
                    lexer = get_lexer_for_filename(filename)
                except ClassNotFound:
                    lexer = TextLexer()
            else:
                lexer = TextLexer()

            # Use true color if available, fallback to 256 colors
            try:
                formatter = TerminalTrueColorFormatter(style='monokai')
            except Exception:
                formatter = Terminal256Formatter(style='monokai')

            return highlight(code, lexer, formatter)

        except Exception as e:
            logger.warning(f"Highlighting failed: {e}")
            return code

    def _handle_code_retrieval(self, result: RoutingResult) -> None:
        """Handle CODE_RETRIEVAL intent."""
        if not result.matched_file:
            # Try to extract filename from query
            print("\n⚠️  Could not identify file. Try: 'show <filename>'")
            return

        # Get full path
        file_path = self.router.get_file_path(result.matched_file)

        if not file_path or not file_path.exists():
            # Try direct path
            file_path = self.project_path / result.matched_file
            if not file_path.exists():
                print(f"\n❌ File not found: {result.matched_file}")
                return

        try:
            # Read file
            content = file_path.read_text(encoding='utf-8', errors='replace')

            # Display with syntax highlighting
            print(f"\n📄 {file_path.relative_to(self.project_path)}")
            print("─" * 60)

            highlighted = self._highlight_code(content, str(file_path))
            print(highlighted)

            print("─" * 60)
            print(f"📊 {len(content)} chars, {content.count(chr(10)) + 1} lines")

        except FileNotFoundError:
            print(f"\n❌ File not found: {result.matched_file}")
        except PermissionError:
            print(f"\n❌ Permission denied: {result.matched_file}")
        except Exception as e:
            print(f"\n❌ Error reading file: {e}")

    def _handle_memory_query(self, result: RoutingResult) -> None:
        """Handle MEMORY_QUERY intent."""
        query = result.query

        try:
            # Search memories
            memories = self.memory.db.recall_memories(
                project_path=str(self.project_path),
                query=query,
                min_salience=SalienceLevel.LOW,
                limit=10
            )

            if not memories:
                print(f"\n💭 No memories found for: '{query}'")
                print("   Try a different search term or check 'stats' for what's stored.")
                return

            print(f"\n🧠 Found {len(memories)} memories:\n")

            for i, mem in enumerate(memories, 1):
                salience = mem['salience']
                icon = {'CRITICAL': '🔥', 'HIGH': '⚡', 'MEDIUM': '📝', 'LOW': '💬', 'NOISE': '🔇'}.get(salience, '📌')

                # Truncate gist for display
                gist = mem['gist']
                if len(gist) > 100:
                    gist = gist[:97] + "..."

                print(f"  {i}. {icon} [{salience}] {gist}")

                if mem.get('file_path'):
                    print(f"     📄 {mem['file_path']}")

                # Show age
                created = datetime.fromisoformat(mem['created_at'])
                age_days = (datetime.now() - created).days
                if age_days == 0:
                    age_str = "today"
                elif age_days == 1:
                    age_str = "yesterday"
                else:
                    age_str = f"{age_days} days ago"
                print(f"     🕐 {age_str}")
                print()

        except Exception as e:
            print(f"\n❌ Error searching memories: {e}")
            logger.exception("Memory search failed")

    def _handle_command(self, result: RoutingResult) -> bool:
        """
        Handle COMMAND intent.

        Returns:
            True if REPL should exit, False otherwise
        """
        cmd = result.command.lower() if result.command else ""

        # Exit commands
        if cmd in ('exit', 'quit', 'bye', 'q'):
            return True

        # Help
        if cmd in ('help', '?'):
            self._show_help()
            return False

        # Stats
        if cmd in ('stats', 'statistics'):
            self._show_stats()
            return False

        # Recent
        if cmd in ('recent', 'history'):
            self._show_recent()
            return False

        # Context
        if cmd in ('context', 'ctx'):
            self._show_context()
            return False

        # Refresh file cache
        if cmd in ('refresh', 'reload'):
            count = self.router.refresh()
            print(f"\n🔄 Refreshed file cache: {count} files indexed")
            return False

        # Unknown command
        print(f"\n⚠️  Command '{cmd}' not yet implemented in REPL.")
        print("   Try 'help' for available commands.")
        return False

    def _show_help(self) -> None:
        """Display help information."""
        print("""
🧠 Vidurai Interactive REPL - Help

COMMANDS:
  help, ?           Show this help
  stats             Show memory statistics
  recent            Show recent activity
  context           Get AI-ready context
  refresh           Refresh file cache
  exit, quit        Exit the REPL

CODE RETRIEVAL:
  show <file>       Display file with syntax highlighting
  cat <file>        Same as show
  <filename>        If a file matches, show it

MEMORY SEARCH:
  <any text>        Search memories for matching content

EXAMPLES:
  > show main.py              # View a file
  > auth bug fix              # Search memories
  > README.md                 # Show README if it exists
  > how does login work       # Narrative memory search

TIPS:
  • Use ↑/↓ arrows to navigate history
  • Ctrl+R to search history
  • Ctrl+C to cancel, Ctrl+D to exit
""")

    def _show_stats(self) -> None:
        """Display memory statistics."""
        try:
            stats = self.memory.db.get_statistics(str(self.project_path))

            print(f"\n📊 Memory Statistics - {self.project_name}")
            print("─" * 50)
            print(f"  Total memories: {stats['total']}")

            if stats.get('by_salience'):
                print("\n  By Salience:")
                for salience in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'NOISE']:
                    count = stats['by_salience'].get(salience, 0)
                    if count > 0:
                        icon = {'CRITICAL': '🔥', 'HIGH': '⚡', 'MEDIUM': '📝', 'LOW': '💬', 'NOISE': '🔇'}.get(salience, '📌')
                        print(f"    {icon} {salience:8s} {count:4d}")

            if stats.get('by_type'):
                print("\n  By Type:")
                for event_type, count in sorted(stats['by_type'].items()):
                    print(f"    {event_type:15s} {count:4d}")

            print("─" * 50)

        except Exception as e:
            print(f"\n❌ Error getting stats: {e}")

    def _show_recent(self) -> None:
        """Show recent activity."""
        try:
            memories = self.memory.db.get_recent_activity(
                str(self.project_path),
                hours=24,
                limit=10
            )

            if not memories:
                print("\n💤 No recent activity in the last 24 hours.")
                return

            print(f"\n🕐 Recent Activity (last 24h)\n")

            for mem in memories:
                salience = mem['salience']
                icon = {'CRITICAL': '🔥', 'HIGH': '⚡', 'MEDIUM': '📝', 'LOW': '💬', 'NOISE': '🔇'}.get(salience, '📌')

                gist = mem['gist'][:80] + "..." if len(mem['gist']) > 80 else mem['gist']

                print(f"  {icon} {gist}")
                if mem.get('file_path'):
                    print(f"     📄 {mem['file_path']}")
                print()

        except Exception as e:
            print(f"\n❌ Error getting recent activity: {e}")

    def _show_context(self) -> None:
        """Show AI-ready context."""
        try:
            context = self.memory.get_context_for_ai(max_tokens=1500)
            print("\n" + context)
        except Exception as e:
            print(f"\n❌ Error getting context: {e}")

    def _record_interaction(self, query: str, result: RoutingResult) -> None:
        """Record interaction in session history."""
        self.history.append({
            'timestamp': datetime.now().isoformat(),
            'query': query,
            'intent': result.intent.name,
            'matched_file': result.matched_file,
            'command': result.command,
            'routing_time_ms': result.routing_time_ms
        })

    def run(self) -> None:
        """Run the REPL main loop."""
        # Print welcome banner
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║  🧠 Vidurai Interactive REPL v{__version__:<28}║
║                                                              ║
║  Project: {self.project_name[:50]:<50} ║
║  Type 'help' for commands, 'exit' to quit                   ║
╚══════════════════════════════════════════════════════════════╝
""")

        while True:
            try:
                # Get input
                if self.session:
                    query = self.session.prompt(self._get_prompt())
                else:
                    # Fallback for no prompt_toolkit
                    query = input(self._get_prompt())

                query = query.strip()

                # Skip empty input
                if not query:
                    continue

                # Route the query
                result = self.router.route(query, str(self.project_path))

                # Record in history
                self._record_interaction(query, result)

                # Handle based on intent
                if result.intent == IntentType.COMMAND:
                    should_exit = self._handle_command(result)
                    if should_exit:
                        break

                elif result.intent == IntentType.CODE_RETRIEVAL:
                    self._handle_code_retrieval(result)

                elif result.intent == IntentType.MEMORY_QUERY:
                    self._handle_memory_query(result)

            except KeyboardInterrupt:
                print("\n\n👋 Use 'exit' or Ctrl+D to quit")
                continue

            except EOFError:
                # Ctrl+D
                break

            except Exception as e:
                print(f"\n❌ Error: {e}")
                logger.exception("REPL error")

        # Goodbye
        session_duration = (datetime.now() - self.session_start).total_seconds()
        print(f"\n👋 Session ended. Duration: {session_duration:.0f}s, Interactions: {len(self.history)}")
        print("   विस्मृति भी विद्या है — 'Forgetting too is knowledge'")
        print("   जय विदुराई! 🕉️\n")


def start_repl(project_path: str = ".") -> None:
    """
    Start the Vidurai interactive REPL.

    Args:
        project_path: Path to the project context
    """
    if not PROMPT_TOOLKIT_AVAILABLE:
        print("⚠️  prompt_toolkit not available. Install for better experience:")
        print("   pip install prompt_toolkit pygments")
        print()

    repl = ViduraiREPL(project_path=project_path)
    repl.run()
