"""
Auto-Memory Policy - Automatically Convert Episodes to Memories
Phase 6.4: Passive & Automatic Memory Capture

Philosophy: विस्मृति भी विद्या है - Memories create themselves from episodes

Design:
- Converts closed episodes into VismritiMemory memories
- Extracts gist from episode summary and events
- Detects salience from episode metadata
- Filters episodes by quality/importance
- No explicit .remember() calls needed

Conversion Rules:
- Bugfix episodes → CRITICAL/HIGH salience
- Feature episodes → HIGH/MEDIUM salience
- Refactor episodes → MEDIUM salience
- Exploration episodes → LOW salience (or skip)

Quality Filters:
- Minimum event count (skip trivial episodes)
- Minimum duration (skip very short episodes)
- Episode type (skip 'unknown' type)
"""

from typing import Optional, Dict, Any, List
from datetime import timedelta
from loguru import logger

try:
    from vidurai.core.episode_builder import Episode
    from vidurai.core.data_structures_v3 import SalienceLevel
    EPISODE_AVAILABLE = True
except ImportError:
    EPISODE_AVAILABLE = False
    Episode = None
    SalienceLevel = None


class AutoMemoryPolicy:
    """
    Automatically convert episodes into memories

    This policy determines which episodes should become memories and
    extracts the appropriate metadata (gist, salience, etc.).

    Conversion Rules:
    1. Quality Filters:
       - Min event count (default: 2)
       - Min duration (default: 1 minute)
       - Valid episode type (not 'unknown')

    2. Salience Detection:
       - Uses episode.metadata['max_salience'] if available
       - Falls back to episode type heuristics
       - Bugfix → CRITICAL/HIGH
       - Feature → HIGH/MEDIUM
       - Refactor → MEDIUM
       - Exploration → LOW

    3. Gist Extraction:
       - Uses episode.summary if available
       - Falls back to first memory event gist
       - Includes episode context (type, duration, event count)

    Usage:
        policy = AutoMemoryPolicy(
            min_event_count=2,
            min_duration_minutes=1,
            auto_create_exploration=False
        )

        # Check if episode should become memory
        if policy.should_create_memory(episode):
            memory_data = policy.episode_to_memory_data(episode)
            memory.remember(**memory_data)
    """

    def __init__(
        self,
        min_event_count: int = 2,
        min_duration_minutes: float = 1.0,
        auto_create_exploration: bool = False,
        auto_create_unknown: bool = False
    ):
        """
        Initialize AutoMemoryPolicy

        Args:
            min_event_count: Minimum events required to create memory
            min_duration_minutes: Minimum episode duration (minutes)
            auto_create_exploration: Create memories from exploration episodes
            auto_create_unknown: Create memories from unknown type episodes
        """
        self.min_event_count = min_event_count
        self.min_duration = timedelta(minutes=min_duration_minutes)
        self.auto_create_exploration = auto_create_exploration
        self.auto_create_unknown = auto_create_unknown

        logger.info(
            f"AutoMemoryPolicy initialized: "
            f"min_events={min_event_count}, "
            f"min_duration={min_duration_minutes}m, "
            f"exploration={auto_create_exploration}, "
            f"unknown={auto_create_unknown}"
        )

    def should_create_memory(self, episode: Episode) -> bool:
        """
        Determine if episode should be converted to memory

        Args:
            episode: The episode to evaluate

        Returns:
            True if episode should become a memory
        """
        # Must be closed
        if not episode.is_closed:
            logger.debug(f"Episode {episode.id[:8]} not closed, skipping")
            return False

        # Check minimum event count
        if episode.event_count < self.min_event_count:
            logger.debug(
                f"Episode {episode.id[:8]} has only {episode.event_count} events "
                f"(min: {self.min_event_count}), skipping"
            )
            return False

        # Check minimum duration
        if episode.duration < self.min_duration:
            logger.debug(
                f"Episode {episode.id[:8]} duration {episode.duration} too short "
                f"(min: {self.min_duration}), skipping"
            )
            return False

        # Check episode type
        if episode.episode_type == "unknown" and not self.auto_create_unknown:
            logger.debug(f"Episode {episode.id[:8]} has unknown type, skipping")
            return False

        if episode.episode_type == "exploration" and not self.auto_create_exploration:
            logger.debug(f"Episode {episode.id[:8]} is exploration, skipping")
            return False

        logger.debug(f"Episode {episode.id[:8]} qualifies for auto-memory")
        return True

    def detect_salience(self, episode: Episode) -> SalienceLevel:
        """
        Detect appropriate salience level for episode

        Uses episode metadata and type to determine salience.

        Args:
            episode: The episode to evaluate

        Returns:
            Detected salience level
        """
        # First priority: Use max_salience from episode metadata
        if 'max_salience' in episode.metadata:
            salience_str = episode.metadata['max_salience']
            try:
                return SalienceLevel[salience_str]
            except (KeyError, ValueError):
                pass

        # Second priority: Heuristics based on episode type
        if episode.episode_type == "bugfix":
            # Bugfixes are generally important
            return SalienceLevel.HIGH

        elif episode.episode_type == "feature":
            # Features are moderately important
            return SalienceLevel.MEDIUM

        elif episode.episode_type == "refactor":
            # Refactors are moderately important
            return SalienceLevel.MEDIUM

        elif episode.episode_type == "exploration":
            # Exploration is low importance
            return SalienceLevel.LOW

        else:
            # Unknown type defaults to low
            return SalienceLevel.LOW

    def extract_gist(self, episode: Episode) -> str:
        """
        Extract gist/summary from episode

        Args:
            episode: The episode to extract from

        Returns:
            Human-readable gist
        """
        # First priority: Use episode summary if available
        if episode.summary:
            return episode.summary

        # Second priority: Extract from first memory.created event
        for event in episode.events:
            if event.type == "memory.created" and 'gist' in event.payload:
                return event.payload['gist']

        # Fallback: Generate from episode metadata
        event_count = episode.event_count
        duration_mins = int(episode.duration.total_seconds() / 60)
        file_count = len(episode.file_paths)

        parts = []
        parts.append(f"{episode.episode_type.capitalize()} session")

        if file_count > 0:
            if file_count == 1:
                parts.append(f"in {list(episode.file_paths)[0]}")
            else:
                parts.append(f"across {file_count} files")

        parts.append(f"({event_count} events, {duration_mins}m)")

        return " ".join(parts)

    def extract_metadata(self, episode: Episode) -> Dict[str, Any]:
        """
        Extract metadata from episode for memory

        Args:
            episode: The episode to extract from

        Returns:
            Metadata dictionary
        """
        metadata = {
            'type': episode.episode_type,
            'episode_id': episode.id,
            'episode_duration_minutes': episode.duration.total_seconds() / 60,
            'episode_event_count': episode.event_count,
            'auto_created': True
        }

        # Add primary file if available
        if episode.file_paths:
            metadata['file'] = list(episode.file_paths)[0]

        # Add queries if tracked
        if 'queries' in episode.metadata:
            metadata['queries'] = episode.metadata['queries']

        return metadata

    def episode_to_memory_data(self, episode: Episode) -> Dict[str, Any]:
        """
        Convert episode to memory creation data

        Args:
            episode: The episode to convert

        Returns:
            Dictionary suitable for VismritiMemory.remember()
        """
        gist = self.extract_gist(episode)
        salience = self.detect_salience(episode)
        metadata = self.extract_metadata(episode)

        return {
            'content': gist,
            'metadata': metadata,
            'salience': salience,
            'extract_gist': False  # We already have the gist
        }

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get policy statistics

        Returns:
            Dictionary with statistics
        """
        return {
            'min_event_count': self.min_event_count,
            'min_duration_minutes': self.min_duration.total_seconds() / 60,
            'auto_create_exploration': self.auto_create_exploration,
            'auto_create_unknown': self.auto_create_unknown
        }


class AutoMemoryManager:
    """
    Manages automatic memory creation from episodes

    This manager subscribes to episode closure events and automatically
    creates memories based on the configured policy.

    Usage:
        from vidurai.core.episode_builder import EpisodeBuilder
        from vidurai.vismriti_memory import VismritiMemory

        # Create components
        builder = EpisodeBuilder()
        memory = VismritiMemory()
        policy = AutoMemoryPolicy()

        # Create manager
        manager = AutoMemoryManager(
            episode_builder=builder,
            memory=memory,
            policy=policy
        )

        # Start auto-memory creation
        manager.start()

        # Now episodes will automatically become memories!
    """

    def __init__(
        self,
        episode_builder,  # EpisodeBuilder instance
        memory,  # VismritiMemory instance
        policy: Optional[AutoMemoryPolicy] = None
    ):
        """
        Initialize AutoMemoryManager

        Args:
            episode_builder: EpisodeBuilder instance
            memory: VismritiMemory instance
            policy: AutoMemoryPolicy instance (creates default if None)
        """
        self.episode_builder = episode_builder
        self.memory = memory
        self.policy = policy or AutoMemoryPolicy()

        # Statistics
        self.memories_created = 0
        self.episodes_skipped = 0

        logger.info("AutoMemoryManager initialized")

    def process_episode(self, episode: Episode) -> Optional[Any]:
        """
        Process a closed episode and create memory if appropriate

        Args:
            episode: The closed episode to process

        Returns:
            Created memory object or None
        """
        # Check if episode should become memory
        if not self.policy.should_create_memory(episode):
            self.episodes_skipped += 1
            return None

        try:
            # Convert episode to memory data
            memory_data = self.policy.episode_to_memory_data(episode)

            # Create memory
            created_memory = self.memory.remember(**memory_data)

            self.memories_created += 1
            logger.info(
                f"Auto-created memory from episode: "
                f"{episode.episode_type} - {memory_data['content'][:50]}..."
            )

            return created_memory

        except Exception as e:
            logger.error(f"Failed to create memory from episode {episode.id[:8]}: {e}")
            self.episodes_skipped += 1
            return None

    def process_closed_episodes(self) -> int:
        """
        Process all closed episodes and create memories

        Returns:
            Number of memories created
        """
        created_count = 0

        # Get closed episodes
        closed_episodes = self.episode_builder.get_closed_episodes()

        for episode in closed_episodes:
            if self.process_episode(episode) is not None:
                created_count += 1

        return created_count

    def start_periodic_processing(self, interval_minutes: int = 5):
        """
        Start periodic processing of closed episodes

        Note: This would require a background thread or async task.
        For now, this is a placeholder for future implementation.

        Args:
            interval_minutes: How often to process episodes
        """
        logger.warning(
            "Periodic processing not yet implemented. "
            "Call process_closed_episodes() manually or integrate with event loop."
        )

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get manager statistics

        Returns:
            Dictionary with statistics
        """
        return {
            'memories_created': self.memories_created,
            'episodes_skipped': self.episodes_skipped,
            'policy': self.policy.get_statistics()
        }
