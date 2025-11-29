"""
Memory Aggregation System
Consolidates repeated memories into summaries

Research Foundation:
- "Repeated exposures strengthen initial trace but don't create new traces"
- "The brain maintains occurrence counts, not individual instances"
- "Forgetting redundancy is a form of intelligent compression"

विस्मृति भी विद्या है (Forgetting too is knowledge)
जय विदुराई! 🕉️
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from loguru import logger

from vidurai.core.data_structures_v3 import Memory, SalienceLevel
from vidurai.core.memory_fingerprint import MemoryFingerprint, MemoryFingerprinter


@dataclass
class AggregatedMemory:
    """
    A memory that represents multiple occurrences

    Instead of storing:
    - "TypeError in foo.py" (1000 times)

    We store:
    - "TypeError in foo.py occurred 1000 times over 3 days"
    """

    # Original memory object (first occurrence)
    original: Memory

    # Fingerprint for matching
    fingerprint: MemoryFingerprint

    # Occurrence tracking
    occurrence_count: int = 1
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)

    # List of timestamps when this occurred
    occurrence_times: List[datetime] = field(default_factory=list)

    def add_occurrence(self, timestamp: Optional[datetime] = None):
        """Record another occurrence of this memory"""
        timestamp = timestamp or datetime.now()
        self.occurrence_count += 1
        self.last_seen = timestamp
        self.occurrence_times.append(timestamp)

        # Keep only last 100 timestamps to avoid unbounded growth
        if len(self.occurrence_times) > 100:
            self.occurrence_times = self.occurrence_times[-100:]

    def to_summary_gist(self) -> str:
        """
        Generate summary gist for this aggregated memory

        Returns human-readable summary like:
        "TypeError in foo.py occurred 42 times over 2 days (last: 5 min ago)"
        """
        # Calculate time span
        if self.occurrence_count == 1:
            return self.original.gist

        time_span = self.last_seen - self.first_seen
        days = time_span.days
        hours = time_span.seconds // 3600

        # Time span description
        if days > 0:
            span_text = f"{days} day{'s' if days > 1 else ''}"
        elif hours > 0:
            span_text = f"{hours} hour{'s' if hours > 1 else ''}"
        else:
            span_text = "minutes"

        # Time since last occurrence
        now = datetime.now()
        since_last = now - self.last_seen
        if since_last.total_seconds() < 60:
            last_text = "just now"
        elif since_last.total_seconds() < 3600:
            mins = int(since_last.total_seconds() / 60)
            last_text = f"{mins} min ago"
        elif since_last.days == 0:
            hours = int(since_last.total_seconds() / 3600)
            last_text = f"{hours}h ago"
        else:
            last_text = f"{since_last.days}d ago"

        # Extract error/event type from original gist
        base_gist = self.original.gist

        # Build summary
        return (
            f"{base_gist} "
            f"(×{self.occurrence_count} over {span_text}, last: {last_text})"
        )

    def get_adjusted_salience(self) -> SalienceLevel:
        """
        Adjust salience based on repetition

        Philosophy:
        - First occurrence: Keep original salience
        - 2-5 occurrences: Slightly less important (noise emerging)
        - 6-20 occurrences: Downgrade (pattern, not emergency)
        - 20+ occurrences: Definitely noise

        Returns adjusted SalienceLevel
        """
        original_salience = self.original.salience

        # Single occurrence - keep original
        if self.occurrence_count == 1:
            return original_salience

        # Apply repetition penalty
        if self.occurrence_count <= 5:
            # 2-5 times: Slight downgrade
            if original_salience == SalienceLevel.CRITICAL:
                return SalienceLevel.HIGH
            elif original_salience == SalienceLevel.HIGH:
                return SalienceLevel.MEDIUM
            else:
                return original_salience

        elif self.occurrence_count <= 20:
            # 6-20 times: Medium downgrade
            if original_salience in [SalienceLevel.CRITICAL, SalienceLevel.HIGH]:
                return SalienceLevel.MEDIUM
            elif original_salience == SalienceLevel.MEDIUM:
                return SalienceLevel.LOW
            else:
                return SalienceLevel.NOISE

        else:
            # 20+ times: Definitely noise
            return SalienceLevel.NOISE


class MemoryAggregator:
    """
    Manages memory aggregation and deduplication

    Philosophy: "Forgetting redundancy while preserving patterns"
    """

    def __init__(self, aggregation_window: int = 7):
        """
        Initialize memory aggregator

        Args:
            aggregation_window: Days to look back for duplicates (default: 7)
        """
        self.fingerprinter = MemoryFingerprinter()
        self.aggregation_window = aggregation_window

        # In-memory cache of recent aggregations
        # Key: fingerprint string, Value: AggregatedMemory
        self.recent_aggregations: Dict[str, AggregatedMemory] = {}

        # Metrics
        self.metrics = {
            'memories_aggregated': 0,
            'occurrences_consolidated': 0,
            'duplicates_prevented': 0,
        }

        logger.info(f"Memory aggregator initialized (window: {aggregation_window} days)")

    def should_aggregate(
        self,
        new_memory: Memory,
        existing_memories: List[Dict]
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Determine if new memory should be aggregated with existing ones

        Args:
            new_memory: New memory to check
            existing_memories: Recent memories from database

        Returns:
            (should_aggregate, matching_memory_dict)
        """
        # Generate fingerprint for new memory
        new_fp = self.fingerprinter.fingerprint(
            content=new_memory.verbatim,
            metadata=new_memory.metadata
        )

        # Check cache first (faster)
        cache_key = str(new_fp)
        if cache_key in self.recent_aggregations:
            logger.debug(f"Cache hit for fingerprint: {cache_key}")
            return True, None  # Will update cache entry

        # Check against existing memories
        for existing in existing_memories:
            existing_fp = self.fingerprinter.fingerprint(
                content=existing.get('verbatim', ''),
                metadata={
                    'file': existing.get('file_path'),
                    'line': existing.get('line_number')
                }
            )

            # Check for match at pattern level
            if new_fp.matches(existing_fp, threshold='pattern'):
                logger.debug(
                    f"Found duplicate: {new_fp.error_type} in "
                    f"{new_fp.file_path}"
                )
                return True, existing

        return False, None

    def aggregate(
        self,
        new_memory: Memory,
        matching_memory: Optional[Dict] = None
    ) -> AggregatedMemory:
        """
        Create or update aggregated memory

        Args:
            new_memory: New memory to aggregate
            matching_memory: Optional existing memory dict from DB

        Returns:
            AggregatedMemory object
        """
        new_fp = self.fingerprinter.fingerprint(
            content=new_memory.verbatim,
            metadata=new_memory.metadata
        )
        cache_key = str(new_fp)

        # Update existing aggregation
        if cache_key in self.recent_aggregations:
            agg = self.recent_aggregations[cache_key]
            agg.add_occurrence()
            self.metrics['occurrences_consolidated'] += 1
            logger.debug(
                f"Updated aggregation: {agg.occurrence_count} occurrences"
            )
            return agg

        # Create new aggregation
        agg = AggregatedMemory(
            original=new_memory,
            fingerprint=new_fp,
            occurrence_count=1,
            first_seen=datetime.now(),
            last_seen=datetime.now(),
            occurrence_times=[datetime.now()]
        )

        # If matching existing memory, set initial count
        if matching_memory:
            # Extract occurrence count from existing tags
            tags = matching_memory.get('tags')
            if tags:
                try:
                    import json
                    tags_list = json.loads(tags) if isinstance(tags, str) else tags
                    for tag in tags_list:
                        if tag.startswith('occurrences:'):
                            count = int(tag.split(':')[1])
                            agg.occurrence_count = count + 1
                            break
                except:
                    pass

        self.recent_aggregations[cache_key] = agg
        self.metrics['memories_aggregated'] += 1

        return agg

    def get_storage_metadata(self, agg: AggregatedMemory) -> Dict:
        """
        Generate metadata for storing aggregated memory

        Returns dict with tags and counters
        """
        tags = [
            f"occurrences:{agg.occurrence_count}",
            f"first_seen:{agg.first_seen.isoformat()}",
            f"last_seen:{agg.last_seen.isoformat()}",
        ]

        if agg.fingerprint.error_type:
            tags.append(f"error_type:{agg.fingerprint.error_type}")

        return {
            'tags': tags,
            'access_count': agg.occurrence_count,
            'occurrence_metadata': {
                'count': agg.occurrence_count,
                'first': agg.first_seen.isoformat(),
                'last': agg.last_seen.isoformat(),
                'pattern_hash': agg.fingerprint.pattern_hash,
            }
        }

    def cleanup_cache(self, max_age_hours: int = 24):
        """
        Remove old entries from cache

        Args:
            max_age_hours: Maximum age in hours to keep in cache
        """
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        to_remove = []

        for key, agg in self.recent_aggregations.items():
            if agg.last_seen < cutoff:
                to_remove.append(key)

        for key in to_remove:
            del self.recent_aggregations[key]

        if to_remove:
            logger.debug(f"Cleaned {len(to_remove)} old aggregations from cache")

    def get_metrics(self) -> Dict:
        """Get aggregation metrics"""
        return {
            **self.metrics,
            'cache_size': len(self.recent_aggregations),
            'compression_ratio': (
                self.metrics['occurrences_consolidated'] /
                max(self.metrics['memories_aggregated'], 1)
            )
        }
