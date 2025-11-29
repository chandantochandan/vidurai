"""
Proactive Hints - Context-Aware Suggestions from Episodes
Phase 6.5: Passive & Automatic Memory Capture

Philosophy: विस्मृति भी विद्या है - Your past work guides your future

Design:
- Detect patterns across episodes and memories
- Generate context-aware suggestions
- Proactive warnings about similar past issues
- Learning from historical debugging patterns

Hint Types:
1. Similar Episode Detection - "You debugged similar issues before"
2. Pattern Warnings - "This pattern failed in episode X"
3. Success Patterns - "This approach worked in past episodes"
4. File Context - "Last time you edited this file, you also modified Y"
5. Query Suggestions - "Related memories: X, Y, Z"

Architecture:
- Pattern detectors analyze episodes and memories
- Hint generators create suggestions
- Delivery mechanisms push hints to user
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, Counter
from loguru import logger

try:
    from vidurai.core.episode_builder import Episode, EpisodeBuilder
    from vidurai.core.event_bus import ViduraiEvent
    EPISODE_AVAILABLE = True
except ImportError:
    EPISODE_AVAILABLE = False
    Episode = None
    EpisodeBuilder = None
    ViduraiEvent = None


@dataclass
class Hint:
    """
    Represents a proactive hint or suggestion

    Attributes:
        id: Unique hint identifier
        hint_type: Type of hint (similar_episode, pattern_warning, etc.)
        title: Short hint title
        message: Detailed hint message
        confidence: Confidence score (0.0 to 1.0)
        source_episodes: Episode IDs that triggered this hint
        context: Additional context data
        timestamp: When hint was generated
    """

    id: str = field(default_factory=lambda: str(__import__('uuid').uuid4()))
    hint_type: str = ""  # similar_episode, pattern_warning, success_pattern, etc.
    title: str = ""
    message: str = ""
    confidence: float = 0.0  # 0.0 to 1.0
    source_episodes: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'hint_type': self.hint_type,
            'title': self.title,
            'message': self.message,
            'confidence': self.confidence,
            'source_episodes': self.source_episodes,
            'context': self.context,
            'timestamp': self.timestamp.isoformat()
        }

    def __str__(self) -> str:
        """Human-readable representation"""
        return f"[{self.hint_type}] {self.title} (confidence: {self.confidence:.2f})"


class PatternDetector:
    """
    Detects patterns across episodes and memories

    Pattern Types:
    - Similar episodes (same files, similar errors)
    - Recurring issues (same error patterns)
    - File co-modification patterns
    - Successful debugging sequences
    """

    def __init__(self, min_similarity: float = 0.6):
        """
        Initialize PatternDetector

        Args:
            min_similarity: Minimum similarity threshold (0.0 to 1.0)
        """
        self.min_similarity = min_similarity
        logger.info(f"PatternDetector initialized: min_similarity={min_similarity}")

    def find_similar_episodes(
        self,
        current_episode: Episode,
        historical_episodes: List[Episode]
    ) -> List[Tuple[Episode, float]]:
        """
        Find episodes similar to the current one

        Similarity factors:
        - Same files
        - Similar error patterns (from gist/summary)
        - Same episode type
        - Similar duration/event count

        Args:
            current_episode: The current episode to compare
            historical_episodes: Past episodes to search

        Returns:
            List of (episode, similarity_score) tuples, sorted by score
        """
        similar = []

        for hist_episode in historical_episodes:
            # Skip if same episode
            if hist_episode.id == current_episode.id:
                continue

            # Calculate similarity
            similarity = self._calculate_similarity(current_episode, hist_episode)

            if similarity >= self.min_similarity:
                similar.append((hist_episode, similarity))

        # Sort by similarity (highest first)
        similar.sort(key=lambda x: x[1], reverse=True)

        logger.debug(
            f"Found {len(similar)} similar episodes to {current_episode.id[:8]} "
            f"(threshold: {self.min_similarity})"
        )

        return similar

    def _calculate_similarity(self, ep1: Episode, ep2: Episode) -> float:
        """
        Calculate similarity score between two episodes

        Weights:
        - File overlap: 40%
        - Episode type match: 30%
        - Text similarity (summary/gist): 30%

        Args:
            ep1: First episode
            ep2: Second episode

        Returns:
            Similarity score (0.0 to 1.0)
        """
        scores = []

        # File overlap (Jaccard similarity)
        if ep1.file_paths or ep2.file_paths:
            intersection = len(ep1.file_paths & ep2.file_paths)
            union = len(ep1.file_paths | ep2.file_paths)
            file_score = intersection / union if union > 0 else 0.0
            scores.append(('file_overlap', file_score, 0.4))

        # Episode type match
        type_score = 1.0 if ep1.episode_type == ep2.episode_type else 0.0
        scores.append(('type_match', type_score, 0.3))

        # Text similarity (simple keyword overlap)
        text_score = self._text_similarity(ep1.summary, ep2.summary)
        scores.append(('text_similarity', text_score, 0.3))

        # Weighted average
        total_weight = sum(weight for _, _, weight in scores)
        if total_weight == 0:
            return 0.0

        weighted_sum = sum(score * weight for _, score, weight in scores)
        similarity = weighted_sum / total_weight

        logger.debug(
            f"Similarity({ep1.id[:8]}, {ep2.id[:8]}): {similarity:.2f} "
            f"[file={scores[0][1]:.2f}, type={scores[1][1]:.2f}, text={scores[2][1]:.2f}]"
        )

        return similarity

    def _text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate simple text similarity using keyword overlap

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0.0 to 1.0)
        """
        if not text1 or not text2:
            return 0.0

        # Extract keywords (lowercase, filter common words)
        stopwords = {'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 'but'}

        def extract_keywords(text: str) -> Set[str]:
            words = text.lower().split()
            return {w for w in words if len(w) > 2 and w not in stopwords}

        keywords1 = extract_keywords(text1)
        keywords2 = extract_keywords(text2)

        if not keywords1 or not keywords2:
            return 0.0

        # Jaccard similarity
        intersection = len(keywords1 & keywords2)
        union = len(keywords1 | keywords2)

        return intersection / union if union > 0 else 0.0

    def detect_recurring_patterns(
        self,
        episodes: List[Episode],
        min_occurrences: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Detect recurring patterns across episodes

        Patterns:
        - Recurring errors (same keywords in summaries)
        - Frequently modified files
        - Common episode types

        Args:
            episodes: Episodes to analyze
            min_occurrences: Minimum occurrences to be considered a pattern

        Returns:
            List of pattern dictionaries
        """
        patterns = []

        # 1. Recurring error keywords
        error_keywords = Counter()
        for episode in episodes:
            if episode.episode_type == "bugfix":
                keywords = self._extract_error_keywords(episode.summary)
                error_keywords.update(keywords)

        for keyword, count in error_keywords.items():
            if count >= min_occurrences:
                patterns.append({
                    'type': 'recurring_error',
                    'keyword': keyword,
                    'occurrences': count,
                    'message': f"'{keyword}' error occurred {count} times"
                })

        # 2. Frequently modified files
        file_counter = Counter()
        for episode in episodes:
            file_counter.update(episode.file_paths)

        for file_path, count in file_counter.items():
            if count >= min_occurrences:
                patterns.append({
                    'type': 'frequent_file',
                    'file': file_path,
                    'occurrences': count,
                    'message': f"'{file_path}' modified in {count} episodes"
                })

        # 3. Episode type distribution
        type_counter = Counter(ep.episode_type for ep in episodes)
        for ep_type, count in type_counter.items():
            if count >= min_occurrences:
                patterns.append({
                    'type': 'episode_type_pattern',
                    'episode_type': ep_type,
                    'occurrences': count,
                    'message': f"{count} {ep_type} episodes"
                })

        logger.info(f"Detected {len(patterns)} recurring patterns")
        return patterns

    def _extract_error_keywords(self, text: str) -> Set[str]:
        """
        Extract error-related keywords from text

        Args:
            text: Text to analyze

        Returns:
            Set of error keywords
        """
        if not text:
            return set()

        # Common error keywords
        error_terms = {
            'error', 'exception', 'bug', 'fail', 'crash', 'issue',
            'typeerror', 'valueerror', 'attributeerror', 'keyerror',
            'nullpointer', 'undefined', 'null', 'nan'
        }

        words = set(text.lower().split())
        return words & error_terms

    def find_file_comodification_patterns(
        self,
        episodes: List[Episode],
        min_support: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Find files that are frequently modified together

        Args:
            episodes: Episodes to analyze
            min_support: Minimum co-occurrences

        Returns:
            List of co-modification pattern dictionaries
        """
        # Count file pairs that appear together
        pair_counts = defaultdict(int)

        for episode in episodes:
            files = sorted(episode.file_paths)
            # Generate all pairs
            for i, file1 in enumerate(files):
                for file2 in files[i+1:]:
                    pair = (file1, file2)
                    pair_counts[pair] += 1

        # Filter by minimum support
        patterns = []
        for (file1, file2), count in pair_counts.items():
            if count >= min_support:
                patterns.append({
                    'type': 'file_comodification',
                    'files': [file1, file2],
                    'occurrences': count,
                    'message': f"'{file1}' and '{file2}' modified together {count} times"
                })

        logger.info(f"Found {len(patterns)} co-modification patterns")
        return patterns


class HintGenerator:
    """
    Generates proactive hints from detected patterns

    Hint Generation:
    - Similar episode hints
    - Pattern warning hints
    - Success pattern hints
    - Context suggestion hints
    """

    def __init__(self, pattern_detector: PatternDetector):
        """
        Initialize HintGenerator

        Args:
            pattern_detector: PatternDetector instance
        """
        self.pattern_detector = pattern_detector
        logger.info("HintGenerator initialized")

    def generate_similar_episode_hints(
        self,
        current_episode: Episode,
        historical_episodes: List[Episode],
        max_hints: int = 3
    ) -> List[Hint]:
        """
        Generate hints about similar past episodes

        Args:
            current_episode: Current episode
            historical_episodes: Past episodes
            max_hints: Maximum number of hints to generate

        Returns:
            List of hints
        """
        hints = []

        similar_episodes = self.pattern_detector.find_similar_episodes(
            current_episode,
            historical_episodes
        )

        for hist_episode, similarity in similar_episodes[:max_hints]:
            hint = Hint(
                hint_type="similar_episode",
                title=f"Similar to past {hist_episode.episode_type}",
                message=self._format_similar_episode_message(current_episode, hist_episode),
                confidence=similarity,
                source_episodes=[hist_episode.id],
                context={
                    'similar_episode_id': hist_episode.id,
                    'similar_episode_type': hist_episode.episode_type,
                    'similar_episode_summary': hist_episode.summary,
                    'similarity_score': similarity,
                    'common_files': list(current_episode.file_paths & hist_episode.file_paths)
                }
            )
            hints.append(hint)

        logger.info(f"Generated {len(hints)} similar episode hints")
        return hints

    def _format_similar_episode_message(
        self,
        current: Episode,
        similar: Episode
    ) -> str:
        """
        Format a message about a similar episode

        Args:
            current: Current episode
            similar: Similar past episode

        Returns:
            Formatted message
        """
        common_files = current.file_paths & similar.file_paths

        parts = []
        parts.append(f"You worked on a similar {similar.episode_type} before:")
        parts.append(f"  • {similar.summary}")

        if common_files:
            file_list = ", ".join(list(common_files)[:3])
            parts.append(f"  • Common files: {file_list}")

        if similar.duration:
            duration_mins = int(similar.duration.total_seconds() / 60)
            parts.append(f"  • Took {duration_mins} minutes with {similar.event_count} steps")

        return "\n".join(parts)

    def generate_pattern_warning_hints(
        self,
        current_episode: Episode,
        patterns: List[Dict[str, Any]]
    ) -> List[Hint]:
        """
        Generate warning hints about recurring patterns

        Args:
            current_episode: Current episode
            patterns: Detected patterns

        Returns:
            List of warning hints
        """
        hints = []

        # Check for recurring errors
        for pattern in patterns:
            if pattern['type'] == 'recurring_error':
                # Check if current episode involves this error
                if current_episode.episode_type == "bugfix":
                    keyword = pattern['keyword']
                    if keyword in current_episode.summary.lower():
                        hint = Hint(
                            hint_type="pattern_warning",
                            title=f"Recurring issue: {keyword}",
                            message=f"This '{keyword}' error has occurred {pattern['occurrences']} times before. "
                                    f"Review past solutions.",
                            confidence=0.8,
                            source_episodes=[],
                            context={
                                'pattern_type': 'recurring_error',
                                'keyword': keyword,
                                'occurrences': pattern['occurrences']
                            }
                        )
                        hints.append(hint)

        logger.info(f"Generated {len(hints)} pattern warning hints")
        return hints

    def generate_success_pattern_hints(
        self,
        current_episode: Episode,
        successful_episodes: List[Episode]
    ) -> List[Hint]:
        """
        Generate hints about successful patterns

        Args:
            current_episode: Current episode
            successful_episodes: Past successful episodes

        Returns:
            List of success hints
        """
        hints = []

        # Find successful episodes with similar context
        for success_ep in successful_episodes:
            if success_ep.episode_type != current_episode.episode_type:
                continue

            common_files = current_episode.file_paths & success_ep.file_paths
            if not common_files:
                continue

            hint = Hint(
                hint_type="success_pattern",
                title=f"Successful {success_ep.episode_type} pattern",
                message=f"Similar successful {success_ep.episode_type}:\n"
                        f"  • {success_ep.summary}\n"
                        f"  • Common files: {', '.join(list(common_files)[:3])}",
                confidence=0.7,
                source_episodes=[success_ep.id],
                context={
                    'success_episode_id': success_ep.id,
                    'success_episode_summary': success_ep.summary,
                    'common_files': list(common_files)
                }
            )
            hints.append(hint)

        logger.info(f"Generated {len(hints)} success pattern hints")
        return hints[:3]  # Limit to top 3

    def generate_file_context_hints(
        self,
        current_episode: Episode,
        comod_patterns: List[Dict[str, Any]]
    ) -> List[Hint]:
        """
        Generate hints about related files

        Args:
            current_episode: Current episode
            comod_patterns: Co-modification patterns

        Returns:
            List of file context hints
        """
        hints = []

        current_files = current_episode.file_paths

        for pattern in comod_patterns:
            if pattern['type'] != 'file_comodification':
                continue

            files = pattern['files']
            # Check if one of the files is in current episode
            if files[0] in current_files and files[1] not in current_files:
                hint = Hint(
                    hint_type="file_context",
                    title=f"Consider checking {files[1]}",
                    message=f"When modifying '{files[0]}', you typically also modify '{files[1]}' "
                            f"({pattern['occurrences']} times before)",
                    confidence=0.6,
                    source_episodes=[],
                    context={
                        'file': files[0],
                        'related_file': files[1],
                        'occurrences': pattern['occurrences']
                    }
                )
                hints.append(hint)
            elif files[1] in current_files and files[0] not in current_files:
                hint = Hint(
                    hint_type="file_context",
                    title=f"Consider checking {files[0]}",
                    message=f"When modifying '{files[1]}', you typically also modify '{files[0]}' "
                            f"({pattern['occurrences']} times before)",
                    confidence=0.6,
                    source_episodes=[],
                    context={
                        'file': files[1],
                        'related_file': files[0],
                        'occurrences': pattern['occurrences']
                    }
                )
                hints.append(hint)

        logger.info(f"Generated {len(hints)} file context hints")
        return hints


class ProactiveHintEngine:
    """
    Main engine for proactive hint generation

    Coordinates pattern detection and hint generation
    """

    def __init__(
        self,
        episode_builder: 'EpisodeBuilder',
        min_similarity: float = 0.6,
        max_hints_per_type: int = 3
    ):
        """
        Initialize ProactiveHintEngine

        Args:
            episode_builder: EpisodeBuilder instance
            min_similarity: Minimum similarity for pattern detection
            max_hints_per_type: Maximum hints per type
        """
        self.episode_builder = episode_builder
        self.pattern_detector = PatternDetector(min_similarity=min_similarity)
        self.hint_generator = HintGenerator(self.pattern_detector)
        self.max_hints_per_type = max_hints_per_type

        # Cache for patterns
        self._pattern_cache = {}
        self._cache_timestamp = None
        self._cache_ttl = timedelta(minutes=5)

        logger.info("ProactiveHintEngine initialized")

    def generate_hints_for_episode(
        self,
        episode: Episode,
        hint_types: Optional[List[str]] = None
    ) -> List[Hint]:
        """
        Generate all relevant hints for an episode

        Args:
            episode: Episode to generate hints for
            hint_types: Optional list of hint types to generate
                       (similar_episode, pattern_warning, success_pattern, file_context)

        Returns:
            List of generated hints
        """
        if hint_types is None:
            hint_types = ['similar_episode', 'pattern_warning', 'success_pattern', 'file_context']

        all_hints = []

        # Get historical episodes
        historical_episodes = self.episode_builder.get_closed_episodes(limit=100)

        # Generate similar episode hints
        if 'similar_episode' in hint_types:
            hints = self.hint_generator.generate_similar_episode_hints(
                episode,
                historical_episodes,
                max_hints=self.max_hints_per_type
            )
            all_hints.extend(hints)

        # Detect patterns (with caching)
        patterns = self._get_patterns(historical_episodes)

        # Generate pattern warning hints
        if 'pattern_warning' in hint_types:
            hints = self.hint_generator.generate_pattern_warning_hints(
                episode,
                patterns['recurring']
            )
            all_hints.extend(hints[:self.max_hints_per_type])

        # Generate success pattern hints
        if 'success_pattern' in hint_types:
            successful_eps = [ep for ep in historical_episodes if ep.event_count >= 3]
            hints = self.hint_generator.generate_success_pattern_hints(
                episode,
                successful_eps
            )
            all_hints.extend(hints[:self.max_hints_per_type])

        # Generate file context hints
        if 'file_context' in hint_types:
            hints = self.hint_generator.generate_file_context_hints(
                episode,
                patterns['comodification']
            )
            all_hints.extend(hints[:self.max_hints_per_type])

        # Sort by confidence
        all_hints.sort(key=lambda h: h.confidence, reverse=True)

        logger.info(f"Generated {len(all_hints)} hints for episode {episode.id[:8]}")
        return all_hints

    def _get_patterns(self, episodes: List[Episode]) -> Dict[str, List]:
        """
        Get patterns with caching

        Args:
            episodes: Episodes to analyze

        Returns:
            Dictionary of pattern types
        """
        now = datetime.now()

        # Check cache
        if (self._cache_timestamp is not None and
            now - self._cache_timestamp < self._cache_ttl):
            logger.debug("Using cached patterns")
            return self._pattern_cache

        # Detect patterns
        logger.debug("Detecting new patterns")
        recurring = self.pattern_detector.detect_recurring_patterns(episodes)
        comodification = self.pattern_detector.find_file_comodification_patterns(episodes)

        self._pattern_cache = {
            'recurring': recurring,
            'comodification': comodification
        }
        self._cache_timestamp = now

        return self._pattern_cache

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get engine statistics

        Returns:
            Dictionary with statistics
        """
        historical = self.episode_builder.get_closed_episodes(limit=100)
        patterns = self._get_patterns(historical)

        return {
            'total_episodes': len(historical),
            'recurring_patterns': len(patterns['recurring']),
            'comodification_patterns': len(patterns['comodification']),
            'min_similarity': self.pattern_detector.min_similarity,
            'max_hints_per_type': self.max_hints_per_type
        }
