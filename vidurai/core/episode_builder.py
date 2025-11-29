"""
Episode Builder - Aggregate Events into Coherent Episodes
Phase 6.3: Passive & Automatic Memory Capture

Philosophy: विस्मृति भी विद्या है - Episodes emerge from event streams

Design:
- Temporal correlation (events within time window)
- Semantic correlation (same project/file/topic)
- Episode detection patterns (bugfix, feature, refactor)
- Automatic episode closure (inactivity timeout)

Example Episode:
    Events:
    1. [10:30] memory.created: "TypeError in auth.py"
    2. [10:32] cli.context: query="TypeError auth"
    3. [10:35] memory.created: "Fixed TypeError in auth.py"

    Episode:
    - Type: "bugfix"
    - Summary: "Fixed TypeError in auth.py"
    - Duration: 5 minutes
    - Events: 3
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict
from loguru import logger

try:
    from vidurai.core.event_bus import ViduraiEvent
    EVENT_BUS_AVAILABLE = True
except ImportError:
    EVENT_BUS_AVAILABLE = False
    ViduraiEvent = None


@dataclass
class Episode:
    """
    Represents a coherent development episode

    An episode is a sequence of related events that form a logical unit of work,
    such as debugging a bug, implementing a feature, or refactoring code.

    Attributes:
        id: Unique episode identifier
        episode_type: Type of episode (bugfix, feature, refactor, exploration, etc.)
        start_time: When the episode started
        end_time: When the episode ended (None if ongoing)
        events: List of events in this episode
        project_path: Primary project path
        file_paths: Set of files involved
        summary: Human-readable episode summary
        metadata: Additional episode-specific data
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    episode_type: str = "unknown"  # bugfix, feature, refactor, exploration
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    events: List[ViduraiEvent] = field(default_factory=list)
    project_path: Optional[str] = None
    file_paths: set = field(default_factory=set)

    summary: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> timedelta:
        """Get episode duration"""
        end = self.end_time or datetime.now()
        return end - self.start_time

    @property
    def event_count(self) -> int:
        """Get number of events in episode"""
        return len(self.events)

    @property
    def is_closed(self) -> bool:
        """Check if episode is closed"""
        return self.end_time is not None

    def add_event(self, event: ViduraiEvent) -> None:
        """Add an event to this episode"""
        self.events.append(event)

        # Update project path (use first event's project)
        if not self.project_path and event.project_path:
            self.project_path = event.project_path

        # Track file paths
        if event.payload.get('file_path'):
            self.file_paths.add(event.payload['file_path'])

    def close(self, end_time: Optional[datetime] = None) -> None:
        """Close the episode"""
        self.end_time = end_time or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'episode_type': self.episode_type,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration.total_seconds(),
            'event_count': self.event_count,
            'project_path': self.project_path,
            'file_paths': list(self.file_paths),
            'summary': self.summary,
            'metadata': self.metadata,
            'is_closed': self.is_closed
        }

    def __str__(self) -> str:
        """Human-readable representation"""
        duration_str = f"{int(self.duration.total_seconds() / 60)}m"
        status = "closed" if self.is_closed else "ongoing"
        return f"[{self.episode_type}] {self.summary or 'Untitled'} ({self.event_count} events, {duration_str}, {status})"


