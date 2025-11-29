#!/usr/bin/env python3
"""
Test suite for Phase 6.3: Episode Builder
Tests episode detection, correlation, and pattern recognition
"""

import sys
import time
from pathlib import Path
from datetime import datetime, timedelta

# Add paths
sys.path.insert(0, str(Path(__file__).parent))


def test_basic_episode_creation():
    """Test basic episode creation and event addition"""
    print("=" * 70)
    print("🧪 TEST 1: Basic Episode Creation")
    print("=" * 70)
    print()

    from vidurai.core.episode_builder import Episode, EpisodeBuilder
    from vidurai.core.event_bus import ViduraiEvent

    builder = EpisodeBuilder(inactivity_timeout_minutes=5)

    # Create test events
    event1 = ViduraiEvent(
        type="memory.created",
        source="vismriti",
        project_path="/test/project",
        payload={"gist": "Fixed bug in auth.py", "memory_type": "bugfix", "file_path": "auth.py"}
    )

    event2 = ViduraiEvent(
        type="cli.context",
        source="cli",
        project_path="/test/project",
        payload={"query": "auth bug", "memory_count": 3}
    )

    # Handle events
    builder.handle_event(event1)
    builder.handle_event(event2)

    # Verify episode created
    episode = builder.get_current_episode("/test/project")
    assert episode is not None, "Should have created an episode"
    assert episode.event_count == 2, "Episode should have 2 events"
    assert episode.project_path == "/test/project"
    assert not episode.is_closed, "Episode should still be open"
    print(f"✅ Created episode: {episode}")
    print(f"✅ Episode has {episode.event_count} events")
    print()

    print("✅ PASSED: Basic episode creation works\n")


def test_episode_type_detection():
    """Test automatic episode type detection"""
    print("=" * 70)
    print("🧪 TEST 2: Episode Type Detection")
    print("=" * 70)
    print()

    from vidurai.core.episode_builder import EpisodeBuilder
    from vidurai.core.event_bus import ViduraiEvent

    builder = EpisodeBuilder()

    # Test 2.1: Bugfix detection
    print("Test 2.1: Bugfix pattern")
    event = ViduraiEvent(
        type="memory.created",
        source="vismriti",
        project_path="/test/bugfix",
        payload={"gist": "Fixed TypeError in login", "memory_type": "bugfix", "file_path": "login.py"}
    )
    builder.handle_event(event)

    episode = builder.get_current_episode("/test/bugfix")
    assert episode.episode_type == "bugfix", "Should detect bugfix episode"
    assert "Fixed TypeError" in episode.summary
    print(f"✅ Detected bugfix: {episode.summary}")
    print()

    # Test 2.2: Feature detection
    print("Test 2.2: Feature pattern")
    event = ViduraiEvent(
        type="memory.created",
        source="vismriti",
        project_path="/test/feature",
        payload={"gist": "Implemented OAuth2 authentication", "memory_type": "feature", "file_path": "oauth.py"}
    )
    builder.handle_event(event)

    episode = builder.get_current_episode("/test/feature")
    assert episode.episode_type == "feature", "Should detect feature episode"
    assert "OAuth2" in episode.summary
    print(f"✅ Detected feature: {episode.summary}")
    print()

    # Test 2.3: Refactor detection
    print("Test 2.3: Refactor pattern")
    event = ViduraiEvent(
        type="memory.created",
        source="vismriti",
        project_path="/test/refactor",
        payload={"gist": "Refactored database layer", "memory_type": "refactor", "file_path": "db.py"}
    )
    builder.handle_event(event)

    episode = builder.get_current_episode("/test/refactor")
    assert episode.episode_type == "refactor", "Should detect refactor episode"
    print(f"✅ Detected refactor: {episode.summary}")
    print()

    # Test 2.4: Exploration detection
    print("Test 2.4: Exploration pattern")
    for i in range(3):
        event = ViduraiEvent(
            type="cli.context",
            source="cli",
            project_path="/test/explore",
            payload={"query": f"query {i}", "memory_count": 2}
        )
        builder.handle_event(event)

    episode = builder.get_current_episode("/test/explore")
    assert episode.episode_type == "exploration", "Should detect exploration episode"
    print(f"✅ Detected exploration: {episode.summary}")
    print()

    print("✅ PASSED: Episode type detection works\n")


