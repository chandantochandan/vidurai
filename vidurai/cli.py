#!/usr/bin/env python3
"""
Vidurai CLI Tool
Standalone command-line interface for memory management
v2.2.0 - Phase 7 (Lazy Loading Refactor)

Usage:
    vidurai --help
    vidurai stats --project /path/to/project
    vidurai recall --query "authentication" --limit 10
    vidurai recall --query "auth" --audience developer
    vidurai context --query "how does login work"
    vidurai context --query "auth" --audience manager
    vidurai recent --hours 24
    vidurai export --format json --output memories.json
    vidurai server --port 8765
    vidurai clear --project /path/to/project

विस्मृति भी विद्या है — "Forgetting too is knowledge"

LAZY LOADING: All heavy imports (vidurai.storage, vidurai.core, pandas, duckdb)
are deferred to inside functions to ensure CLI startup < 0.5s.
"""

import click
import json
import os
import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

# Version - hardcoded to avoid vidurai/__init__.py heavy loading
# This MUST match vidurai/__version__.py
__version__ = "2.2.0"

# ============================================================================
# LAZY LOADING HELPERS
# These functions check availability without importing heavy modules
# ============================================================================

def _check_psutil():
    """Check if psutil is available (lazy)."""
    try:
        import psutil
        return True
    except ImportError:
        return False

def _get_psutil():
    """Get psutil module (lazy import)."""
    import psutil
    return psutil

def _check_tabulate():
    """Check if tabulate is available (lazy)."""
    try:
        import tabulate
        return True
    except ImportError:
        return False


def _check_event_bus():
    """Check if event bus is available (lazy)."""
    try:
        from vidurai.shared.events import publish_event
        return True
    except ImportError:
        return False


def _check_mcp_installer():
    """Check if MCP installer is available (lazy)."""
    try:
        from vidurai.integrations.mcp import check_mcp_status, install_mcp_server
        return True
    except ImportError:
        return False


def _check_hints_available():
    """Check if hints are available (lazy)."""
    try:
        from vidurai.core.proactive_hints import HintGenerator
        return True
    except ImportError:
        return False


def _check_sf_v2_available():
    """Check if SF-V2 components are available (lazy)."""
    try:
        from vidurai.core.memory_pin_manager import MemoryPinManager
        return True
    except ImportError:
        return False


@click.group()
@click.version_option(version=__version__, prog_name='Vidurai')
def cli():
    """
    🧠 Vidurai - Persistent AI Memory Layer

    Vidurai is an intelligent memory system that captures, classifies,
    and recalls project context for AI-powered development.

    Examples:
        vidurai stats                          # Show memory statistics
        vidurai recall --query "auth bug"      # Search memories
        vidurai context                        # Get AI-ready context
        vidurai recent --hours 24              # Show recent activity
        vidurai server                         # Start MCP server
    """
    pass


# ============================================================================
# Phase 7.1: Daemon Process Management (start/stop/status)
# ============================================================================

# Constants for daemon management
VIDURAI_HOME = Path.home() / ".vidurai"
PID_FILE = VIDURAI_HOME / "daemon.pid"
LOG_FILE = VIDURAI_HOME / "vidurai.log"


def _ensure_vidurai_home():
    """Ensure ~/.vidurai directory exists"""
    VIDURAI_HOME.mkdir(parents=True, exist_ok=True)


def _is_daemon_running() -> Tuple[bool, Optional[int]]:
    """
    Check if daemon is actually running (Stale Lock Rule).

    Returns:
        (is_running, pid) - tuple of running status and PID (if found)
    """
    if not _check_psutil():
        # Fallback: just check if PID file exists
        if PID_FILE.exists():
            try:
                pid = int(PID_FILE.read_text().strip())
                return True, pid
            except (ValueError, OSError):
                return False, None
        return False, None

    if not PID_FILE.exists():
        return False, None

    # Lazy import psutil only when needed
    psutil = _get_psutil()

    try:
        pid = int(PID_FILE.read_text().strip())

        # Stale Lock Rule: Verify process exists AND is a Python/vidurai process
        if not psutil.pid_exists(pid):
            # Stale PID file - process doesn't exist
            PID_FILE.unlink(missing_ok=True)
            return False, None

        proc = psutil.Process(pid)
        proc_name = proc.name().lower()

        # Check if it's a Python process (could be python, python3, etc.)
        if 'python' not in proc_name and 'vidurai' not in proc_name:
            # PID belongs to a different process - stale lock
            PID_FILE.unlink(missing_ok=True)
            return False, None

        return True, pid

    except (ValueError, OSError, psutil.NoSuchProcess, psutil.AccessDenied):
        # Clean up invalid PID file
        PID_FILE.unlink(missing_ok=True)
        return False, None


@cli.command()
def start():
    """Start the Vidurai Guardian daemon (background service).

    The daemon provides:
    - IPC server for VS Code extension communication
    - File watching and context mediation
    - Memory bridge for AI hints

    Examples:
        vidurai start                 # Start daemon
        vidurai status                # Check if running
        vidurai stop                  # Stop daemon
    """
    if not _check_psutil():
        click.echo("❌ psutil not installed. Run: pip install psutil>=5.9.0", err=True)
        sys.exit(1)

    # Lazy import psutil
    psutil = _get_psutil()

    _ensure_vidurai_home()

    # Check if already running
    is_running, existing_pid = _is_daemon_running()
    if is_running:
        click.echo(f"⚠️  Vidurai Guardian already running (PID: {existing_pid})")
        click.echo(f"   Use 'vidurai status' to check, 'vidurai stop' to stop.")
        return

    click.echo("🚀 Starting Vidurai Guardian daemon...")

    # Prepare log file
    log_file = open(LOG_FILE, 'a')

    # Platform-specific process detachment
    if sys.platform == 'win32':
        # Windows: Use CREATE_NO_WINDOW to prevent terminal popup
        # CREATE_NEW_PROCESS_GROUP for signal isolation
        creationflags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
        proc = subprocess.Popen(
            [sys.executable, "-m", "vidurai.daemon"],
            stdout=log_file,
            stderr=log_file,
            stdin=subprocess.DEVNULL,
            creationflags=creationflags,
        )
    else:
        # POSIX (Mac/Linux): Use start_new_session=True to detach from terminal
        proc = subprocess.Popen(
            [sys.executable, "-m", "vidurai.daemon"],
            stdout=log_file,
            stderr=log_file,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )

    # Write PID file
    PID_FILE.write_text(str(proc.pid))

    # Brief wait to check if process started successfully
    time.sleep(0.5)

    # Verify it's still running
    if psutil.pid_exists(proc.pid):
        click.echo(f"✅ Vidurai Guardian started (PID: {proc.pid})")
        click.echo(f"   Log file: {LOG_FILE}")
        click.echo(f"   Use 'vidurai status' to check health.")
    else:
        click.echo("❌ Daemon failed to start. Check log file:", err=True)
        click.echo(f"   {LOG_FILE}", err=True)
        PID_FILE.unlink(missing_ok=True)
        sys.exit(1)


