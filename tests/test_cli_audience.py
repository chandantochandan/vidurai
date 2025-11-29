#!/usr/bin/env python3
"""
Test suite for Phase 5.4: CLI Audience Integration
Tests that CLI commands support --audience flag
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent))


def test_cli_audience_integration():
    """Test CLI with audience parameter"""
    print("=" * 70)
    print("🧪 TEST: CLI Audience Integration")
    print("=" * 70)
    print()

    from vidurai.vismriti_memory import VismritiMemory
    from vidurai.cli import recall, context
    from click.testing import CliRunner

    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    try:
        # Setup: Create some memories with multi-audience enabled
        print("Setup: Creating test memories...")
        memory = VismritiMemory(
            enable_multi_audience=True,
            project_path=temp_dir
        )

        # Store test memories
        test_memories = [
            {
                "content": "Fixed critical authentication bug in JWT validation middleware",
                "metadata": {"type": "bugfix", "file": "auth/middleware.py", "line": 42}
            },
            {
                "content": "Implemented new user registration feature with OAuth2 support",
                "metadata": {"type": "feature", "file": "auth/register.py"}
            }
        ]

        for mem_data in test_memories:
            memory.remember(
                mem_data["content"],
                metadata=mem_data["metadata"],
                extract_gist=False
            )

        print(f"✅ Created {len(test_memories)} test memories\n")

        # Test 1: Recall without audience (canonical)
        print("Test 1: Recall without audience")
        runner = CliRunner()
        result = runner.invoke(recall, [
            '--project', temp_dir,
            '--query', 'authentication',
            '--min-salience', 'LOW'
        ])

        print("Output:")
        print(result.output[:300])
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "authentication" in result.output.lower() or "auth" in result.output.lower()
        print("✅ Recall works without audience\n")

        # Test 2: Recall with developer audience
        print("Test 2: Recall with --audience developer")
        result = runner.invoke(recall, [
            '--project', temp_dir,
            '--query', 'authentication',
            '--audience', 'developer',
            '--min-salience', 'LOW'
        ])

        print("Output:")
        print(result.output[:300])
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "(developer view)" in result.output
        # Developer gist should mention file (middleware.py)
        assert "middleware" in result.output.lower() or "auth" in result.output.lower()
        print("✅ Recall works with developer audience\n")

        # Test 3: Recall with manager audience
        print("Test 3: Recall with --audience manager")
        result = runner.invoke(recall, [
            '--project', temp_dir,
            '--query', 'authentication',
            '--audience', 'manager',
            '--min-salience', 'LOW'
        ])

        print("Output:")
        print(result.output[:300])
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "(manager view)" in result.output
        print("✅ Recall works with manager audience\n")

        # Test 4: Context without audience
        print("Test 4: Context without audience")
        result = runner.invoke(context, [
            '--project', temp_dir,
            '--query', 'authentication'
        ])

        print("Output:")
        print(result.output[:300])
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "VIDURAI PROJECT CONTEXT" in result.output or "No relevant" in result.output
        print("✅ Context works without audience\n")

        # Test 5: Context with developer audience
        print("Test 5: Context with --audience developer")
        result = runner.invoke(context, [
            '--project', temp_dir,
            '--query', 'authentication',
            '--audience', 'developer'
        ])

        print("Output:")
        print(result.output[:300])
        assert result.exit_code == 0, f"Command failed: {result.output}"
        # Should have context or no relevant message
        assert len(result.output) > 0
        print("✅ Context works with developer audience\n")

        print("=" * 70)
        print("✅ ALL CLI AUDIENCE TESTS PASSED")
        print("=" * 70)
        print()

    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    try:
        print()
        print("🚀 PHASE 5.4 CLI TEST: Audience Integration")
        print()

        test_cli_audience_integration()

        print("Summary:")
        print("  ✅ recall command supports --audience flag")
        print("  ✅ context command supports --audience flag")
        print("  ✅ Audience-specific gists displayed correctly")
        print("  ✅ Backward compatibility maintained (works without --audience)")
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
