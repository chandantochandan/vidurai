#!/usr/bin/env python3
"""
Test suite for Phase 6.4: Auto-Memory Policy
Tests automatic conversion of episodes to memories
"""

import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

# Add paths
sys.path.insert(0, str(Path(__file__).parent))


def test_quality_filters():
    """Test should_create_memory() quality filters"""
    print("=" * 70)
    print("🧪 TEST 1: Quality Filters")
    print("=" * 70)
    print()

    from vidurai.core.auto_memory_policy import AutoMemoryPolicy
    from vidurai.core.episode_builder import Episode
    from vidurai.core.event_bus import ViduraiEvent

    policy = AutoMemoryPolicy(
        min_event_count=2,
        min_duration_minutes=1.0,
        auto_create_exploration=False,
        auto_create_unknown=False
    )

    # Test 1.1: Episode must be closed
    print("Test 1.1: Episode must be closed")
    episode = Episode(project_path="/test")
    episode.episode_type = "bugfix"
    episode.start_time = datetime.now() - timedelta(minutes=5)  # Set earlier start time
    event1 = ViduraiEvent(type="memory.created", source="test", project_path="/test", payload={"gist": "test"})
    event2 = ViduraiEvent(type="memory.created", source="test", project_path="/test", payload={"gist": "test"})
    episode.add_event(event1)
    episode.add_event(event2)

    assert not policy.should_create_memory(episode), "Open episode should be rejected"
    print("✅ Open episodes rejected")

    episode.close()
    assert policy.should_create_memory(episode), "Closed episode should be accepted"
    print("✅ Closed episodes accepted")
    print()

    # Test 1.2: Minimum event count
    print("Test 1.2: Minimum event count")
    episode2 = Episode(project_path="/test")
    episode2.episode_type = "bugfix"
    episode2.add_event(ViduraiEvent(type="memory.created", source="test", project_path="/test", payload={"gist": "single"}))
    episode2.close()

    assert not policy.should_create_memory(episode2), "Episode with 1 event should be rejected"
    print("✅ Episodes with too few events rejected")
    print()

    # Test 1.3: Minimum duration
    print("Test 1.3: Minimum duration")
    episode3 = Episode(project_path="/test")
    episode3.episode_type = "bugfix"
    episode3.add_event(ViduraiEvent(type="memory.created", source="test", project_path="/test", payload={"gist": "e1"}))
    episode3.add_event(ViduraiEvent(type="memory.created", source="test", project_path="/test", payload={"gist": "e2"}))
    # Simulate very short duration
    episode3.start_time = datetime.now() - timedelta(seconds=30)
    episode3.close()

    assert not policy.should_create_memory(episode3), "Episode too short should be rejected"
    print("✅ Episodes with too short duration rejected")
    print()

    # Test 1.4: Episode type filters
    print("Test 1.4: Episode type filters")
    episode4 = Episode(project_path="/test")
    episode4.episode_type = "unknown"
    episode4.start_time = datetime.now() - timedelta(minutes=5)
    episode4.add_event(ViduraiEvent(type="memory.created", source="test", project_path="/test", payload={"gist": "e1"}))
    episode4.add_event(ViduraiEvent(type="memory.created", source="test", project_path="/test", payload={"gist": "e2"}))
    episode4.close()

    assert not policy.should_create_memory(episode4), "Unknown type should be rejected by default"
    print("✅ Unknown type episodes rejected by default")

    # With auto_create_unknown enabled
    policy2 = AutoMemoryPolicy(auto_create_unknown=True)
    assert policy2.should_create_memory(episode4), "Unknown type should be accepted with flag"
    print("✅ Unknown type accepted when auto_create_unknown=True")
    print()

    # Test 1.5: Exploration episodes
    print("Test 1.5: Exploration episodes")
    episode5 = Episode(project_path="/test")
    episode5.episode_type = "exploration"
    episode5.start_time = datetime.now() - timedelta(minutes=5)
    episode5.add_event(ViduraiEvent(type="cli.context", source="test", project_path="/test", payload={"query": "q1"}))
    episode5.add_event(ViduraiEvent(type="cli.context", source="test", project_path="/test", payload={"query": "q2"}))
    episode5.close()

    assert not policy.should_create_memory(episode5), "Exploration should be rejected by default"
    print("✅ Exploration episodes rejected by default")

    policy3 = AutoMemoryPolicy(auto_create_exploration=True)
    assert policy3.should_create_memory(episode5), "Exploration should be accepted with flag"
    print("✅ Exploration accepted when auto_create_exploration=True")
    print()

    print("✅ PASSED: Quality filters work\n")