@cli.command()
def stop():
    """Stop the Vidurai Guardian daemon.

    Gracefully terminates the daemon process. If it doesn't respond
    within 2 seconds, force kills it.

    Examples:
        vidurai stop                  # Stop daemon
        vidurai status                # Verify stopped
    """
    if not _check_psutil():
        click.echo("❌ psutil not installed. Run: pip install psutil>=5.9.0", err=True)
        sys.exit(1)

    # Lazy import psutil
    psutil = _get_psutil()

    is_running, pid = _is_daemon_running()

    if not is_running:
        click.echo("⚪ Vidurai Guardian is not running.")
        # Clean up stale PID file if exists
        PID_FILE.unlink(missing_ok=True)
        return

    click.echo(f"🛑 Stopping Vidurai Guardian (PID: {pid})...")

    try:
        proc = psutil.Process(pid)

        # Safety check: Verify it's a Python/vidurai process
        proc_name = proc.name().lower()
        if 'python' not in proc_name and 'vidurai' not in proc_name:
            click.echo(f"⚠️  PID {pid} is not a Vidurai process ({proc_name}). Cleaning up.", err=True)
            PID_FILE.unlink(missing_ok=True)
            return

        # Graceful termination
        proc.terminate()

        # Wait up to 2 seconds for graceful shutdown
        try:
            proc.wait(timeout=2)
            click.echo("✅ Vidurai Guardian stopped gracefully.")
        except psutil.TimeoutExpired:
            # Force kill if still alive
            click.echo("⚠️  Daemon not responding. Force killing...")
            proc.kill()
            proc.wait(timeout=1)
            click.echo("✅ Vidurai Guardian force stopped.")

    except psutil.NoSuchProcess:
        click.echo("⚠️  Process already terminated.")
    except psutil.AccessDenied:
        click.echo(f"❌ Permission denied to stop PID {pid}.", err=True)
        click.echo("   Try: sudo vidurai stop", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error stopping daemon: {e}", err=True)
        sys.exit(1)
    finally:
        # Always clean up PID file
        PID_FILE.unlink(missing_ok=True)


@cli.command()
def status():
    """Show Vidurai Guardian daemon status.

    Displays:
    - Running status (🟢 Running / ⚪ Stopped)
    - Process ID (PID)
    - Memory usage
    - Uptime

    Examples:
        vidurai status                # Check daemon status
    """
    is_running, pid = _is_daemon_running()

    if not is_running:
        click.echo("⚪ Vidurai Guardian: Stopped")
        click.echo(f"   Start with: vidurai start")
        return

    click.echo(f"🟢 Vidurai Guardian: Running (PID: {pid})")

    # Show additional info if psutil available
    if _check_psutil():
        psutil = _get_psutil()
        try:
            proc = psutil.Process(pid)

            # Memory usage
            mem_info = proc.memory_info()
            mem_mb = mem_info.rss / (1024 * 1024)
            click.echo(f"   Memory: {mem_mb:.1f} MB")

            # Uptime
            create_time = datetime.fromtimestamp(proc.create_time())
            uptime = datetime.now() - create_time
            hours, remainder = divmod(int(uptime.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            click.echo(f"   Uptime: {hours}h {minutes}m {seconds}s")

            # CPU usage (requires small delay for accurate reading)
            cpu_percent = proc.cpu_percent(interval=0.1)
            click.echo(f"   CPU: {cpu_percent:.1f}%")

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    click.echo(f"   Log: {LOG_FILE}")
    click.echo(f"   PID file: {PID_FILE}")


@cli.command()
@click.option('--lines', '-n', default=50, help='Number of lines to show.')
@click.option('--follow', '-f', is_flag=True, help='Follow log output (like tail -f).')
def logs(lines, follow):
    """Show or follow the Vidurai daemon logs.

    Displays recent log entries from the daemon. Use --follow to
    continuously monitor new log entries in real-time.

    Examples:
        vidurai logs                  # Show last 50 lines
        vidurai logs -n 100           # Show last 100 lines
        vidurai logs -f               # Follow logs (Ctrl+C to stop)
        vidurai logs -n 20 -f         # Show last 20 then follow
    """
    from collections import deque

    if not LOG_FILE.exists():
        click.echo(f"⚠️  No log file found at {LOG_FILE}")
        click.echo("   Start the daemon first: vidurai start")
        return

    click.echo(f"📜 Log file: {LOG_FILE}")
    click.echo(f"   Showing last {lines} lines...")
    click.echo("-" * 60)

    with open(LOG_FILE, 'r', encoding='utf-8', errors='replace') as f:
        # Read last N lines efficiently using deque
        last_lines = deque(f, maxlen=lines)
        for line in last_lines:
            click.echo(line.rstrip())

        # Follow mode (like tail -f)
        if follow:
            click.echo("-" * 60)
            click.echo("📡 Following logs (Ctrl+C to stop)...")
            try:
                while True:
                    line = f.readline()
                    if line:
                        click.echo(line.rstrip())
                    else:
                        time.sleep(0.1)
            except KeyboardInterrupt:
                click.echo("\n🛑 Stopped following logs.")


@cli.command()
@click.option('--project', default='.', help='Project path (default: current directory)')
@click.option('--query', help='Search query to filter memories')
@click.option('--limit', default=10, help='Maximum results to show')
@click.option('--min-salience', type=click.Choice(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'NOISE']),
              default='MEDIUM', help='Minimum salience level')
@click.option('--audience', type=click.Choice(['developer', 'ai', 'manager', 'personal']),
              help='Audience perspective for gists (Phase 5: Multi-Audience)')
def recall(project, query, limit, min_salience, audience):
    """Recall memories from project database"""
    # [CTO Mandate] Canonicalize path to prevent split-brain projects
    project = os.path.abspath(project)
    try:
        # Lazy import to fix NameError
        from vidurai.storage.database import MemoryDatabase, SalienceLevel
        
        db = MemoryDatabase()
        salience = SalienceLevel[min_salience]

        # Smart Query Sanitization: Extract keywords for intersection search
        keywords = None
        if query:
            from vidurai.vismriti_memory import STOP_WORDS
            import re
            tokens = re.split(r'[\s\-_.,;:!?"\'/\\()[\]{}]+', query.lower())
            keywords = [t for t in tokens if t and t not in STOP_WORDS and len(t) > 1]
            if not keywords:
                keywords = [query]  # Fallback if everything was a stop word

        memories = db.recall_memories(
            project_path=project,
            query=query,
            min_salience=salience,
            limit=limit,
            keywords=keywords  # Pass sanitized keywords for intersection search
        )

        if not memories:
            click.echo("No memories found matching your criteria")
            return

        # Phase 5: Enrich with audience-specific gists if requested
        if audience:
            for mem in memories:
                try:
                    audience_gists = db.get_audience_gists(mem['id'], audiences=[audience])
                    if audience in audience_gists:
                        mem['display_gist'] = audience_gists[audience]
                    else:
                        mem['display_gist'] = mem['gist']
                except Exception:
                    mem['display_gist'] = mem['gist']
        else:
            for mem in memories:
                mem['display_gist'] = mem['gist']

        audience_label = f" ({audience} view)" if audience else ""
        click.echo(f"\n🧠 Found {len(memories)} memories{audience_label}\n")

        # Phase 6: Publish CLI recall event
        EVENT_BUS_AVAILABLE = _check_event_bus()
        if EVENT_BUS_AVAILABLE:
            try:
                from vidurai.shared.events import publish_event
                publish_event(
                    "cli.recall",
                    source="cli",
                    project_path=project,
                    query=query or "all",
                    memory_count=len(memories),
                    min_salience=min_salience,
                    audience=audience
                )
            except Exception:
                pass  # Silent fail for event publishing

        TABULATE_AVAILABLE = _check_tabulate()
        if TABULATE_AVAILABLE:
            # Pretty table output
            from tabulate import tabulate
            table = []
            for mem in memories:
                gist = mem['display_gist'][:60] + '...' if len(mem['display_gist']) > 60 else mem['display_gist']
                file_path = mem.get('file_path', 'N/A')
                if file_path and len(file_path) > 30:
                    file_path = '...' + file_path[-27:]

                created = datetime.fromisoformat(mem['created_at'])
                age_days = (datetime.now() - created).days

                table.append([
                    _get_salience_icon(mem['salience']),
                    gist,
                    file_path,
                    f"{age_days}d ago"
                ])

            click.echo(tabulate(table, headers=['', 'Gist', 'File', 'Age'], tablefmt='simple'))
        else:
            # Fallback simple output
            for i, mem in enumerate(memories, 1):
                click.echo(f"{i}. [{mem['salience']}] {mem['display_gist']}")
                if mem.get('file_path'):
                    click.echo(f"   File: {mem['file_path']}")
                click.echo(f"   Created: {mem['created_at'][:10]}\n")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--project', default='.', help='Project path (default: current directory)')
@click.option('--query', help='Context query to filter relevant memories')
@click.option('--max-tokens', default=2000, help='Maximum tokens in output')
@click.option('--audience', type=click.Choice(['developer', 'ai', 'manager', 'personal']),
              help='Audience perspective for gists (Phase 5: Multi-Audience)')
@click.option('--show-hints/--no-hints', default=True, help='Show proactive hints (Phase 6.6)')
@click.option('--max-hints', default=3, help='Maximum number of hints to display')
def context(project, query, max_tokens, audience, show_hints, max_hints):
    """Get formatted context for AI tools (Claude Code, ChatGPT, etc.)"""
    # [CTO Mandate] Canonicalize path to prevent split-brain projects
    project = os.path.abspath(project)
    try:
        # Lazy import
        from vidurai.vismriti_memory import VismritiMemory
        
        memory = VismritiMemory(project_path=project)
        ctx = memory.get_context_for_ai(query=query, max_tokens=max_tokens, audience=audience)

        click.echo(ctx)

        # Phase 6.6: Show proactive hints
        HINTS_AVAILABLE = _check_hints_available()
        if show_hints and HINTS_AVAILABLE:
            try:
                from vidurai.core.proactive_hints import ProactiveHintEngine
                from vidurai.core.episode_builder import EpisodeBuilder
                
                builder = EpisodeBuilder()
                hint_engine = ProactiveHintEngine(builder)
                
                # Get recent episodes and generate hints
                episodes = builder.get_closed_episodes(limit=10)
                if episodes:
                    recent_episode = episodes[0]
                    hints = hint_engine.generate_hints_for_episode(recent_episode)
                    
                    if hints[:max_hints]:
                        click.echo("\n💡 Proactive Hints:")
                        for hint in hints[:max_hints]:
                            click.echo(f"  • [{hint.hint_type}] {hint.title} (confidence: {hint.confidence:.2f})")
                            
            except Exception as e:
                # Silent fail for hints - don't break context display
                click.echo(f"\n⚠️  Hints unavailable: {e}", err=True)

        # Phase 6: Publish CLI context event
        EVENT_BUS_AVAILABLE = _check_event_bus()
        if EVENT_BUS_AVAILABLE:
            try:
                from vidurai.shared.events import publish_event
                publish_event(
                    "cli.context",
                    source="cli",
                    project_path=project,
                    query=query or "all",
                    max_tokens=max_tokens,
                    audience=audience,
                    context_length=len(ctx)
                )
            except Exception:
                pass  # Silent fail for event publishing

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--project', default='.', help='Project path (default: current directory)')
def stats(project):
    """Show memory statistics for a project"""
    # [CTO Mandate] Canonicalize path to prevent split-brain projects
    project = os.path.abspath(project)
    try:
        # Lazy import
        from vidurai.storage.database import MemoryDatabase
        
        db = MemoryDatabase()
        stats_data = db.get_statistics(project)

        project_name = Path(project).resolve().name

        click.echo("\n" + "=" * 60)
        click.echo(f"📊 Memory Statistics - {project_name}")
        click.echo("=" * 60)
        click.echo(f"Total memories: {stats_data['total']}")

        if stats_data['by_salience']:
            click.echo("\nBy Salience:")
            for salience in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'NOISE']:
                count = stats_data['by_salience'].get(salience, 0)
                if count > 0:
                    icon = _get_salience_icon(salience)
                    click.echo(f"  {icon} {salience:8s} {count:4d}")

        if stats_data['by_type']:
            click.echo("\nBy Type:")
            for event_type, count in sorted(stats_data['by_type'].items()):
                click.echo(f"  {event_type:15s} {count:4d}")

        click.echo("=" * 60 + "\n")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--project', default='.', help='Project path (default: current directory)')
@click.option('--hours', default=24, help='Hours to look back')
@click.option('--limit', default=20, help='Maximum results')
def recent(project, hours, limit):
    """Show recent development activity"""
    # [CTO Mandate] Canonicalize path to prevent split-brain projects
    project = os.path.abspath(project)
    try:
        # Lazy import
        from vidurai.storage.database import MemoryDatabase
        
        db = MemoryDatabase()
        memories = db.get_recent_activity(project, hours=hours, limit=limit)

        if not memories:
            click.echo(f"No activity in the last {hours} hours")
            return

        click.echo(f"\n🕐 Recent Activity (last {hours}h)\n")
        click.echo("=" * 70)

        for mem in memories:
            created = datetime.fromisoformat(mem['created_at'])
            time_ago = _format_time_ago(created)

            icon = _get_salience_icon(mem['salience'])
            click.echo(f"\n{icon} {mem['gist']}")

            if mem.get('file_path'):
                click.echo(f"   📄 File: {mem['file_path']}")

            click.echo(f"   🕒 {time_ago}")

        click.echo("\n" + "=" * 70 + "\n")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--project', default='.', help='Project path (default: current directory)')
@click.option('--format', type=click.Choice(['json', 'text', 'sql']), default='json',
              help='Export format')
@click.option('--output', type=click.Path(), help='Output file (default: stdout)')
@click.option('--limit', default=10000, help='Maximum memories to export')
def export(project, format, output, limit):
    """Export project memories"""
    # [CTO Mandate] Canonicalize path to prevent split-brain projects
    project = os.path.abspath(project)
    try:
        # Lazy import
        from vidurai.storage.database import MemoryDatabase, SalienceLevel
        
        db = MemoryDatabase()

        if format == 'json':
            memories = db.recall_memories(
                project_path=project,
                min_salience=SalienceLevel.NOISE,
                limit=limit
            )

            # Convert datetime objects to strings for JSON serialization
            for mem in memories:
                if 'created_at' in mem and isinstance(mem['created_at'], datetime):
                    mem['created_at'] = mem['created_at'].isoformat()

            data = json.dumps(memories, indent=2)

            if output:
                Path(output).write_text(data)
                click.echo(f"✅ Exported {len(memories)} memories to {output}")
            else:
                click.echo(data)

        elif format == 'text':
            memories = db.recall_memories(
                project_path=project,
                min_salience=SalienceLevel.NOISE,
                limit=limit
            )

            output_lines = []
            for mem in memories:
                output_lines.append(f"[{mem['salience']}] {mem['gist']}")
                if mem.get('file_path'):
                    output_lines.append(f"  File: {mem['file_path']}")
                output_lines.append(f"  Created: {mem['created_at']}")
                output_lines.append("")

            text = "\n".join(output_lines)

            if output:
                Path(output).write_text(text)
                click.echo(f"✅ Exported {len(memories)} memories to {output}")
            else:
                click.echo(text)

        elif format == 'sql':
            click.echo(f"Database location: {db.db_path}")
            click.echo("\nTo export as SQL, use:")
            click.echo(f"  sqlite3 {db.db_path} .dump > backup.sql")
            click.echo("\nOr browse interactively:")
            click.echo(f"  sqlite3 {db.db_path}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--host', default='localhost', help='Host to bind to')
@click.option('--port', default=8765, help='Port to listen on')
@click.option('--allow-all-origins', is_flag=True, help='⚠️  Disable CORS (dev only)')
def server(host, port, allow_all_origins):
    """Start MCP server for AI tool integration"""
    try:
        from vidurai.mcp_server import start_mcp_server

        click.echo("Starting Vidurai MCP Server...")
        click.echo(f"Host: {host}:{port}")

        if allow_all_origins:
            click.echo("⚠️  CORS restrictions DISABLED (development mode)")

        start_mcp_server(host=host, port=port, allow_all_origins=allow_all_origins)

    except KeyboardInterrupt:
        click.echo("\n\n👋 Server stopped")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


# ============================================================================
# Sprint 1: The Connector - MCP Installation Commands
# ============================================================================

@cli.command('mcp-install')
@click.option('--dry-run', is_flag=True, help='Show what would be done without modifying files')
@click.option('--status', is_flag=True, help='Show current MCP installation status')
def mcp_install(dry_run, status):
    """Install Vidurai as MCP server for Claude Desktop (Sprint 1)

    This command configures Claude Desktop to use Vidurai as an MCP
    (Model Context Protocol) server, enabling persistent memory integration.

    Examples:
        vidurai mcp-install              # Install MCP server
        vidurai mcp-install --dry-run    # Preview changes
        vidurai mcp-install --status     # Check current status
    """
    MCP_INSTALLER_AVAILABLE = _check_mcp_installer()
    if not MCP_INSTALLER_AVAILABLE:
        click.echo("❌ MCP installer not available. Check installation.", err=True)
        sys.exit(1)

    try:
        # Lazy import MCP functions
        from vidurai.integrations.mcp import check_mcp_status, install_mcp_server
        
        if status:
            # Show current status
            status_info = check_mcp_status()
            click.echo("\n🔌 MCP Installation Status\n")
            click.echo(f"  Config path: {status_info['config_path']}")
            click.echo(f"  Config exists: {'Yes' if status_info['config_exists'] else 'No'}")
            click.echo(f"  Vidurai installed: {'Yes' if status_info['vidurai_installed'] else 'No'}")

            if status_info['vidurai_installed']:
                click.echo(f"  Vidurai config: {json.dumps(status_info['vidurai_config'], indent=4)}")

            if status_info['other_servers']:
                click.echo(f"  Other MCP servers: {', '.join(status_info['other_servers'])}")

            if 'error' in status_info:
                click.echo(f"  Error: {status_info['error']}", err=True)
            return

        # Perform installation
        success, message = install_mcp_server(dry_run=dry_run)

        if success:
            if not dry_run:
                click.echo("\n✅ Installation complete!")
                click.echo("   Restart Claude Desktop to activate Vidurai memory.")
        else:
            click.echo(f"\n❌ Installation failed: {message}", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command('get-context-json')
@click.option('--project', default='.', help='Project path (default: current directory)')
@click.option('--query', help='Context query to filter relevant memories')
@click.option('--max-tokens', default=2000, help='Maximum tokens in output')
@click.option('--audience', type=click.Choice(['developer', 'ai', 'manager', 'personal']),
              help='Audience perspective for gists')
def get_context_json(project, query, max_tokens, audience):
    """Get project context as JSON (stdout only, for piping)

    This command outputs ONLY valid JSON to stdout, making it suitable
    for piping to other tools or parsing programmatically.

    All status messages and logs go to stderr.

    Examples:
        vidurai get-context-json                          # Get context as JSON
        vidurai get-context-json --query "auth" | jq .    # Pipe to jq
        vidurai get-context-json --project /path/to/proj  # Specific project
    """
    # [CTO Mandate] Canonicalize path to prevent split-brain projects
    project = os.path.abspath(project)
    try:
        # All informational output goes to stderr
        print(f"[Vidurai] Fetching context for: {project}", file=sys.stderr)
        if query:
            print(f"[Vidurai] Query filter: {query}", file=sys.stderr)

        # Lazy import
        from vidurai.vismriti_memory import VismritiMemory
        
        memory = VismritiMemory(project_path=project)
        ctx = memory.get_context_for_ai(query=query, max_tokens=max_tokens, audience=audience)

        # Build JSON output
        output = {
            "project": str(Path(project).resolve()),
            "query": query,
            "audience": audience,
            "max_tokens": max_tokens,
            "context": ctx,
            "timestamp": datetime.now().isoformat(),
            "version": __version__
        }

        # ONLY valid JSON to stdout
        print(json.dumps(output, indent=2, ensure_ascii=False))

        # Phase 6: Publish CLI event (to stderr implicitly via logger)
        EVENT_BUS_AVAILABLE = _check_event_bus()
        if EVENT_BUS_AVAILABLE:
            try:
                from vidurai.shared.events import publish_event
                publish_event(
                    "cli.get_context_json",
                    source="cli",
                    project_path=project,
                    query=query or "all",
                    max_tokens=max_tokens,
                    audience=audience,
                    context_length=len(ctx)
                )
            except Exception:
                pass  # Silent fail for event publishing

    except Exception as e:
        # Error output as JSON to stdout for consistency
        error_output = {
            "error": str(e),
            "project": str(Path(project).resolve()),
            "timestamp": datetime.now().isoformat(),
            "version": __version__
        }
        print(json.dumps(error_output, indent=2, ensure_ascii=False))
        print(f"[Vidurai] Error: {e}", file=sys.stderr)
        sys.exit(1)


# ============================================================================
# Sprint 2: Knowledge Ingestion - "Ghost in the Shell"
# ============================================================================

@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--type', 'source_type', default='auto',
              type=click.Choice(['auto', 'openai', 'anthropic', 'gemini']),
              help='Source type: openai, anthropic, gemini, or auto-detect')
@click.option('--project', default='.', help='Project path for storage')
@click.option('--dry-run', is_flag=True, help='Preview without storing')
@click.option('--preview', is_flag=True, help='Show first 5 events and exit')
@click.option('--skip-system', is_flag=True, help='Skip system messages')
def ingest(file_path, source_type, project, dry_run, preview, skip_system):
    """Ingest historical AI conversations (Ghost in the Shell).

    Import your ChatGPT, Claude, or Gemini conversation history into Vidurai
    with original timestamps preserved and PII automatically sanitized.

    Supports large files (>500MB) via streaming - never loads full file into memory.

    Examples:
        vidurai ingest conversations.json                    # Auto-detect format
        vidurai ingest history.json --type anthropic         # Explicit format
        vidurai ingest export.json --preview                 # Preview first events
        vidurai ingest export.json --dry-run                 # Count without storing
        vidurai ingest export.json --project /my/project     # Store to specific project
    """
    # [CTO Mandate] Canonicalize path to prevent split-brain projects
    project = os.path.abspath(project)
    if not INGESTION_AVAILABLE:
        click.echo("❌ Ingestion module not available. Check installation.", err=True)
        click.echo("   Try: pip install ijson>=3.2.0", err=True)
        sys.exit(1)

    file_path = Path(file_path)
    file_size_mb = file_path.stat().st_size / (1024 * 1024)

    click.echo(f"\n📥 Vidurai Knowledge Ingestion", err=True)
    click.echo(f"   File: {file_path.name} ({file_size_mb:.1f} MB)", err=True)
    click.echo(f"   Type: {source_type}", err=True)
    click.echo(f"   Project: {Path(project).resolve()}", err=True)

    if dry_run:
        click.echo(f"   Mode: DRY RUN (no storage)", err=True)

    try:
        manager = IngestionManager(project_path=project)

        # Preview mode - just show first events
        if preview:
            click.echo(f"\n📋 Preview (first 5 events):\n", err=True)
            events = manager.preview_file(str(file_path), source_type, max_events=5)

            if not events:
                click.echo("   No events found or could not parse file.", err=True)
                return

            for i, event in enumerate(events, 1):
                click.echo(f"   [{i}] {event['role'].upper()} @ {event['timestamp'][:19]}", err=True)
                if event.get('conversation_title'):
                    click.echo(f"       Conversation: {event['conversation_title']}", err=True)
                click.echo(f"       {event['content']}", err=True)
                click.echo("", err=True)

            click.echo(f"   Use 'vidurai ingest {file_path}' to import all events.", err=True)
            return

        # Build skip roles list
        skip_roles = []
        if skip_system:
            skip_roles.append('system')

        # Progress tracking
        last_update = [0]  # Use list for closure mutation

        def progress_callback(count: int, message: str):
            # Update every 100 events or when significant progress
            if count - last_update[0] >= 100:
                if TQDM_AVAILABLE:
                    # tqdm handles its own output
                    pass
                else:
                    click.echo(f"   Processed {count} events...", err=True)
                last_update[0] = count

        manager.progress_callback = progress_callback

        # Process file
        click.echo(f"\n🔄 Processing...", err=True)

        if TQDM_AVAILABLE and not dry_run:
            # Use tqdm progress bar (estimates based on file size)
            # Rough estimate: 1KB per event on average
            estimated_events = int(file_size_mb * 1024)  # ~1KB per event

            with tqdm(total=estimated_events, desc="Ingesting", unit="events",
                      file=sys.stderr, leave=True) as pbar:
                def tqdm_callback(count: int, message: str):
                    pbar.update(count - pbar.n)

                manager.progress_callback = tqdm_callback
                stats = manager.process_file(
                    str(file_path),
                    source_type=source_type,
                    skip_roles=skip_roles,
                    dry_run=dry_run
                )
                pbar.total = stats.events_processed
                pbar.refresh()
        else:
            stats = manager.process_file(
                str(file_path),
                source_type=source_type,
                skip_roles=skip_roles,
                dry_run=dry_run
            )

        # Show results
        click.echo(f"\n✅ Ingestion Complete!", err=True)
        click.echo(f"   Duration: {stats.duration_seconds:.1f}s", err=True)
        click.echo(f"   Events processed: {stats.events_processed}", err=True)
        click.echo(f"   Events stored: {stats.events_stored}", err=True)
        click.echo(f"   Events skipped: {stats.events_skipped}", err=True)
        click.echo(f"   Conversations: {stats.conversations_count}", err=True)
        click.echo(f"   PII redactions: {stats.pii_redactions}", err=True)

        if stats.errors > 0:
            click.echo(f"   ⚠️  Errors: {stats.errors}", err=True)

        if stats.events_per_second > 0:
            click.echo(f"   Speed: {stats.events_per_second:.0f} events/sec", err=True)

        if dry_run:
            click.echo(f"\n   (Dry run - no data was stored)", err=True)
        else:
            click.echo(f"\n   Use 'vidurai recall --project {project}' to search imported memories.", err=True)

    except Exception as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


# ============================================================================
# Sprint 3: The Interaction Layer - Chat REPL
# ============================================================================

@cli.command()
@click.option('--project', default='.', help='Project context path')
def chat(project):
    """Start the interactive Vidurai Voice session (REPL).

    Launch an interactive shell for:
    - Viewing files with syntax highlighting
    - Searching project memories
    - Getting AI-ready context

    The REPL uses a Hybrid Intent Router to understand your queries:
    - File names -> Show file contents
    - Code verbs (show, cat, read) -> Code retrieval
    - Other text -> Memory search

    Examples:
        vidurai chat                      # Start in current directory
        vidurai chat --project /my/proj   # Start with specific project
    """
    # [CTO Mandate] Canonicalize path to prevent split-brain projects
    project = os.path.abspath(project)
    
    # Lazy import and availability check
    try:
        import prompt_toolkit
        from vidurai.repl import ViduraiREPL
        REPL_AVAILABLE = True
    except ImportError:
        REPL_AVAILABLE = False
    
    if not REPL_AVAILABLE:
        click.echo("❌ Interactive REPL not available.", err=True)
        click.echo("   Install dependencies: pip install prompt_toolkit pygments", err=True)
        sys.exit(1)

    try:
        from vidurai.repl import start_repl
        start_repl(project)
    except ImportError as e:
        click.echo(f"❌ Missing dependency: {e}", err=True)
        click.echo("   Install: pip install prompt_toolkit pygments", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error starting REPL: {e}", err=True)
        sys.exit(1)


# ============================================================================
# Sprint 4: The Shadow Layer - Safe Code Modification
# ============================================================================

@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--dry-run', is_flag=True, help='Show diff only, do not apply changes')
@click.option('--simulate', is_flag=True, help='(Test Mode) Appends a dummy comment to verify isolation')
@click.option('--show-info', is_flag=True, help='Show shadow workspace information')
def fix(file_path, dry_run, simulate, show_info):
    """Agentic Fixer (Shadow Mode). Safely modifies code in isolation.

    Uses a ShadowWorkspace to stage changes in a temporary directory,
    allowing you to preview diffs before applying to the real file.

    Zero Trust Architecture:
    - Original files are NEVER modified directly
    - All changes staged in shadow workspace
    - User must explicitly confirm before promotion

    Examples:
        vidurai fix src/main.py --simulate         # Test with dummy change
        vidurai fix src/main.py --simulate --dry-run  # Preview only
        vidurai fix src/main.py --show-info        # Show workspace info
    """
    from vidurai.core.shadow import ShadowWorkspace

    workspace = ShadowWorkspace('.')

    try:
        # Show workspace info
        if show_info:
            info = workspace.get_session_info()
            click.echo(f"\n🛡️ Shadow Workspace Info:")
            click.echo(f"   Session ID: {info['session_id']}")
            click.echo(f"   Project: {info['project_path']}")
            click.echo(f"   Shadow Root: {info['shadow_root']}")
            click.echo(f"   Created: {info['created_at'][:19]}")
            click.echo()

        # Stage the file
        shadow_path = workspace.stage_file(file_path)
        click.echo(f"\n🛡️ Shadow Workspace Active")
        click.echo(f"   Original: {file_path}")
        click.echo(f"   Shadow:   {shadow_path}")

        # Apply change (simulation or future real logic)
        if simulate:
            click.echo(f"\n🔧 Simulation Mode: Appending test comment...")
            with open(shadow_path, 'a') as f:
                f.write("\n# Fixed by Vidurai (Shadow Mode) - Test Comment\n")

            # Mark as modified in workspace
            workspace._staged_files[str(workspace._normalize_path(file_path))].modified = True

        # Get and display diff
        diff = workspace.get_diff(file_path)

        if not diff:
            click.echo("\n✨ No changes detected.")
            return

        # Show diff with stats
        stats = workspace.get_diff_stats(file_path)
        click.echo(f"\n📝 Proposed Changes:")
        click.echo(f"   +{stats['additions']} additions, -{stats['deletions']} deletions")
        click.echo()
        click.echo("─" * 60)

        # Colorize diff output
        for line in diff.splitlines():
            if line.startswith('+++') or line.startswith('---'):
                click.echo(click.style(line, bold=True))
            elif line.startswith('+'):
                click.echo(click.style(line, fg='green'))
            elif line.startswith('-'):
                click.echo(click.style(line, fg='red'))
            elif line.startswith('@@'):
                click.echo(click.style(line, fg='cyan'))
            else:
                click.echo(line)

        click.echo("─" * 60)

        # Apply or not
        if dry_run:
            click.echo(f"\n🔒 Dry-run mode: Real file untouched.")
            click.echo(f"   Remove --dry-run to apply changes.")
        else:
            click.echo()
            if click.confirm("⚠️  Promote changes to Production?"):
                workspace.promote_file(file_path)
                click.echo(f"\n✅ Fix applied to: {file_path}")
            else:
                click.echo(f"\n❌ Changes discarded. Original file untouched.")

    except FileNotFoundError as e:
        click.echo(f"\n❌ File not found: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
    finally:
        # ALWAYS cleanup - even on errors
        workspace.cleanup()
        click.echo(f"\n🧹 Shadow workspace cleaned up.")


@cli.command()
@click.option('--project', default='.', help='Project path (default: current directory)')
@click.confirmation_option(prompt='⚠️  Delete all memories for this project?')
def clear(project):
    """Clear all memories for a project (irreversible!)"""
    # [CTO Mandate] Canonicalize path to prevent split-brain projects
    project = os.path.abspath(project)
    try:
        db = MemoryDatabase()
        project_id = db.get_or_create_project(project)

        # Use proper connection with WAL mode for delete operation
        conn = db.get_connection_for_reading()
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memories WHERE project_id = ?", (project_id,))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        click.echo(f"✅ Deleted {deleted} memories from {Path(project).resolve().name}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def info():
    """Show Vidurai installation information"""
    # Lazy import
    from vidurai.storage.database import MemoryDatabase

    try:
        db = MemoryDatabase()

        click.echo("\n" + "=" * 60)
        click.echo("🧠 Vidurai - Persistent AI Memory Layer")
        click.echo("=" * 60)
        click.echo(f"Version: {__version__}")
        click.echo(f"Database: {db.db_path}")

        # Count total memories (using get_connection_for_reading for thread-safe reads)
        conn = db.get_connection_for_reading()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM memories")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM projects")
        projects = cursor.fetchone()[0]
        conn.close()

        click.echo(f"Total memories: {total}")
        click.echo(f"Total projects: {projects}")
        click.echo("=" * 60)
        click.echo("\nCommands:")
        click.echo("  vidurai stats            Show memory statistics")
        click.echo("  vidurai recall           Search memories")
        click.echo("  vidurai context          Get AI-ready context")
        click.echo("  vidurai recent           Show recent activity")
        click.echo("  vidurai server           Start MCP server")
        click.echo("  vidurai export           Export memories")
        click.echo("  vidurai clear            Clear project memories")
        click.echo("\nविस्मृति भी विद्या है — 'Forgetting too is knowledge'")
        click.echo("जय विदुराई! 🕉️\n")

        db.close()

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--project', default='.', help='Project path (default: current directory)')
@click.option('--max-hints', default=5, help='Maximum number of hints to display')
@click.option('--min-confidence', default=0.5, help='Minimum confidence threshold (0.0-1.0)')
@click.option('--hint-type', type=click.Choice(['similar_episode', 'pattern_warning', 'success_pattern', 'file_context']),
              multiple=True, help='Specific hint types to show')
@click.option('--show-context', is_flag=True, help='Show detailed context data')
def hints(project, max_hints, min_confidence, hint_type, show_context):
    """Show proactive hints based on your development history (Phase 6.6)"""
    # [CTO Mandate] Canonicalize path to prevent split-brain projects
    project = os.path.abspath(project)
    
    # Lazy import and availability check
    try:
        from vidurai.core.proactive_hints import HintGenerator, ProactiveHintEngine
        from vidurai.core.episode_builder import EpisodeBuilder
        HINTS_AVAILABLE = True
    except ImportError:
        HINTS_AVAILABLE = False
    
    if not HINTS_AVAILABLE:
        click.echo("❌ Proactive hints not available. Install required dependencies.", err=True)
        sys.exit(1)

    try:
        # Initialize components
        builder = EpisodeBuilder()
        hint_engine = ProactiveHintEngine(builder, min_similarity=min_confidence)

        # Get recent episodes for the project
        episodes = builder.get_closed_episodes(limit=50)
        
        if not episodes:
            click.echo("\n💡 No hints available yet.")
            click.echo("   Hints are generated from your development history.")
            click.echo("   Keep working and check back later!\n")
            return

        # Generate hints from the most recent episode
        recent_episode = episodes[0] if episodes else None
        if not recent_episode:
            click.echo("\n💡 No recent development episodes found.")
            return

        # Get hints
        hint_types_list = list(hint_type) if hint_type else None
        hints_list = hint_engine.generate_hints_for_episode(
            recent_episode,
            hint_types=hint_types_list
        )

        # Filter by confidence and limit
        filtered_hints = [h for h in hints_list if h.confidence >= min_confidence]
        filtered_hints = filtered_hints[:max_hints]

        if not filtered_hints:
            click.echo("\n💡 No hints meet the confidence threshold.")
            click.echo(f"   Try lowering --min-confidence (current: {min_confidence})")
            return

        # Display hints
        click.echo(f"\n💡 Found {len(filtered_hints)} hints for {Path(project).name}\n")
        
        for i, hint in enumerate(filtered_hints, 1):
            click.echo(f"{i}. [{hint.hint_type.upper()}] {hint.title}")
            click.echo(f"   Confidence: {hint.confidence:.2f}")
            click.echo(f"   {hint.description}")
            
            if show_context and hint.context:
                click.echo(f"   Context: {hint.context}")
            
            click.echo()

        # Show statistics
        stats = hint_engine.get_statistics()
        click.echo(f"📊 Statistics:")
        click.echo(f"  • Total episodes analyzed: {stats['total_episodes']}")
        click.echo(f"  • Recurring patterns detected: {stats['recurring_patterns']}")
        click.echo(f"  • Co-modification patterns: {stats['comodification_patterns']}")
        click.echo()

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def _get_salience_icon(salience: str) -> str:
    """Get icon for salience level"""
    icons = {
        'CRITICAL': '🔥',
        'HIGH': '⚡',
        'MEDIUM': '📝',
        'LOW': '💬',
        'NOISE': '🔇'
    }
    return icons.get(salience, '📌')


def _format_time_ago(dt: datetime) -> str:
    """Format datetime as human-readable time ago"""
    now = datetime.now()
    diff = now - dt

    if diff.days > 0:
        return f"{diff.days}d ago"
    elif diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f"{hours}h ago"
    elif diff.seconds >= 60:
        mins = diff.seconds // 60
        return f"{mins}m ago"
    else:
        return "just now"


# ============================================================================
# SF-V2 Commands: Memory Pinning & Forgetting Ledger
# ============================================================================

@cli.command()
@click.argument('memory_id', type=int)
@click.option('--project', default='.', help='Project path (default: current directory)')
@click.option('--reason', help='Reason for pinning this memory')
def pin(memory_id, project, reason):
    """Pin a memory to prevent it from being forgotten (SF-V2)"""
    # [CTO Mandate] Canonicalize path to prevent split-brain projects
    project = os.path.abspath(project)
    
    SF_V2_AVAILABLE = _check_sf_v2_available()
    if not SF_V2_AVAILABLE:
        click.echo("❌ SF-V2 components not available. Install latest version.", err=True)
        return

    try:
        # Lazy imports
        from vidurai.storage.database import MemoryDatabase
        from vidurai.core.memory_pin_manager import MemoryPinManager
        
        db = MemoryDatabase()
        pin_manager = MemoryPinManager(db)

        success = pin_manager.pin(memory_id, reason=reason, pinned_by='user')

        if success:
            click.echo(f"📌 Pinned memory {memory_id}")
            if reason:
                click.echo(f"   Reason: {reason}")
            click.echo(f"   This memory will NEVER be forgotten.")
        else:
            click.echo(f"❌ Failed to pin memory {memory_id}", err=True)
            click.echo(f"   Check: memory exists, not at pin limit (50/project)", err=True)

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)


@cli.command()
@click.argument('memory_id', type=int)
@click.option('--project', default='.', help='Project path (default: current directory)')
def unpin(memory_id, project):
    """Unpin a memory to allow forgetting (SF-V2)"""
    # [CTO Mandate] Canonicalize path to prevent split-brain projects
    project = os.path.abspath(project)
    
    SF_V2_AVAILABLE = _check_sf_v2_available()
    if not SF_V2_AVAILABLE:
        click.echo("❌ SF-V2 components not available.", err=True)
        return

    try:
        # Lazy imports
        from vidurai.storage.database import MemoryDatabase
        from vidurai.core.memory_pin_manager import MemoryPinManager
        
        db = MemoryDatabase()
        pin_manager = MemoryPinManager(db)

        success = pin_manager.unpin(memory_id)

        if success:
            click.echo(f"📍 Unpinned memory {memory_id}")
            click.echo(f"   This memory can now be forgotten by retention policies.")
        else:
            click.echo(f"❌ Failed to unpin memory {memory_id}", err=True)

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)


@cli.command()
@click.option('--project', default='.', help='Project path (default: current directory)')
@click.option('--show-content', is_flag=True, help='Show memory content (not just IDs)')
def pins(project, show_content):
    """List all pinned memories (SF-V2)"""
    # [CTO Mandate] Canonicalize path to prevent split-brain projects
    project = os.path.abspath(project)
    
    SF_V2_AVAILABLE = _check_sf_v2_available()
    if not SF_V2_AVAILABLE:
        click.echo("❌ SF-V2 components not available.", err=True)
        return

    try:
        # Lazy imports
        from vidurai.storage.database import MemoryDatabase
        from vidurai.core.memory_pin_manager import MemoryPinManager
        
        db = MemoryDatabase()
        pin_manager = MemoryPinManager(db)

        pinned_memories = pin_manager.get_pinned_memories(project)

        if not pinned_memories:
            click.echo("📌 No pinned memories for this project.")
            return

        click.echo(f"📌 Pinned Memories ({len(pinned_memories)}):\n")

        for mem in pinned_memories:
            click.echo(f"  ID: {mem['id']}")
            click.echo(f"     Salience: {mem['salience']}")
            click.echo(f"     Created: {mem['created_at'][:19]}")

            if show_content:
                click.echo(f"     Gist: {mem['gist'][:100]}...")

            click.echo()

        # Show statistics
        stats = pin_manager.get_statistics()
        total_pins = stats.get('total_pins', 0)
        max_pins = stats.get('max_pins_per_project', 50)

        click.echo(f"Total Pins Across All Projects: {total_pins}")
        click.echo(f"Max Pins Per Project: {max_pins}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)


@cli.command(name="forgetting-log")
@click.option('--limit', default=10, help='Number of events to show (default: 10)')
@click.option('--project', help='Filter by project path')
@click.option('--event-type', type=click.Choice(['consolidation', 'decay', 'aggregation']),
              help='Filter by event type')
def forgetting_log(limit, project, event_type):
    """Show forgetting event log for transparency (SF-V2)"""
    # [CTO Mandate] Canonicalize path to prevent split-brain projects
    if project:
        project = os.path.abspath(project)
    
    SF_V2_AVAILABLE = _check_sf_v2_available()
    if not SF_V2_AVAILABLE:
        click.echo("❌ SF-V2 components not available.", err=True)
        return

    try:
        # Lazy import
        from vidurai.core.forgetting_ledger import get_ledger
        
        ledger = get_ledger()
        events = ledger.get_events(project=project, event_type=event_type, limit=limit)

        if not events:
            click.echo("📋 No forgetting events recorded.")
            return

        click.echo(f"📋 Forgetting Log (last {len(events)} events):\n")

        for event in events:
            timestamp = event.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            compression = event.get_compression_ratio()

            click.echo(f"[{timestamp}] {event.event_type.upper()}")
            click.echo(f"  Action: {event.action}")
            click.echo(f"  Reason: {event.reason}")
            click.echo(f"  Impact: {event.memories_before} → {event.memories_after} memories ({compression:.0%} reduction)")

            if event.entities_preserved > 0:
                click.echo(f"  Preserved: {event.entities_preserved} entities, "
                          f"{event.root_causes_preserved} root causes, "
                          f"{event.resolutions_preserved} resolutions")

            click.echo(f"  Policy: {event.policy}")
            click.echo(f"  Reversible: {'Yes' if event.reversible else 'No'}")
            click.echo()

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)


@cli.command(name="forgetting-stats")
@click.option('--project', help='Filter by project path')
@click.option('--days', default=30, help='Look back N days (default: 30)')
def forgetting_stats(project, days):
    """Show forgetting statistics (SF-V2)"""
    # Lazy import SF-V2 components
    try:
        from vidurai.core.forgetting_ledger import get_ledger
    except ImportError:
        click.echo("❌ SF-V2 components not available.", err=True)
        return

    # [CTO Mandate] Canonicalize path to prevent split-brain projects
    if project:
        project = os.path.abspath(project)

    try:
        from datetime import timedelta

        ledger = get_ledger()
        since = datetime.now() - timedelta(days=days)
        stats = ledger.get_statistics(project=project, since=since)

        if stats['total_events'] == 0:
            click.echo(f"📊 No forgetting events in last {days} days.")
            return

        click.echo(f"📊 Forgetting Statistics (last {days} days):\n")
        click.echo(f"Total Events: {stats['total_events']}")
        click.echo(f"Events by Type:")

        for event_type, count in stats['by_type'].items():
            click.echo(f"  {event_type}: {count}")

        click.echo(f"\nMemories Removed: {stats['total_memories_removed']}")
        click.echo(f"Entities Preserved: {stats['total_entities_preserved']}")
        click.echo(f"Root Causes Preserved: {stats['total_root_causes_preserved']}")
        click.echo(f"Resolutions Preserved: {stats['total_resolutions_preserved']}")
        click.echo(f"Average Compression: {stats['average_compression_ratio']:.0%}")

        if stats['time_span']['oldest'] and stats['time_span']['newest']:
            click.echo(f"\nTime Span:")
            click.echo(f"  Oldest Event: {stats['time_span']['oldest'][:19]}")
            click.echo(f"  Newest Event: {stats['time_span']['newest'][:19]}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)


@cli.command()
@click.option('--project', help='Filter by project path')
@click.option('--force', is_flag=True, help='Skip confirmation prompt')
def hygiene(project, force):
    """
    Memory hygiene - Review and archive low-utility memories.

    The Constitution's Purgatory Protocol:
    1. Evaluate memories using Utility Score formula
    2. Mark low-utility memories as PENDING_DECAY
    3. User reviews and decides: Archive or Grant Mercy

    Utility Score Formula:
        score = (0.4 * log(access_count + 1)) +
                (0.4 * 1/(days_old + 1)) +
                (0.2 * outcome)

    Memories with score < 0.15 are marked for decay.
    Pinned memories are IMMUNE (never decayed).
    """
    # [CTO Mandate] Canonicalize path to prevent split-brain projects
    if project:
        project = os.path.abspath(project)

    try:
        from vidurai.core.constitution.retention import RetentionJudge

        judge = RetentionJudge()

        # Step 1: Evaluate all memories
        click.echo("🧹 Running memory hygiene check...\n")
        counts = judge.evaluate_all_memories()

        click.echo(f"📊 Evaluation Results:")
        click.echo(f"   Active:        {counts['active']}")
        click.echo(f"   Immune (📌):   {counts['immune']}")
        click.echo(f"   Pending Decay: {counts['pending_decay']}")
        click.echo()

        # Step 2: Check pending decay count
        pending = judge.get_pending_decay_count()

        if pending == 0:
            click.echo("✅ No memories marked for decay. Your memory is healthy!")
            return

        click.echo(f"🗑️  Found {pending} memories marked for decay (Low Utility).\n")

        # Step 3: User decision
        if force:
            action = 'y'
        else:
            click.echo("What would you like to do?")
            click.echo("  [y] Archive these memories (remove from active context)")
            click.echo("  [n] Grant mercy (bump access count, keep active)")
            click.echo("  [q] Quit (leave as PENDING_DECAY for later)")
            action = click.prompt("Your choice", type=click.Choice(['y', 'n', 'q']), default='q')

        # Step 4: Execute action
        if action == 'y':
            archived = judge.archive_pending()
            click.echo(f"\n✅ Archived {archived} memories.")
            click.echo("   (Status changed to ARCHIVED, removed from active context)")

        elif action == 'n':
            saved = judge.grant_mercy()
            click.echo(f"\n✅ Granted mercy to {saved} memories.")
            click.echo("   (Access count bumped, status returned to ACTIVE)")

        else:
            click.echo("\n⏸️  No action taken. Memories remain in PENDING_DECAY.")
            click.echo("   Run 'vidurai hygiene' again later to review.")

    except ImportError:
        click.echo("❌ Constitution module not available.", err=True)
        click.echo("   Please ensure vidurai.core.constitution is installed.", err=True)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)


@cli.command()
@click.argument('code', required=False)
@click.option('--file', '-f', help='File to audit')
def audit(code, file):
    """
    Audit code for security risks.

    Checks Python code for dangerous patterns:
    - Banned imports (os, subprocess, shutil, sys)
    - Dangerous calls (os.system, eval, exec)

    Examples:
        vidurai audit "import os; os.system('ls')"
        vidurai audit -f /path/to/script.py
    """
    try:
        from vidurai.core.verification.auditor import CodeAuditor

        auditor = CodeAuditor()

        if file:
            # Audit file
            warnings, language = auditor.scan_file(file)
            click.echo(f"🔍 Auditing: {file} (detected: {language})\n")
        elif code:
            # Audit code string
            warnings = auditor.scan_safety(code)
            click.echo(f"🔍 Auditing code snippet...\n")
        else:
            click.echo("❌ Please provide code or --file option.", err=True)
            return

        if warnings:
            click.echo(f"⚠️  Found {len(warnings)} security warning(s):\n")
            for i, warning in enumerate(warnings, 1):
                click.echo(f"  {i}. {warning}")
            click.echo()
            click.echo("🛑 Code flagged for manual review.")
        else:
            click.echo("✅ No security issues found.")

    except ImportError:
        click.echo("❌ Verification module not available.", err=True)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)


if __name__ == '__main__':
    cli()
