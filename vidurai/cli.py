#!/usr/bin/env python3
"""
Vidurai CLI Tool
Standalone command-line interface for memory management
v2.0 - Phase 2

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
"""

import click
import json
import sys
from pathlib import Path
from datetime import datetime

try:
    from tabulate import tabulate
    TABULATE_AVAILABLE = True
except ImportError:
    TABULATE_AVAILABLE = False

from vidurai.storage.database import MemoryDatabase, SalienceLevel
from vidurai.vismriti_memory import VismritiMemory
from vidurai.version import __version__

# Phase 6: Event Bus integration
try:
    from vidurai.core.event_bus import publish_event
    EVENT_BUS_AVAILABLE = True
except ImportError:
    EVENT_BUS_AVAILABLE = False

# Phase 6.6: Proactive Hints integration
try:
    from vidurai.core.episode_builder import EpisodeBuilder
    from vidurai.core.hint_delivery import create_hint_service
    HINTS_AVAILABLE = True
except ImportError:
    HINTS_AVAILABLE = False

# SF-V2: Smart Forgetting integration
try:
    from vidurai.core.memory_pinning import MemoryPinManager
    from vidurai.core.forgetting_ledger import get_ledger
    SF_V2_AVAILABLE = True
except ImportError:
    SF_V2_AVAILABLE = False


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
    try:
        db = MemoryDatabase()
        salience = SalienceLevel[min_salience]

        memories = db.recall_memories(
            project_path=project,
            query=query,
            min_salience=salience,
            limit=limit
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
        if EVENT_BUS_AVAILABLE:
            try:
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

        if TABULATE_AVAILABLE:
            # Pretty table output
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
    try:
        memory = VismritiMemory(project_path=project)
        ctx = memory.get_context_for_ai(query=query, max_tokens=max_tokens, audience=audience)

        click.echo(ctx)

        # Phase 6.6: Show proactive hints
        if show_hints and HINTS_AVAILABLE:
            try:
                builder = EpisodeBuilder()
                hint_service = create_hint_service(builder)
                hints = hint_service.get_hints_for_project(
                    project_path=project,
                    max_hints=max_hints
                )

                if hints:
                    hint_output = hint_service.format_for_cli(hints)
                    click.echo(hint_output)
            except Exception as e:
                # Silent fail for hints - don't break context display
                click.echo(f"\n⚠️  Hints unavailable: {e}", err=True)

        # Phase 6: Publish CLI context event
        if EVENT_BUS_AVAILABLE:
            try:
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
    try:
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
    try:
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
    try:
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


@cli.command()
@click.option('--project', default='.', help='Project path (default: current directory)')
@click.confirmation_option(prompt='⚠️  Delete all memories for this project?')
def clear(project):
    """Clear all memories for a project (irreversible!)"""
    try:
        db = MemoryDatabase()
        project_id = db.get_or_create_project(project)

        cursor = db.conn.cursor()
        cursor.execute("DELETE FROM memories WHERE project_id = ?", (project_id,))
        deleted = cursor.rowcount
        db.conn.commit()

        click.echo(f"✅ Deleted {deleted} memories from {Path(project).resolve().name}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def info():
    """Show Vidurai installation information"""
    try:
        db = MemoryDatabase()

        click.echo("\n" + "=" * 60)
        click.echo("🧠 Vidurai - Persistent AI Memory Layer")
        click.echo("=" * 60)
        click.echo(f"Version: {__version__}")
        click.echo(f"Database: {db.db_path}")

        # Count total memories
        cursor = db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM memories")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM projects")
        projects = cursor.fetchone()[0]

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
    if not HINTS_AVAILABLE:
        click.echo("❌ Proactive hints not available. Install required dependencies.", err=True)
        sys.exit(1)

    try:
        builder = EpisodeBuilder()
        hint_service = create_hint_service(builder)

        # Get hints
        hint_types = list(hint_type) if hint_type else None
        hints_list = hint_service.get_hints_for_project(
            project_path=project,
            hint_types=hint_types,
            min_confidence=min_confidence,
            max_hints=max_hints
        )

        if not hints_list:
            click.echo("\n💡 No hints available yet.")
            click.echo("   Hints are generated from your development history.")
            click.echo("   Keep working and check back later!\n")
            return

        # Format and display
        hint_output = hint_service.format_for_cli(hints_list, show_context=show_context)
        click.echo(hint_output)

        # Show statistics
        stats = hint_service.get_statistics()
        click.echo(f"\n📊 Statistics:")
        click.echo(f"  • Total episodes analyzed: {stats['engine_stats']['total_episodes']}")
        click.echo(f"  • Recurring patterns detected: {stats['engine_stats']['recurring_patterns']}")
        click.echo(f"  • Co-modification patterns: {stats['engine_stats']['comodification_patterns']}")
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
    if not SF_V2_AVAILABLE:
        click.echo("❌ SF-V2 components not available. Install latest version.", err=True)
        return

    try:
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
    if not SF_V2_AVAILABLE:
        click.echo("❌ SF-V2 components not available.", err=True)
        return

    try:
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
    if not SF_V2_AVAILABLE:
        click.echo("❌ SF-V2 components not available.", err=True)
        return

    try:
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


@cli.command()
@click.option('--limit', default=10, help='Number of events to show (default: 10)')
@click.option('--project', help='Filter by project path')
@click.option('--event-type', type=click.Choice(['consolidation', 'decay', 'aggregation']),
              help='Filter by event type')
def forgetting_log(limit, project, event_type):
    """Show forgetting event log for transparency (SF-V2)"""
    if not SF_V2_AVAILABLE:
        click.echo("❌ SF-V2 components not available.", err=True)
        return

    try:
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


@cli.command()
@click.option('--project', help='Filter by project path')
@click.option('--days', default=30, help='Look back N days (default: 30)')
def forgetting_stats(project, days):
    """Show forgetting statistics (SF-V2)"""
    if not SF_V2_AVAILABLE:
        click.echo("❌ SF-V2 components not available.", err=True)
        return

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


if __name__ == '__main__':
    cli()