def test_salience_detection():
    """Test detect_salience() from episode metadata and types"""
    print("=" * 70)
    print("🧪 TEST 2: Salience Detection")
    print("=" * 70)
    print()

    from vidurai.core.auto_memory_policy import AutoMemoryPolicy
    from vidurai.core.episode_builder import Episode
    from vidurai.core.data_structures_v3 import SalienceLevel

    policy = AutoMemoryPolicy()

    # Test 2.1: Salience from metadata
    print("Test 2.1: Salience from episode metadata")
    episode = Episode(project_path="/test")
    episode.episode_type = "bugfix"
    episode.metadata['max_salience'] = "CRITICAL"

    salience = policy.detect_salience(episode)
    assert salience == SalienceLevel.CRITICAL, "Should use metadata salience"
    print(f"✅ Used metadata salience: {salience.name}")
    print()

    # Test 2.2: Bugfix heuristic
    print("Test 2.2: Bugfix salience heuristic")
    episode2 = Episode(project_path="/test")
    episode2.episode_type = "bugfix"

    salience = policy.detect_salience(episode2)
    assert salience == SalienceLevel.HIGH, "Bugfix should be HIGH"
    print(f"✅ Bugfix detected as: {salience.name}")
    print()

    # Test 2.3: Feature heuristic
    print("Test 2.3: Feature salience heuristic")
    episode3 = Episode(project_path="/test")
    episode3.episode_type = "feature"

    salience = policy.detect_salience(episode3)
    assert salience == SalienceLevel.MEDIUM, "Feature should be MEDIUM"
    print(f"✅ Feature detected as: {salience.name}")
    print()

    # Test 2.4: Refactor heuristic
    print("Test 2.4: Refactor salience heuristic")
    episode4 = Episode(project_path="/test")
    episode4.episode_type = "refactor"

    salience = policy.detect_salience(episode4)
    assert salience == SalienceLevel.MEDIUM, "Refactor should be MEDIUM"
    print(f"✅ Refactor detected as: {salience.name}")
    print()

    # Test 2.5: Exploration heuristic
    print("Test 2.5: Exploration salience heuristic")
    episode5 = Episode(project_path="/test")
    episode5.episode_type = "exploration"

    salience = policy.detect_salience(episode5)
    assert salience == SalienceLevel.LOW, "Exploration should be LOW"
    print(f"✅ Exploration detected as: {salience.name}")
    print()

    print("✅ PASSED: Salience detection works\n")


def test_gist_extraction():
    """Test extract_gist() from various episode configurations"""
    print("=" * 70)
    print("🧪 TEST 3: Gist Extraction")
    print("=" * 70)
    print()

    from vidurai.core.auto_memory_policy import AutoMemoryPolicy
    from vidurai.core.episode_builder import Episode
    from vidurai.core.event_bus import ViduraiEvent

    policy = AutoMemoryPolicy()

    # Test 3.1: Extract from episode summary
    print("Test 3.1: Extract from episode summary")
    episode = Episode(project_path="/test")
    episode.episode_type = "bugfix"
    episode.summary = "Fixed critical authentication bug in auth.py"
    episode.add_event(ViduraiEvent(type="memory.created", source="test", project_path="/test", payload={"gist": "something"}))

    gist = policy.extract_gist(episode)
    assert gist == episode.summary, "Should use episode summary"
    print(f"✅ Extracted from summary: '{gist}'")
    print()

    # Test 3.2: Extract from memory.created event
    print("Test 3.2: Extract from memory.created event")
    episode2 = Episode(project_path="/test")
    episode2.episode_type = "feature"
    episode2.start_time = datetime.now() - timedelta(minutes=2)  # Set earlier start
    event = ViduraiEvent(
        type="memory.created",
        source="test",
        project_path="/test",
        payload={"gist": "Implemented OAuth2 login flow", "file_path": "oauth.py"}
    )
    episode2.add_event(event)

    gist = policy.extract_gist(episode2)
    # Debug: print what we got
    if gist != "Implemented OAuth2 login flow":
        print(f"DEBUG: Expected 'Implemented OAuth2 login flow', got '{gist}'")
        print(f"DEBUG: Episode summary: '{episode2.summary}'")
        print(f"DEBUG: Episode events: {len(episode2.events)}")
        if episode2.events:
            print(f"DEBUG: First event type: {episode2.events[0].type}")
            print(f"DEBUG: First event payload: {episode2.events[0].payload}")
    assert gist == "Implemented OAuth2 login flow", f"Should extract from event payload, got '{gist}'"
    print(f"✅ Extracted from event: '{gist}'")
    print()

    # Test 3.3: Generate from metadata
    print("Test 3.3: Generate from episode metadata")
    episode3 = Episode(project_path="/test")
    episode3.episode_type = "refactor"
    episode3.start_time = datetime.now() - timedelta(minutes=15)
    episode3.add_event(ViduraiEvent(type="cli.context", source="test", project_path="/test", payload={"query": "test"}))
    episode3.add_event(ViduraiEvent(type="cli.context", source="test", project_path="/test", payload={"query": "test"}))
    episode3.file_paths.add("module.py")
    episode3.close()

    gist = policy.extract_gist(episode3)
    assert "Refactor" in gist, "Should mention episode type"
    assert "module.py" in gist, "Should mention file"
    assert "2 events" in gist, "Should mention event count"
    print(f"✅ Generated from metadata: '{gist}'")
    print()

    print("✅ PASSED: Gist extraction works\n")