def test_temporal_correlation():
    """Test time-based episode grouping"""
    print("=" * 70)
    print("🧪 TEST 3: Temporal Correlation")
    print("=" * 70)
    print()

    from vidurai.core.episode_builder import EpisodeBuilder
    from vidurai.core.event_bus import ViduraiEvent

    # Short timeout for testing
    builder = EpisodeBuilder(inactivity_timeout_minutes=1)

    # Create events within timeout
    print("Test 3.1: Events within timeout grouped together")
    event1 = ViduraiEvent(
        type="memory.created",
        source="vismriti",
        project_path="/test/temporal",
        payload={"gist": "Started work", "memory_type": "feature"}
    )
    builder.handle_event(event1)

    event2 = ViduraiEvent(
        type="memory.created",
        source="vismriti",
        project_path="/test/temporal",
        payload={"gist": "Continued work", "memory_type": "feature"}
    )
    builder.handle_event(event2)

    episode = builder.get_current_episode("/test/temporal")
    assert episode.event_count == 2, "Events should be in same episode"
    print(f"✅ {episode.event_count} events grouped in same episode")
    print()

    # Wait for timeout (simulate with manual timestamp adjustment)
    print("Test 3.2: Events after timeout create new episode")
    # Manually adjust last event timestamp to simulate timeout
    episode.events[-1].timestamp = datetime.now() - timedelta(minutes=2)

    event3 = ViduraiEvent(
        type="memory.created",
        source="vismriti",
        project_path="/test/temporal",
        payload={"gist": "New work after break", "memory_type": "feature"}
    )
    builder.handle_event(event3)

    # Should have closed old episode and created new one
    stats = builder.get_statistics()
    assert stats['closed_episodes'] >= 1, "Should have closed previous episode"
    assert stats['active_episodes'] >= 1, "Should have new active episode"
    print(f"✅ Previous episode closed, new episode created")
    print(f"✅ Closed episodes: {stats['closed_episodes']}")
    print()

    print("✅ PASSED: Temporal correlation works\n")


def test_semantic_correlation():
    """Test project/file-based grouping"""
    print("=" * 70)
    print("🧪 TEST 4: Semantic Correlation")
    print("=" * 70)
    print()

    from vidurai.core.episode_builder import EpisodeBuilder
    from vidurai.core.event_bus import ViduraiEvent

    builder = EpisodeBuilder()

    # Test 4.1: Same project groups together
    print("Test 4.1: Same project correlation")
    for i in range(3):
        event = ViduraiEvent(
            type="memory.created",
            source="vismriti",
            project_path="/test/project1",
            payload={"gist": f"Work {i}", "file_path": f"file{i}.py"}
        )
        builder.handle_event(event)

    episode1 = builder.get_current_episode("/test/project1")
    assert episode1.event_count == 3, "Same project should group together"
    assert len(episode1.file_paths) == 3, "Should track all 3 files"
    print(f"✅ {episode1.event_count} events in same project episode")
    print(f"✅ Tracked {len(episode1.file_paths)} files: {episode1.file_paths}")
    print()

    # Test 4.2: Different projects create separate episodes
    print("Test 4.2: Different projects create separate episodes")
    event = ViduraiEvent(
        type="memory.created",
        source="vismriti",
        project_path="/test/project2",
        payload={"gist": "Different project work"}
    )
    builder.handle_event(event)

    episode2 = builder.get_current_episode("/test/project2")
    assert episode2 is not episode1, "Different project should create new episode"
    assert episode2.event_count == 1, "New episode should have 1 event"
    print(f"✅ Separate episode created for different project")
    print()

    print("✅ PASSED: Semantic correlation works\n")


def test_episode_closure():
    """Test episode closing mechanisms"""
    print("=" * 70)
    print("🧪 TEST 5: Episode Closure")
    print("=" * 70)
    print()

    from vidurai.core.episode_builder import EpisodeBuilder
    from vidurai.core.event_bus import ViduraiEvent

    builder = EpisodeBuilder(
        inactivity_timeout_minutes=1,
        max_episode_duration_minutes=5
    )

    # Create episode
    event = ViduraiEvent(
        type="memory.created",
        source="vismriti",
        project_path="/test/closure",
        payload={"gist": "Some work"}
    )
    builder.handle_event(event)

    episode = builder.get_current_episode("/test/closure")
    assert episode is not None
    assert not episode.is_closed
    print("✅ Episode created and open")
    print()

    # Test manual closure
    print("Test 5.1: Manual closure")
    builder._close_episode(episode)
    assert episode.is_closed
    assert episode.end_time is not None
    print(f"✅ Episode closed manually")
    print(f"✅ Duration: {episode.duration}")
    print()

    # Test automatic closure by inactivity
    print("Test 5.2: Automatic closure by inactivity")
    event = ViduraiEvent(
        type="memory.created",
        source="vismriti",
        project_path="/test/closure2",
        payload={"gist": "New work"}
    )
    builder.handle_event(event)

    episode2 = builder.get_current_episode("/test/closure2")
    # Simulate inactivity
    episode2.events[-1].timestamp = datetime.now() - timedelta(minutes=2)

    builder._close_stale_episodes()

    stats = builder.get_statistics()
    assert stats['closed_episodes'] >= 2, "Episode should be closed due to inactivity"
    print(f"✅ Episode auto-closed due to inactivity")
    print()

    print("✅ PASSED: Episode closure works\n")


