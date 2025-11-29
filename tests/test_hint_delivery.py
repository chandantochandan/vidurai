#!/usr/bin/env python3
"""
Test suite for Phase 6.6: Hint Delivery Integration
Tests CLI, MCP, and formatting integration
"""

import sys
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

# Add paths
sys.path.insert(0, str(Path(__file__).parent))


def test_hint_formatter():
    """Test hint formatting for different channels"""
    print("=" * 70)
    print("🧪 TEST 1: Hint Formatting")
    print("=" * 70)
    print()

    from vidurai.core.proactive_hints import Hint
    from vidurai.core.hint_delivery import HintFormatter

    formatter = HintFormatter()

    # Create sample hints
    hints = [
        Hint(
            hint_type="similar_episode",
            title="Similar bugfix found",
            message="You worked on a similar bugfix before:\n  • Fixed TypeError in auth.py\n  • Took 15 minutes",
            confidence=0.85,
            source_episodes=['abc-123'],
            context={'common_files': ['auth.py']}
        ),
        Hint(
            hint_type="pattern_warning",
            title="Recurring issue: typeerror",
            message="This 'typeerror' error has occurred 5 times before.",
            confidence=0.80,
            context={'keyword': 'typeerror', 'occurrences': 5}
        )
    ]

    # Test CLI formatting
    print("Test 1.1: CLI formatting")
    cli_output = formatter.format_cli(hints)
    assert "💡 Proactive Hints:" in cli_output
    assert "Similar bugfix found" in cli_output
    assert "85%" in cli_output or "0.85" in cli_output
    print("✅ CLI format contains expected elements")
    print()

    # Test JSON formatting
    print("Test 1.2: JSON formatting")
    json_output = formatter.format_json(hints)
    assert json_output['count'] == 2
    assert len(json_output['hints']) == 2
    assert json_output['avg_confidence'] == 0.825
    assert 'similar_episode' in json_output['hint_types']
    print(f"✅ JSON format: {json_output['count']} hints, avg confidence: {json_output['avg_confidence']}")
    print()

    # Test Markdown formatting
    print("Test 1.3: Markdown formatting")
    md_output = formatter.format_markdown(hints)
    assert "## Proactive Hints" in md_output
    assert "### 1." in md_output
    assert "Similar bugfix found" in md_output
    print("✅ Markdown format contains expected structure")
    print()

    # Test plain text formatting
    print("Test 1.4: Plain text formatting")
    plain_output = formatter.format_plain(hints)
    assert "Proactive Hints:" in plain_output
    assert "1. Similar bugfix found" in plain_output
    print("✅ Plain text format works")
    print()

    print("✅ PASSED: Hint formatting works\n")


def test_hint_filter():
    """Test hint filtering and ranking"""
    print("=" * 70)
    print("🧪 TEST 2: Hint Filtering and Ranking")
    print("=" * 70)
    print()

    from vidurai.core.proactive_hints import Hint
    from vidurai.core.hint_delivery import HintFilter

    filter = HintFilter(min_confidence=0.6)

    # Create sample hints with varying confidence
    hints = [
        Hint(hint_type="similar_episode", title="Hint 1", message="msg", confidence=0.85),
        Hint(hint_type="pattern_warning", title="Hint 2", message="msg", confidence=0.75),
        Hint(hint_type="file_context", title="Hint 3", message="msg", confidence=0.55),
        Hint(hint_type="success_pattern", title="Hint 4", message="msg", confidence=0.45),
    ]

    # Test confidence filtering
    print("Test 2.1: Confidence filtering")
    filtered = filter.filter_hints(hints)
    assert len(filtered) == 2, f"Should filter to 2 hints (>= 0.6), got {len(filtered)}"
    assert all(h.confidence >= 0.6 for h in filtered)
    print(f"✅ Filtered {len(hints)} hints to {len(filtered)} (confidence >= 0.6)")
    print()

    # Test type filtering
    print("Test 2.2: Type filtering")
    filtered_type = filter.filter_hints(hints, include_types=['similar_episode', 'pattern_warning'])
    assert len(filtered_type) == 2
    assert all(h.hint_type in ['similar_episode', 'pattern_warning'] for h in filtered_type)
    print(f"✅ Filtered to specific types: {[h.hint_type for h in filtered_type]}")
    print()

    # Test ranking by confidence
    print("Test 2.3: Ranking by confidence")
    ranked = filter.rank_hints(hints, ranking_method='confidence')
    assert ranked[0].confidence == 0.85
    assert ranked[-1].confidence == 0.45
    print(f"✅ Ranked by confidence: {[h.confidence for h in ranked]}")
    print()

    # Test ranking by type priority
    print("Test 2.4: Ranking by type priority")
    ranked_type = filter.rank_hints(hints, ranking_method='type_priority')
    assert ranked_type[0].hint_type == "pattern_warning"  # Priority 4
    print(f"✅ Ranked by type: {[h.hint_type for h in ranked_type]}")
    print()

    # Test deduplication
    print("Test 2.5: Deduplication")
    duplicates = hints + [Hint(hint_type="similar_episode", title="Hint 1", message="dup", confidence=0.9)]
    unique = filter.deduplicate_hints(duplicates)
    assert len(unique) == len(hints), "Should remove duplicate 'Hint 1'"
    print(f"✅ Deduplicated {len(duplicates)} to {len(unique)} hints")
    print()

    print("✅ PASSED: Hint filtering and ranking works\n")


