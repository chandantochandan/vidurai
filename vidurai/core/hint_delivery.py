"""
Hint Delivery - Integration Layer for Proactive Hints
Phase 6.6: Hint Delivery to CLI/MCP/Extensions

Philosophy: विस्मृति भी विद्या है - Deliver insights at the right moment

Design:
- Format hints for different delivery channels (CLI, MCP, IDE)
- Filter and rank hints by relevance and confidence
- Provide hint summaries and details
- Track hint delivery metrics

Delivery Channels:
1. CLI - Rich terminal formatting with colors
2. MCP Server - JSON responses for AI tools
3. IDE Extensions - Structured data for tooltips/notifications
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger

try:
    from vidurai.core.proactive_hints import Hint, ProactiveHintEngine
    from vidurai.core.episode_builder import Episode, EpisodeBuilder
    HINTS_AVAILABLE = True
except ImportError:
    HINTS_AVAILABLE = False
    Hint = None
    ProactiveHintEngine = None
    Episode = None
    EpisodeBuilder = None


class HintFormatter:
    """
    Formats hints for different delivery channels

    Supported formats:
    - CLI (terminal with colors)
    - JSON (for MCP server)
    - Markdown (for documentation/reports)
    - Plain text (fallback)
    """

    # ANSI color codes for terminal
    COLORS = {
        'reset': '\033[0m',
        'bold': '\033[1m',
        'dim': '\033[2m',
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'cyan': '\033[96m',
    }

    # Emoji icons for hint types
    ICONS = {
        'similar_episode': '🔄',
        'pattern_warning': '⚠️',
        'success_pattern': '✅',
        'file_context': '📁',
    }

    @staticmethod
    def format_cli(hints: List[Hint], show_context: bool = False, max_hints: int = 5) -> str:
        """
        Format hints for CLI display with colors and icons

        Args:
            hints: List of hints to format
            show_context: Include detailed context data
            max_hints: Maximum hints to display

        Returns:
            Formatted string for terminal output
        """
        if not hints:
            return f"{HintFormatter.COLORS['dim']}No hints available{HintFormatter.COLORS['reset']}"

        lines = []
        lines.append("")
        lines.append(f"{HintFormatter.COLORS['bold']}💡 Proactive Hints:{HintFormatter.COLORS['reset']}")
        lines.append("")

        for i, hint in enumerate(hints[:max_hints], 1):
            # Hint header with icon and confidence
            icon = HintFormatter.ICONS.get(hint.hint_type, '💡')
            confidence_color = HintFormatter._confidence_color(hint.confidence)

            lines.append(
                f"{i}. {icon} {HintFormatter.COLORS['bold']}{hint.title}{HintFormatter.COLORS['reset']} "
                f"({confidence_color}confidence: {hint.confidence:.0%}{HintFormatter.COLORS['reset']})"
            )

            # Hint message (indented)
            for line in hint.message.split('\n'):
                if line.strip():
                    lines.append(f"   {HintFormatter.COLORS['dim']}{line}{HintFormatter.COLORS['reset']}")

            # Optional context data
            if show_context and hint.context:
                lines.append(f"   {HintFormatter.COLORS['dim']}Context:{HintFormatter.COLORS['reset']}")
                for key, value in list(hint.context.items())[:3]:  # Show top 3 context items
                    if isinstance(value, (str, int, float, bool)):
                        lines.append(f"     • {key}: {value}")

            lines.append("")

        if len(hints) > max_hints:
            lines.append(f"{HintFormatter.COLORS['dim']}... and {len(hints) - max_hints} more hints{HintFormatter.COLORS['reset']}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def format_json(hints: List[Hint]) -> Dict[str, Any]:
        """
        Format hints for JSON/MCP server response

        Args:
            hints: List of hints to format

        Returns:
            JSON-serializable dictionary
        """
        return {
            'hints': [hint.to_dict() for hint in hints],
            'count': len(hints),
            'timestamp': datetime.now().isoformat(),
            'hint_types': list(set(h.hint_type for h in hints)),
            'avg_confidence': sum(h.confidence for h in hints) / len(hints) if hints else 0.0
        }

    @staticmethod
    def format_markdown(hints: List[Hint], title: str = "Proactive Hints") -> str:
        """
        Format hints as Markdown

        Args:
            hints: List of hints to format
            title: Section title

        Returns:
            Markdown-formatted string
        """
        if not hints:
            return f"## {title}\n\nNo hints available.\n"

        lines = []
        lines.append(f"## {title}\n")

        for i, hint in enumerate(hints, 1):
            icon = HintFormatter.ICONS.get(hint.hint_type, '💡')
            lines.append(f"### {i}. {icon} {hint.title}")
            lines.append(f"**Type**: {hint.hint_type} | **Confidence**: {hint.confidence:.0%}\n")
            lines.append(hint.message)
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def format_plain(hints: List[Hint]) -> str:
        """
        Format hints as plain text (no colors/formatting)

        Args:
            hints: List of hints to format

        Returns:
            Plain text string
        """
        if not hints:
            return "No hints available"

        lines = []
        lines.append("Proactive Hints:")
        lines.append("")

        for i, hint in enumerate(hints, 1):
            lines.append(f"{i}. {hint.title} (confidence: {hint.confidence:.0%})")
            lines.append(f"   {hint.message}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _confidence_color(confidence: float) -> str:
        """Get color code based on confidence level"""
        if confidence >= 0.8:
            return HintFormatter.COLORS['green']
        elif confidence >= 0.6:
            return HintFormatter.COLORS['yellow']
        else:
            return HintFormatter.COLORS['red']


class HintFilter:
    """
    Filters and ranks hints based on various criteria

    Filtering:
    - Minimum confidence threshold
    - Hint type inclusion/exclusion
    - Deduplication
    - Recency (prefer recent episodes)

    Ranking:
    - By confidence (default)
    - By hint type priority
    - By episode recency
    """

    def __init__(
        self,
        min_confidence: float = 0.5,
        hint_type_priority: Optional[Dict[str, int]] = None
    ):
        """
        Initialize HintFilter

        Args:
            min_confidence: Minimum confidence threshold (0.0-1.0)
            hint_type_priority: Custom priority for hint types (higher = more important)
                               Default: pattern_warning=4, similar_episode=3, success_pattern=2, file_context=1
        """
        self.min_confidence = min_confidence
        self.hint_type_priority = hint_type_priority or {
            'pattern_warning': 4,
            'similar_episode': 3,
            'success_pattern': 2,
            'file_context': 1
        }

        logger.info(f"HintFilter initialized: min_confidence={min_confidence}")

    def filter_hints(
        self,
        hints: List[Hint],
        include_types: Optional[List[str]] = None,
        exclude_types: Optional[List[str]] = None
    ) -> List[Hint]:
        """
        Filter hints by confidence and type

        Args:
            hints: List of hints to filter
            include_types: Only include these hint types
            exclude_types: Exclude these hint types

        Returns:
            Filtered list of hints
        """
        filtered = []

        for hint in hints:
            # Check confidence
            if hint.confidence < self.min_confidence:
                continue

            # Check type inclusion
            if include_types and hint.hint_type not in include_types:
                continue

            # Check type exclusion
            if exclude_types and hint.hint_type in exclude_types:
                continue

            filtered.append(hint)

        logger.debug(f"Filtered {len(hints)} hints to {len(filtered)}")
        return filtered

    def rank_hints(
        self,
        hints: List[Hint],
        ranking_method: str = 'confidence'
    ) -> List[Hint]:
        """
        Rank hints by specified method

        Args:
            hints: List of hints to rank
            ranking_method: 'confidence', 'type_priority', or 'combined'

        Returns:
            Sorted list of hints
        """
        if ranking_method == 'confidence':
            # Sort by confidence (highest first)
            return sorted(hints, key=lambda h: h.confidence, reverse=True)

        elif ranking_method == 'type_priority':
            # Sort by hint type priority
            return sorted(
                hints,
                key=lambda h: self.hint_type_priority.get(h.hint_type, 0),
                reverse=True
            )

        elif ranking_method == 'combined':
            # Combined: type priority * confidence
            return sorted(
                hints,
                key=lambda h: self.hint_type_priority.get(h.hint_type, 0) * h.confidence,
                reverse=True
            )

        else:
            logger.warning(f"Unknown ranking method: {ranking_method}, using confidence")
            return sorted(hints, key=lambda h: h.confidence, reverse=True)

    def deduplicate_hints(self, hints: List[Hint]) -> List[Hint]:
        """
        Remove duplicate hints based on title similarity

        Args:
            hints: List of hints to deduplicate

        Returns:
            Deduplicated list of hints
        """
        seen_titles = set()
        unique = []

        for hint in hints:
            # Use lowercase title as key
            key = hint.title.lower()

            if key not in seen_titles:
                seen_titles.add(key)
                unique.append(hint)

        if len(unique) < len(hints):
            logger.debug(f"Deduplicated {len(hints)} hints to {len(unique)}")

        return unique


class HintDeliveryService:
    """
    Main service for hint delivery across all channels

    Responsibilities:
    - Generate hints from current episode
    - Filter and rank hints
    - Format for specific channels
    - Track delivery metrics
    """

    def __init__(
        self,
        episode_builder: 'EpisodeBuilder',
        hint_engine: Optional['ProactiveHintEngine'] = None,
        hint_filter: Optional['HintFilter'] = None
    ):
        """
        Initialize HintDeliveryService

        Args:
            episode_builder: EpisodeBuilder instance
            hint_engine: ProactiveHintEngine instance (creates default if None)
            hint_filter: HintFilter instance (creates default if None)
        """
        self.episode_builder = episode_builder
        self.hint_engine = hint_engine or ProactiveHintEngine(episode_builder)
        self.hint_filter = hint_filter or HintFilter()
        self.formatter = HintFormatter()

        # Metrics
        self.hints_delivered = 0
        self.hints_filtered = 0

        logger.info("HintDeliveryService initialized")

    def get_hints_for_project(
        self,
        project_path: str,
        hint_types: Optional[List[str]] = None,
        min_confidence: float = 0.5,
        max_hints: int = 5
    ) -> List[Hint]:
        """
        Get hints for a project's current episode

        Args:
            project_path: Path to project
            hint_types: Optional list of hint types to include
            min_confidence: Minimum confidence threshold
            max_hints: Maximum number of hints to return

        Returns:
            List of filtered and ranked hints
        """
        # Get current episode
        current_episode = self.episode_builder.get_current_episode(project_path)

        if not current_episode:
            logger.debug(f"No current episode for {project_path}")
            return []

        # Generate hints
        hints = self.hint_engine.generate_hints_for_episode(
            current_episode,
            hint_types=hint_types
        )

        # Filter by confidence
        self.hint_filter.min_confidence = min_confidence
        filtered = self.hint_filter.filter_hints(hints, include_types=hint_types)

        # Deduplicate
        unique = self.hint_filter.deduplicate_hints(filtered)

        # Rank by combined score
        ranked = self.hint_filter.rank_hints(unique, ranking_method='combined')

        # Limit
        result = ranked[:max_hints]

        self.hints_filtered += len(hints) - len(result)
        self.hints_delivered += len(result)

        logger.info(
            f"Delivered {len(result)} hints for {project_path} "
            f"(filtered {len(hints) - len(result)})"
        )

        return result

    def format_for_cli(
        self,
        hints: List[Hint],
        show_context: bool = False
    ) -> str:
        """
        Format hints for CLI display

        Args:
            hints: Hints to format
            show_context: Show detailed context

        Returns:
            Formatted CLI string
        """
        return self.formatter.format_cli(hints, show_context=show_context)

    def format_for_mcp(self, hints: List[Hint]) -> Dict[str, Any]:
        """
        Format hints for MCP server response

        Args:
            hints: Hints to format

        Returns:
            JSON-serializable dictionary
        """
        return self.formatter.format_json(hints)

    def format_for_markdown(self, hints: List[Hint], title: str = "Proactive Hints") -> str:
        """
        Format hints as Markdown

        Args:
            hints: Hints to format
            title: Section title

        Returns:
            Markdown string
        """
        return self.formatter.format_markdown(hints, title=title)

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get delivery service statistics

        Returns:
            Dictionary with statistics
        """
        return {
            'hints_delivered': self.hints_delivered,
            'hints_filtered': self.hints_filtered,
            'engine_stats': self.hint_engine.get_statistics(),
            'filter_config': {
                'min_confidence': self.hint_filter.min_confidence,
                'type_priority': self.hint_filter.hint_type_priority
            }
        }


def create_hint_service(episode_builder: 'EpisodeBuilder') -> HintDeliveryService:
    """
    Factory function to create a fully configured HintDeliveryService

    Args:
        episode_builder: EpisodeBuilder instance

    Returns:
        Configured HintDeliveryService
    """
    # Create hint engine with reasonable defaults
    hint_engine = ProactiveHintEngine(
        episode_builder=episode_builder,
        min_similarity=0.6,
        max_hints_per_type=3
    )

    # Create filter with reasonable defaults
    hint_filter = HintFilter(
        min_confidence=0.5,
        hint_type_priority={
            'pattern_warning': 4,  # Warnings are most important
            'similar_episode': 3,  # History is very useful
            'success_pattern': 2,  # Success patterns are helpful
            'file_context': 1      # File suggestions are nice-to-have
        }
    )

    # Create service
    service = HintDeliveryService(
        episode_builder=episode_builder,
        hint_engine=hint_engine,
        hint_filter=hint_filter
    )

    logger.info("Created HintDeliveryService with default configuration")
    return service