def test_episode_metadata():
    """Test episode metadata tracking"""
    print("=" * 70)
    print("🧪 TEST 6: Episode Metadata")
    print("=" * 70)
    print()

    from vidurai.core.episode_builder import EpisodeBuilder
    from vidurai.core.event_bus import ViduraiEvent

    builder = EpisodeBuilder()

    # Create events with different metadata
    event1 = ViduraiEvent(
        type="cli.context",
        source="cli",
        project_path="/test/metadata",
        payload={"query": "authentication"}
    )
    builder.handle_event(event1)

    event2 = ViduraiEvent(
        type="memory.created",
        source="vismriti",
        project_path="/test/metadata",
        payload={"gist": "Fixed auth bug", "salience": "HIGH"}
    )
    builder.handle_event(event2)

    event3 = ViduraiEvent(
        type="memory.created",
        source="vismriti",
        project_path="/test/metadata",
        payload={"gist": "Critical fix", "salience": "CRITICAL"}
    )
    builder.handle_event(event3)

    episode = builder.get_current_episode("/test/metadata")

    # Verify metadata
    assert 'queries' in episode.metadata, "Should track queries"
    assert 'authentication' in episode.metadata['queries']
    print(f"✅ Tracked queries: {episode.metadata['queries']}")

    assert 'max_salience' in episode.metadata, "Should track max salience"
    assert episode.metadata['max_salience'] == "CRITICAL", "Should update to highest salience"
    print(f"✅ Max salience: {episode.metadata['max_salience']}")
    print()

    print("✅ PASSED: Episode metadata tracking works\n")


def test_episode_statistics():
    """Test episode statistics"""
    print("=" * 70)
    print("🧪 TEST 7: Episode Statistics")
    print("=" * 70)
    print()

    from vidurai.core.episode_builder import EpisodeBuilder
    from vidurai.core.event_bus import ViduraiEvent

    builder = EpisodeBuilder()

    # Create multiple episodes of different types
    projects = [
        ("/test/bugfix1", "bugfix", "Fixed bug 1"),
        ("/test/bugfix2", "bugfix", "Fixed bug 2"),
        ("/test/feature1", "feature", "Added feature 1"),
        ("/test/refactor1", "refactor", "Refactored code"),
    ]

    for project, ep_type, gist in projects:
        event = ViduraiEvent(
            type="memory.created",
            source="vismriti",
            project_path=project,
            payload={"gist": gist, "memory_type": ep_type}
        )
        builder.handle_event(event)

    # Close all episodes
    for episode in list(builder.active_episodes.values()):
        builder._close_episode(episode)

    # Get statistics
    stats = builder.get_statistics()

    print(f"Statistics: {stats}")
    assert stats['closed_episodes'] == 4, "Should have 4 closed episodes"
    assert stats['episodes_by_type']['bugfix'] == 2, "Should have 2 bugfix episodes"
    assert stats['episodes_by_type']['feature'] == 1, "Should have 1 feature episode"
    assert stats['episodes_by_type']['refactor'] == 1, "Should have 1 refactor episode"
    print(f"✅ Closed episodes: {stats['closed_episodes']}")
    print(f"✅ By type: {stats['episodes_by_type']}")
    print()

    print("✅ PASSED: Episode statistics work\n")


def test_episode_serialization():
    """Test episode to_dict() serialization"""
    print("=" * 70)
    print("🧪 TEST 8: Episode Serialization")
    print("=" * 70)
    print()

    from vidurai.core.episode_builder import Episode
    from vidurai.core.event_bus import ViduraiEvent

    episode = Episode(project_path="/test/serialize")
    episode.episode_type = "bugfix"
    episode.summary = "Fixed critical bug"

    event1 = ViduraiEvent(
        type="memory.created",
        source="vismriti",
        project_path="/test/serialize",
        payload={"gist": "Bug fix", "file_path": "auth.py"}
    )
    episode.add_event(event1)

    episode.close()

    # Serialize
    data = episode.to_dict()

    print(f"Serialized episode: {data}")
    assert data['id'] == episode.id
    assert data['episode_type'] == "bugfix"
    assert data['summary'] == "Fixed critical bug"
    assert data['event_count'] == 1
    assert data['is_closed'] == True
    assert 'auth.py' in data['file_paths']
    print(f"✅ Serialized correctly")
    print()

    print("✅ PASSED: Episode serialization works\n")


if __name__ == "__main__":
    try:
        print()
        print("🚀 PHASE 6.3 TEST SUITE: Episode Builder")
        print()

        test_basic_episode_creation()
        test_episode_type_detection()
        test_temporal_correlation()
        test_semantic_correlation()
        test_episode_closure()
        test_episode_metadata()
        test_episode_statistics()
        test_episode_serialization()

        print()
        print("=" * 70)
        print("✅ ALL PHASE 6.3 TESTS PASSED")
        print("=" * 70)
        print()
        print("Summary:")
        print("  ✅ Basic episode creation and event addition")
        print("  ✅ Episode type detection (bugfix, feature, refactor, exploration)")
        print("  ✅ Temporal correlation (time-based grouping)")
        print("  ✅ Semantic correlation (project/file-based grouping)")
        print("  ✅ Episode closure (manual and automatic)")
        print("  ✅ Episode metadata tracking")
        print("  ✅ Episode statistics")
        print("  ✅ Episode serialization")
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
