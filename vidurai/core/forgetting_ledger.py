"""
Forgetting Ledger System
Transparent logging of all forgetting events for auditability and trust

Philosophy: "Trust through transparency—every forgetting must be accountable"
विस्मृति भी विद्या है (Forgetting too is knowledge)

Research Foundation:
- Audit trails in automated systems
- Explainable AI and algorithmic transparency
- Trust calibration through observability
"""

import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger


@dataclass
class ForgettingEvent:
    """
    Record of a single forgetting event

    Captures complete information about what was forgotten and why.
    """
    timestamp: datetime
    event_type: str  # consolidation, decay, deletion, aggregation
    action: str  # compress_light, compress_aggressive, decay_low_value, etc.
    project_path: str

    # Quantitative impact
    memories_before: int
    memories_after: int
    memories_removed: List[int]  # IDs of removed memories
    consolidated_into: List[int]  # IDs of new consolidated memories

    # Preservation metrics
    entities_preserved: int
    root_causes_preserved: int
    resolutions_preserved: int

    # Metadata
    reason: str  # Why this action was taken
    policy: str  # rule_based, rl_based, manual
    reversible: bool  # Can this be undone?

    # Optional context
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        data = asdict(self)
        data['timestamp'] = data['timestamp'].isoformat()
        return data

    def get_compression_ratio(self) -> float:
        """Calculate compression ratio"""
        if self.memories_before == 0:
            return 0.0
        return 1.0 - (self.memories_after / self.memories_before)

    def get_summary(self) -> str:
        """Get one-line summary"""
        compression = self.get_compression_ratio()
        return (
            f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {self.event_type.upper()}: "
            f"{self.memories_before} → {self.memories_after} memories "
            f"({compression:.0%} reduction) - {self.reason}"
        )