def test_metadata_extraction():
    """Test extract_metadata() for memory enrichment"""
    print("=" * 70)
    print("🧪 TEST 4: Metadata Extraction")
    print("=" * 70)
    print()

    from vidurai.core.auto_memory_policy import AutoMemoryPolicy
    from vidurai.core.episode_builder import Episode
    from vidurai.core.event_bus import ViduraiEvent

    policy = AutoMemoryPolicy()

    episode = Episode(project_path="/test")
    episode.episode_type = "bugfix"
    episode.start_time = datetime.now() - timedelta(minutes=10)
    episode.file_paths.add("auth.py")
    episode.metadata['queries'] = ["auth bug", "TypeError"]

    event1 = ViduraiEvent(type="memory.created", source="test", project_path="/test", payload={"gist": "e1"})
    event2 = ViduraiEvent(type="memory.created", source="test", project_path="/test", payload={"gist": "e2"})
    event3 = ViduraiEvent(type="memory.created", source="test", project_path="/test", payload={"gist": "e3"})
    episode.add_event(event1)
    episode.add_event(event2)
    episode.add_event(event3)
    episode.close()

    metadata = policy.extract_metadata(episode)

    # Verify metadata fields
    assert metadata['type'] == "bugfix", "Should include episode type"
    assert metadata['episode_id'] == episode.id, "Should include episode ID"
    assert metadata['episode_event_count'] == 3, "Should include event count"
    assert metadata['episode_duration_minutes'] == pytest.approx(10, rel=0.2), "Should include duration"
    assert metadata['auto_created'] == True, "Should mark as auto-created"
    assert metadata['file'] == "auth.py", "Should include primary file"
    assert metadata['queries'] == ["auth bug", "TypeError"], "Should include queries"

    print(f"✅ Extracted metadata: {metadata}")
    print()

    print("✅ PASSED: Metadata extraction works\n")


def test_episode_to_memory_conversion():
    """Test episode_to_memory_data() conversion"""
    print("=" * 70)
    print("🧪 TEST 5: Episode to Memory Conversion")
    print("=" * 70)
    print()

    from vidurai.core.auto_memory_policy import AutoMemoryPolicy
    from vidurai.core.episode_builder import Episode
    from vidurai.core.event_bus import ViduraiEvent
    from vidurai.core.data_structures_v3 import SalienceLevel

    policy = AutoMemoryPolicy()

    # Create a realistic episode
    episode = Episode(project_path="/test/project")
    episode.episode_type = "bugfix"
    episode.summary = "Fixed TypeError in login function"
    episode.metadata['max_salience'] = "HIGH"
    episode.start_time = datetime.now() - timedelta(minutes=5)

    event1 = ViduraiEvent(
        type="memory.created",
        source="test",
        project_path="/test/project",
        payload={"gist": "Found TypeError", "file_path": "auth.py"}
    )
    event2 = ViduraiEvent(
        type="cli.context",
        source="test",
        project_path="/test/project",
        payload={"query": "TypeError login"}
    )
    event3 = ViduraiEvent(
        type="memory.created",
        source="test",
        project_path="/test/project",
        payload={"gist": "Fixed TypeError in login function", "file_path": "auth.py"}
    )

    episode.add_event(event1)
    episode.add_event(event2)
    episode.add_event(event3)
    episode.close()

    # Convert to memory data
    memory_data = policy.episode_to_memory_data(episode)

    # Verify conversion
    assert memory_data['content'] == "Fixed TypeError in login function", "Should use episode summary"
    assert memory_data['salience'] == SalienceLevel.HIGH, "Should detect HIGH salience"
    assert memory_data['extract_gist'] == False, "Should not re-extract gist"
    assert 'metadata' in memory_data, "Should include metadata"
    assert memory_data['metadata']['type'] == "bugfix", "Metadata should include type"
    assert memory_data['metadata']['auto_created'] == True, "Should mark as auto-created"

    print(f"✅ Memory data: {memory_data['content'][:50]}...")
    print(f"✅ Salience: {memory_data['salience'].name}")
    print(f"✅ Metadata: {memory_data['metadata']}")
    print()

    print("✅ PASSED: Episode to memory conversion works\n")