class EpisodeBuilder:
    """
    Build episodes from event streams

    Uses temporal and semantic correlation to group related events into episodes.
    Automatically detects episode types and generates summaries.

    Episode Detection Patterns:
    - Bugfix: error event → context query → fix memory
    - Feature: multiple memory.created with same file/topic
    - Exploration: multiple context queries without memory creation
    - Refactor: multiple file edits in same project

    Correlation Strategy:
    - Temporal: Events within configurable time window (default: 30 minutes)
    - Semantic: Same project, file, or related topic

    Usage:
        builder = EpisodeBuilder(inactivity_timeout_minutes=30)

        # Subscribe to EventBus
        EventBus.subscribe(builder.handle_event)

        # Get closed episodes
        episodes = builder.get_closed_episodes()

        # Get current episode
        current = builder.get_current_episode()
    """

    def __init__(
        self,
        inactivity_timeout_minutes: int = 30,
        max_episode_duration_minutes: int = 120
    ):
        """
        Initialize EpisodeBuilder

        Args:
            inactivity_timeout_minutes: Close episode after this many minutes of inactivity
            max_episode_duration_minutes: Force close episode after this duration
        """
        self.inactivity_timeout = timedelta(minutes=inactivity_timeout_minutes)
        self.max_episode_duration = timedelta(minutes=max_episode_duration_minutes)

        # Current ongoing episodes (by project_path)
        self.active_episodes: Dict[str, Episode] = {}

        # Closed episodes
        self.closed_episodes: List[Episode] = []

        logger.info(
            f"EpisodeBuilder initialized: "
            f"inactivity_timeout={inactivity_timeout_minutes}m, "
            f"max_duration={max_episode_duration_minutes}m"
        )

    def handle_event(self, event: ViduraiEvent) -> None:
        """
        Handle incoming event from EventBus

        This is the main entry point for event processing.
        Called by EventBus when an event is published.

        Args:
            event: The event to process
        """
        # Close stale episodes first
        self._close_stale_episodes()

        # Get or create episode for this event's project
        project = event.project_path or "unknown"
        episode = self._get_or_create_episode(project, event)

        # Add event to episode
        episode.add_event(event)

        # Update episode metadata based on event
        self._update_episode_from_event(episode, event)

        logger.debug(
            f"Event added to episode: {event.type} → {episode.episode_type} "
            f"({episode.event_count} events)"
        )

    def _get_or_create_episode(self, project: str, event: ViduraiEvent) -> Episode:
        """
        Get existing episode or create new one

        Args:
            project: Project path
            event: The event triggering episode creation

        Returns:
            Active episode for this project
        """
        # Check if we have an active episode for this project
        if project in self.active_episodes:
            episode = self.active_episodes[project]

            # Check if episode should be closed due to inactivity
            time_since_last = datetime.now() - episode.events[-1].timestamp
            if time_since_last > self.inactivity_timeout:
                self._close_episode(episode)
                # Create new episode
                episode = Episode(project_path=project)
                self.active_episodes[project] = episode
                logger.info(f"Started new episode for {project} (previous closed due to inactivity)")

            # Check if episode exceeds max duration
            elif episode.duration > self.max_episode_duration:
                self._close_episode(episode)
                # Create new episode
                episode = Episode(project_path=project)
                self.active_episodes[project] = episode
                logger.info(f"Started new episode for {project} (previous closed due to max duration)")

            return episode

        # Create new episode
        episode = Episode(project_path=project)
        self.active_episodes[project] = episode
        logger.info(f"Started new episode for {project}")
        return episode

    def _update_episode_from_event(self, episode: Episode, event: ViduraiEvent) -> None:
        """
        Update episode metadata based on event type and content

        Detects episode patterns and updates type/summary accordingly.

        Args:
            episode: The episode to update
            event: The event to process
        """
        # Detect bugfix pattern
        if event.type == "memory.created":
            gist = event.payload.get('gist', '').lower()
            memory_type = event.payload.get('memory_type', '')

            if memory_type == 'bugfix' or any(word in gist for word in ['fix', 'bug', 'error', 'issue']):
                episode.episode_type = "bugfix"
                if not episode.summary:
                    episode.summary = event.payload.get('gist', '')[:100]

            elif memory_type == 'feature' or any(word in gist for word in ['add', 'implement', 'create']):
                if episode.episode_type == "unknown":
                    episode.episode_type = "feature"
                if not episode.summary:
                    episode.summary = event.payload.get('gist', '')[:100]

            elif memory_type == 'refactor' or any(word in gist for word in ['refactor', 'clean', 'improve']):
                if episode.episode_type == "unknown":
                    episode.episode_type = "refactor"
                if not episode.summary:
                    episode.summary = event.payload.get('gist', '')[:100]

        # Detect exploration pattern (multiple context queries)
        elif event.type in ["cli.context", "mcp.get_context", "memory.context_retrieved"]:
            if episode.episode_type == "unknown":
                # Count context queries
                context_queries = sum(1 for e in episode.events if 'context' in e.type)
                if context_queries >= 2:
                    episode.episode_type = "exploration"
                    episode.summary = f"Exploring {event.payload.get('query', 'project')}"

        # Track metadata
        if 'query' in event.payload:
            if 'queries' not in episode.metadata:
                episode.metadata['queries'] = []
            episode.metadata['queries'].append(event.payload['query'])

        if 'salience' in event.payload:
            if 'max_salience' not in episode.metadata:
                episode.metadata['max_salience'] = event.payload['salience']
            else:
                # Update if higher salience
                salience_order = {'CRITICAL': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1, 'NOISE': 0}
                current_level = salience_order.get(episode.metadata['max_salience'], 0)
                new_level = salience_order.get(event.payload['salience'], 0)
                if new_level > current_level:
                    episode.metadata['max_salience'] = event.payload['salience']

    def _close_episode(self, episode: Episode) -> None:
        """
        Close an episode and move it to closed list

        Args:
            episode: The episode to close
        """
        episode.close()
        self.closed_episodes.append(episode)

        # Remove from active episodes
        if episode.project_path and episode.project_path in self.active_episodes:
            del self.active_episodes[episode.project_path]

        logger.info(f"Closed episode: {episode}")

    def _close_stale_episodes(self) -> None:
        """
        Close episodes that have exceeded inactivity timeout
        """
        now = datetime.now()
        to_close = []

        for project, episode in self.active_episodes.items():
            if not episode.events:
                continue

            time_since_last = now - episode.events[-1].timestamp
            if time_since_last > self.inactivity_timeout:
                to_close.append(episode)
            elif episode.duration > self.max_episode_duration:
                to_close.append(episode)

        for episode in to_close:
            self._close_episode(episode)

    def get_current_episode(self, project_path: Optional[str] = None) -> Optional[Episode]:
        """
        Get current active episode

        Args:
            project_path: Optional project to filter by

        Returns:
            Current episode or None
        """
        if project_path:
            return self.active_episodes.get(project_path)

        # Return any active episode (if multiple, return most recent)
        if self.active_episodes:
            return max(self.active_episodes.values(), key=lambda e: e.start_time)

        return None

    def get_closed_episodes(self, limit: int = 100) -> List[Episode]:
        """
        Get closed episodes

        Args:
            limit: Maximum number of episodes to return

        Returns:
            List of closed episodes, newest first
        """
        return sorted(self.closed_episodes, key=lambda e: e.end_time or e.start_time, reverse=True)[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get episode statistics

        Returns:
            Dictionary with statistics
        """
        self._close_stale_episodes()

        # Count by type
        type_counts = defaultdict(int)
        for episode in self.closed_episodes:
            type_counts[episode.episode_type] += 1

        # Calculate average duration
        if self.closed_episodes:
            avg_duration = sum(e.duration.total_seconds() for e in self.closed_episodes) / len(self.closed_episodes)
        else:
            avg_duration = 0

        return {
            'active_episodes': len(self.active_episodes),
            'closed_episodes': len(self.closed_episodes),
            'episodes_by_type': dict(type_counts),
            'average_duration_minutes': avg_duration / 60,
            'inactivity_timeout_minutes': self.inactivity_timeout.total_seconds() / 60,
            'max_duration_minutes': self.max_episode_duration.total_seconds() / 60
        }

    def reset(self) -> None:
        """Reset builder state (useful for testing)"""
        self.active_episodes.clear()
        self.closed_episodes.clear()
        logger.debug("EpisodeBuilder reset")