class ForgettingLedger:
    """
    Append-only ledger of forgetting events

    Provides:
    - Complete audit trail
    - Query capabilities
    - Statistics and analytics
    - Transparency for users
    """

    def __init__(self, ledger_path: Optional[str] = None):
        """
        Initialize forgetting ledger

        Args:
            ledger_path: Path to ledger file (default: ~/.vidurai/forgetting_ledger.jsonl)
        """
        if ledger_path:
            self.ledger_path = Path(ledger_path).expanduser()
        else:
            self.ledger_path = Path.home() / ".vidurai" / "forgetting_ledger.jsonl"

        # Ensure directory exists
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)

        # Create file if it doesn't exist
        if not self.ledger_path.exists():
            self.ledger_path.touch()

        logger.debug(f"Forgetting ledger initialized at {self.ledger_path}")

    def log_event(self, event: ForgettingEvent):
        """
        Append event to ledger

        Args:
            event: ForgettingEvent to log
        """
        try:
            with open(self.ledger_path, 'a') as f:
                f.write(json.dumps(event.to_dict()) + '\n')

            logger.info(f"Logged forgetting event: {event.get_summary()}")

        except Exception as e:
            logger.error(f"Error logging forgetting event: {e}")

    def log_consolidation(
        self,
        project_path: str,
        memories_before: int,
        memories_after: int,
        memories_removed: List[int],
        consolidated_into: List[int],
        entities_preserved: int,
        root_causes_preserved: int,
        resolutions_preserved: int,
        action: str,
        reason: str,
        policy: str = "rule_based"
    ):
        """
        Convenience method to log consolidation event

        Args:
            project_path: Project path
            memories_before: Count before consolidation
            memories_after: Count after consolidation
            memories_removed: IDs of removed memories
            consolidated_into: IDs of new consolidated memories
            entities_preserved: Count of preserved entities
            root_causes_preserved: Count of preserved root causes
            resolutions_preserved: Count of preserved resolutions
            action: Specific action taken
            reason: Why consolidation occurred
            policy: Policy that decided this
        """
        event = ForgettingEvent(
            timestamp=datetime.now(),
            event_type="consolidation",
            action=action,
            project_path=project_path,
            memories_before=memories_before,
            memories_after=memories_after,
            memories_removed=memories_removed,
            consolidated_into=consolidated_into,
            entities_preserved=entities_preserved,
            root_causes_preserved=root_causes_preserved,
            resolutions_preserved=resolutions_preserved,
            reason=reason,
            policy=policy,
            reversible=False  # Consolidation is not reversible by default
        )
        self.log_event(event)

    def log_aggregation(
        self,
        project_path: str,
        memories_before: int,
        memories_after: int,
        duplicates_merged: int,
        action: str = "auto_merge",
        reason: str = "Duplicate detection"
    ):
        """
        Log aggregation event (duplicate merging)

        Args:
            project_path: Project path
            memories_before: Count before aggregation
            memories_after: Count after aggregation
            duplicates_merged: Number of duplicates merged
            action: Aggregation action
            reason: Why aggregation occurred
        """
        event = ForgettingEvent(
            timestamp=datetime.now(),
            event_type="aggregation",
            action=action,
            project_path=project_path,
            memories_before=memories_before,
            memories_after=memories_after,
            memories_removed=[],  # Not tracked for aggregation
            consolidated_into=[],
            entities_preserved=0,  # Aggregation preserves all entities
            root_causes_preserved=0,
            resolutions_preserved=0,
            reason=reason,
            policy="aggregation",
            reversible=True  # Aggregation can be reversed within 24h
        )
        self.log_event(event)

    def log_decay(
        self,
        project_path: str,
        memories_before: int,
        memories_after: int,
        memories_removed: List[int],
        action: str = "decay_low_value",
        reason: str = "Age-based decay"
    ):
        """
        Log decay event (deletion based on age/value)

        Args:
            project_path: Project path
            memories_before: Count before decay
            memories_after: Count after decay
            memories_removed: IDs of decayed memories
            action: Decay action
            reason: Why decay occurred
        """
        event = ForgettingEvent(
            timestamp=datetime.now(),
            event_type="decay",
            action=action,
            project_path=project_path,
            memories_before=memories_before,
            memories_after=memories_after,
            memories_removed=memories_removed,
            consolidated_into=[],
            entities_preserved=0,
            root_causes_preserved=0,
            resolutions_preserved=0,
            reason=reason,
            policy="retention_policy",
            reversible=False  # Decay is permanent
        )
        self.log_event(event)

    def get_events(
        self,
        project: Optional[str] = None,
        event_type: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[ForgettingEvent]:
        """
        Query forgetting events

        Args:
            project: Filter by project path
            event_type: Filter by event type (consolidation, decay, etc.)
            since: Only return events after this timestamp
            limit: Maximum number of events to return

        Returns:
            List of ForgettingEvent objects
        """
        try:
            events = []

            with open(self.ledger_path, 'r') as f:
                for line in f:
                    data = json.loads(line.strip())

                    # Parse timestamp
                    data['timestamp'] = datetime.fromisoformat(data['timestamp'])

                    # Create event object
                    event = ForgettingEvent(**data)

                    # Apply filters
                    if project and event.project_path != project:
                        continue
                    if event_type and event.event_type != event_type:
                        continue
                    if since and event.timestamp < since:
                        continue

                    events.append(event)

            # Sort by timestamp (newest first) and limit
            events.sort(key=lambda e: e.timestamp, reverse=True)
            return events[:limit]

        except FileNotFoundError:
            return []
        except Exception as e:
            logger.error(f"Error reading forgetting ledger: {e}")
            return []

    def get_statistics(
        self,
        project: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get aggregate statistics about forgetting events

        Args:
            project: Filter by project
            since: Only include events after this timestamp

        Returns:
            Dictionary with statistics
        """
        events = self.get_events(project=project, since=since, limit=10000)

        if not events:
            return {
                'total_events': 0,
                'by_type': {},
                'total_memories_removed': 0,
                'total_entities_preserved': 0,
            }

        # Count by type
        by_type = {}
        for event in events:
            by_type[event.event_type] = by_type.get(event.event_type, 0) + 1

        # Sum totals
        total_removed = sum(len(e.memories_removed) for e in events)
        total_entities_preserved = sum(e.entities_preserved for e in events)
        total_root_causes = sum(e.root_causes_preserved for e in events)
        total_resolutions = sum(e.resolutions_preserved for e in events)

        # Calculate average compression
        compression_ratios = [e.get_compression_ratio() for e in events if e.memories_before > 0]
        avg_compression = sum(compression_ratios) / len(compression_ratios) if compression_ratios else 0.0

        return {
            'total_events': len(events),
            'by_type': by_type,
            'total_memories_removed': total_removed,
            'total_entities_preserved': total_entities_preserved,
            'total_root_causes_preserved': total_root_causes,
            'total_resolutions_preserved': total_resolutions,
            'average_compression_ratio': avg_compression,
            'time_span': {
                'oldest': events[-1].timestamp.isoformat() if events else None,
                'newest': events[0].timestamp.isoformat() if events else None,
            }
        }

    def get_recent_summary(self, limit: int = 10) -> str:
        """
        Get human-readable summary of recent events

        Args:
            limit: Number of recent events to include

        Returns:
            Formatted string with event summaries
        """
        events = self.get_events(limit=limit)

        if not events:
            return "No forgetting events recorded."

        lines = [f"📋 Forgetting Log (last {len(events)} events)\n"]

        for event in events:
            # Format timestamp
            timestamp = event.timestamp.strftime('%Y-%m-%d %H:%M:%S')

            # Format impact
            compression = event.get_compression_ratio()
            impact = f"{event.memories_before} → {event.memories_after} memories ({compression:.0%} reduction)"

            # Format preservation
            preservation = []
            if event.entities_preserved > 0:
                preservation.append(f"{event.entities_preserved} entities")
            if event.root_causes_preserved > 0:
                preservation.append(f"{event.root_causes_preserved} root causes")
            if event.resolutions_preserved > 0:
                preservation.append(f"{event.resolutions_preserved} resolutions")

            preservation_text = f"Preserved: {', '.join(preservation)}" if preservation else ""

            # Format reversibility
            reversible = "Reversible: Yes (within 24h)" if event.reversible else "Reversible: No"

            lines.extend([
                f"[{timestamp}] {event.event_type.upper()}",
                f"  Action: {event.action}",
                f"  Reason: {event.reason}",
                f"  Impact: {impact}",
            ])

            if preservation_text:
                lines.append(f"  {preservation_text}")

            lines.extend([
                f"  Policy: {event.policy}",
                f"  {reversible}",
                ""
            ])

        return "\n".join(lines)

    # DEPRECATED: Removed to enforce append-only immutability compliance (v2.2.0 Audit).
    # def clear_old_events(self, older_than_days: int = 365):
    #     """
    #     Remove events older than specified days
    #     
    #     REMOVED: This method violated the append-only immutability rule.
    #     The forgetting ledger must remain append-only for audit compliance.
    #     """
    #     pass


# Global ledger instance
_global_ledger: Optional[ForgettingLedger] = None


def get_ledger() -> ForgettingLedger:
    """
    Get global ledger instance (singleton)

    Returns:
        ForgettingLedger instance
    """
    global _global_ledger
    if _global_ledger is None:
        _global_ledger = ForgettingLedger()
    return _global_ledger