def test_auto_memory_manager():
    """Test AutoMemoryManager integration"""
    print("=" * 70)
    print("🧪 TEST 6: AutoMemoryManager Integration")
    print("=" * 70)
    print()

    from vidurai.core.auto_memory_policy import AutoMemoryPolicy, AutoMemoryManager
    from vidurai.core.episode_builder import Episode, EpisodeBuilder
    from vidurai.core.event_bus import ViduraiEvent
    from vidurai.vismriti_memory import VismritiMemory

    # Create temp directory for memory storage
    temp_dir = tempfile.mkdtemp()
    try:
        # Setup components
        builder = EpisodeBuilder()
        memory = VismritiMemory(project_path=temp_dir)
        policy = AutoMemoryPolicy(min_event_count=2, min_duration_minutes=0.5)
        manager = AutoMemoryManager(
            episode_builder=builder,
            memory=memory,
            policy=policy
        )

        # Test 6.1: Process valid episode
        print("Test 6.1: Process valid episode creates memory")
        episode = Episode(project_path=temp_dir)
        episode.episode_type = "bugfix"
        episode.summary = "Fixed authentication bug"
        episode.metadata['max_salience'] = "HIGH"
        episode.start_time = datetime.now() - timedelta(minutes=5)

        event1 = ViduraiEvent(type="memory.created", source="test", project_path=temp_dir, payload={"gist": "e1", "file_path": "auth.py"})
        event2 = ViduraiEvent(type="memory.created", source="test", project_path=temp_dir, payload={"gist": "e2", "file_path": "auth.py"})
        episode.add_event(event1)
        episode.add_event(event2)
        episode.close()

        created_memory = manager.process_episode(episode)
        assert created_memory is not None, "Should create memory from valid episode"
        assert manager.memories_created == 1, "Should track created memories"
        print(f"✅ Created memory: {created_memory.gist[:50]}...")
        print()

        # Test 6.2: Skip invalid episode
        print("Test 6.2: Skip episode that doesn't meet criteria")
        episode2 = Episode(project_path=temp_dir)
        episode2.episode_type = "bugfix"
        episode2.add_event(ViduraiEvent(type="memory.created", source="test", project_path=temp_dir, payload={"gist": "single"}))
        episode2.close()

        result = manager.process_episode(episode2)
        assert result is None, "Should skip episode with too few events"
        assert manager.episodes_skipped == 1, "Should track skipped episodes"
        print(f"✅ Skipped invalid episode")
        print()

        # Test 6.3: Statistics
        print("Test 6.3: Manager statistics")
        stats = manager.get_statistics()
        assert stats['memories_created'] == 1, "Should track created count"
        assert stats['episodes_skipped'] == 1, "Should track skipped count"
        assert 'policy' in stats, "Should include policy stats"
        print(f"✅ Statistics: {stats}")
        print()

        print("✅ PASSED: AutoMemoryManager integration works\n")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_end_to_end_auto_memory():
    """Test full flow: events → episodes → memories"""
    print("=" * 70)
    print("🧪 TEST 7: End-to-End Auto-Memory Creation")
    print("=" * 70)
    print()

    from vidurai.core.auto_memory_policy import AutoMemoryPolicy, AutoMemoryManager
    from vidurai.core.episode_builder import EpisodeBuilder
    from vidurai.core.event_bus import ViduraiEvent
    from vidurai.vismriti_memory import VismritiMemory

    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    try:
        # Setup pipeline
        builder = EpisodeBuilder(inactivity_timeout_minutes=1)
        memory = VismritiMemory(project_path=temp_dir)
        policy = AutoMemoryPolicy(min_event_count=2, min_duration_minutes=0.5)
        manager = AutoMemoryManager(builder, memory, policy)

        print("Simulating development session...")

        # Simulate bugfix session
        events = [
            ViduraiEvent(
                type="memory.created",
                source="vismriti",
                project_path=temp_dir,
                payload={"gist": "Found TypeError in auth.py", "memory_type": "bugfix", "file_path": "auth.py"}
            ),
            ViduraiEvent(
                type="cli.context",
                source="cli",
                project_path=temp_dir,
                payload={"query": "TypeError auth", "memory_count": 5}
            ),
            ViduraiEvent(
                type="memory.created",
                source="vismriti",
                project_path=temp_dir,
                payload={"gist": "Fixed TypeError in auth.py", "memory_type": "bugfix", "file_path": "auth.py", "salience": "HIGH"}
            ),
        ]

        # Feed events to builder
        for event in events:
            builder.handle_event(event)

        episode = builder.get_current_episode(temp_dir)
        assert episode is not None, "Should have created episode"
        assert episode.event_count == 3, "Should have all events"
        print(f"✅ Created episode: {episode}")

        # Set earlier start time to meet minimum duration
        episode.start_time = datetime.now() - timedelta(minutes=2)

        # Manually close episode for testing
        builder._close_episode(episode)

        # Process closed episodes
        created_count = manager.process_closed_episodes()
        assert created_count == 1, "Should create 1 memory"
        print(f"✅ Auto-created {created_count} memory from episode")

        # Verify memory was created by checking manager statistics
        assert manager.memories_created == 1, "Should have created 1 memory"

        # Query the memory to verify it exists
        context = memory.get_context_for_ai(query="TypeError")
        assert "TypeError" in context or "auth" in context.lower(), "Memory should be retrievable"

        print(f"✅ Found auto-created memory in context")
        print(f"✅ Manager statistics: {manager.get_statistics()}")
        print()

        print("✅ PASSED: End-to-end auto-memory creation works\n")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_policy_statistics():
    """Test AutoMemoryPolicy statistics"""
    print("=" * 70)
    print("🧪 TEST 8: Policy Statistics")
    print("=" * 70)
    print()

    from vidurai.core.auto_memory_policy import AutoMemoryPolicy

    policy = AutoMemoryPolicy(
        min_event_count=3,
        min_duration_minutes=2.0,
        auto_create_exploration=True,
        auto_create_unknown=False
    )

    stats = policy.get_statistics()

    assert stats['min_event_count'] == 3, "Should report min event count"
    assert stats['min_duration_minutes'] == 2.0, "Should report min duration"
    assert stats['auto_create_exploration'] == True, "Should report exploration flag"
    assert stats['auto_create_unknown'] == False, "Should report unknown flag"

    print(f"✅ Policy statistics: {stats}")
    print()

    print("✅ PASSED: Policy statistics work\n")


if __name__ == "__main__":
    # pytest is needed for approx() in test 4
    try:
        import pytest
    except ImportError:
        print("Installing pytest for test utilities...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pytest"])
        import pytest

    try:
        print()
        print("🚀 PHASE 6.4 TEST SUITE: Auto-Memory Policy")
        print()

        test_quality_filters()
        test_salience_detection()
        test_gist_extraction()
        test_metadata_extraction()
        test_episode_to_memory_conversion()
        test_auto_memory_manager()
        test_end_to_end_auto_memory()
        test_policy_statistics()

        print()
        print("=" * 70)
        print("✅ ALL PHASE 6.4 TESTS PASSED")
        print("=" * 70)
        print()
        print("Summary:")
        print("  ✅ Quality filters (event count, duration, type)")
        print("  ✅ Salience detection (metadata + heuristics)")
        print("  ✅ Gist extraction (summary, events, metadata)")
        print("  ✅ Metadata extraction for memory enrichment")
        print("  ✅ Episode to memory data conversion")
        print("  ✅ AutoMemoryManager integration")
        print("  ✅ End-to-end: events → episodes → memories")
        print("  ✅ Policy statistics")
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