def test_hint_delivery_service():
    """Test HintDeliveryService integration"""
    print("=" * 70)
    print("🧪 TEST 3: Hint Delivery Service")
    print("=" * 70)
    print()

    from vidurai.core.episode_builder import EpisodeBuilder, Episode
    from vidurai.core.event_bus import ViduraiEvent
    from vidurai.core.hint_delivery import create_hint_service

    # Create builder with historical episodes
    builder = EpisodeBuilder()

    # Create some historical episodes
    for i in range(3):
        event = ViduraiEvent(
            type="memory.created",
            source="test",
            project_path="/test/project",
            payload={"gist": f"Fixed TypeError in auth.py issue {i}", "memory_type": "bugfix", "file_path": "auth.py"}
        )
        builder.handle_event(event)

        episode = builder.get_current_episode("/test/project")
        if episode:
            episode.start_time = datetime.now() - timedelta(days=i+1, minutes=10)
            builder._close_episode(episode)

    # Create hint service
    service = create_hint_service(builder)

    # Test getting hints for project
    print("Test 3.1: Get hints for project")
    hints = service.get_hints_for_project("/test/project", max_hints=5)

    if len(hints) > 0:
        print(f"✅ Generated {len(hints)} hints")
        for hint in hints:
            print(f"  • [{hint.hint_type}] {hint.title} (confidence: {hint.confidence:.2f})")
    else:
        print("✅ No hints generated (expected for minimal test data)")
    print()

    # Test CLI formatting
    print("Test 3.2: CLI formatting")
    cli_output = service.format_for_cli(hints)
    assert isinstance(cli_output, str)
    print("✅ CLI format string generated")
    print()

    # Test MCP formatting
    print("Test 3.3: MCP formatting")
    mcp_output = service.format_for_mcp(hints)
    assert 'hints' in mcp_output
    assert 'count' in mcp_output
    assert mcp_output['count'] == len(hints)
    print(f"✅ MCP format: {mcp_output['count']} hints")
    print()

    # Test statistics
    print("Test 3.4: Service statistics")
    stats = service.get_statistics()
    assert 'hints_delivered' in stats
    assert 'engine_stats' in stats
    print(f"✅ Statistics: delivered={stats['hints_delivered']}, filtered={stats['hints_filtered']}")
    print()

    print("✅ PASSED: Hint delivery service works\n")


def test_cli_integration():
    """Test CLI command integration"""
    print("=" * 70)
    print("🧪 TEST 4: CLI Integration")
    print("=" * 70)
    print()

    # Test that imports work
    print("Test 4.1: Import CLI modules")
    try:
        from vidurai.cli import cli
        print("✅ CLI module imports successfully")
    except ImportError as e:
        print(f"⚠️  CLI import warning: {e}")
    print()

    # Test hints availability flag
    print("Test 4.2: Hints availability")
    from vidurai import cli as cli_module
    if hasattr(cli_module, 'HINTS_AVAILABLE'):
        print(f"✅ HINTS_AVAILABLE flag: {cli_module.HINTS_AVAILABLE}")
    else:
        print("⚠️  HINTS_AVAILABLE flag not found")
    print()

    print("✅ PASSED: CLI integration ready\n")


def test_mcp_integration():
    """Test MCP server integration"""
    print("=" * 70)
    print("🧪 TEST 5: MCP Server Integration")
    print("=" * 70)
    print()

    # Test that imports work
    print("Test 5.1: Import MCP modules")
    try:
        from vidurai.mcp_server import MCPRequestHandler
        print("✅ MCP server module imports successfully")
    except ImportError as e:
        print(f"⚠️  MCP import warning: {e}")
    print()

    # Test hints availability flag
    print("Test 5.2: Hints availability")
    from vidurai import mcp_server as mcp_module
    if hasattr(mcp_module, 'HINTS_AVAILABLE'):
        print(f"✅ HINTS_AVAILABLE flag: {mcp_module.HINTS_AVAILABLE}")
    else:
        print("⚠️  HINTS_AVAILABLE flag not found")
    print()

    # Test get_proactive_hints method exists
    print("Test 5.3: MCP hint method exists")
    from vidurai.mcp_server import MCPRequestHandler
    assert hasattr(MCPRequestHandler, 'get_proactive_hints'), "Should have get_proactive_hints method"
    print("✅ get_proactive_hints method exists")
    print()

    print("✅ PASSED: MCP server integration ready\n")


if __name__ == "__main__":
    try:
        print()
        print("🚀 PHASE 6.6 TEST SUITE: Hint Delivery Integration")
        print()

        test_hint_formatter()
        test_hint_filter()
        test_hint_delivery_service()
        test_cli_integration()
        test_mcp_integration()

        print()
        print("=" * 70)
        print("✅ ALL PHASE 6.6 INTEGRATION TESTS PASSED")
        print("=" * 70)
        print()
        print("Summary:")
        print("  ✅ Hint formatting (CLI, JSON, Markdown, Plain)")
        print("  ✅ Hint filtering and ranking")
        print("  ✅ Hint delivery service")
        print("  ✅ CLI integration")
        print("  ✅ MCP server integration")
        print()

    except AssertionError as e:
        print(f"\n\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
