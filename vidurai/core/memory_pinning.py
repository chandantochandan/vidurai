"""
Memory Pinning System
Allows users to pin critical memories that should never be forgotten

Philosophy: "Trust the system, but control what matters most"
विस्मृति भी विद्या है (Forgetting too is knowledge)

v2.5: Updated to use MemoryDatabase public API (Queue-Based Actor pattern)
- No direct self.db.conn access (prevents lock contention)
- All writes route through _enqueue via public API
- All reads use get_connection_for_reading via public API

Research Foundation:
- User agency in automated systems
- Hybrid human-AI memory management
- Exception handling in forgetting policies
"""

import json
from typing import List, Optional, Dict, Any, Set
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from loguru import logger


@dataclass
class PinRecord:
    """Record of a pinned memory"""
    memory_id: int
    project_path: str
    pinned_at: datetime
    pinned_by: str  # 'user' or 'auto'
    reason: Optional[str] = None
    auto_pin_criteria: Optional[str] = None  # For auto-pins: what triggered it

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        data = asdict(self)
        data['pinned_at'] = data['pinned_at'].isoformat()
        return data


class MemoryPinManager:
    """
    Manages memory pinning operations

    Pinned memories:
    - Cannot be merged/consolidated
    - Cannot be dropped/deleted (except manual unpin)
    - Cannot be compressed
    - Cannot decay with age
    - Always included in relevant queries

    v2.5: Uses MemoryDatabase public API to avoid lock contention
    """

    def __init__(self, db, max_pins_per_project: int = 50):
        """
        Initialize pin manager

        Args:
            db: MemoryDatabase instance
            max_pins_per_project: Maximum pins allowed per project (default: 50)
        """
        self.db = db
        self.max_pins_per_project = max_pins_per_project

        # Ensure pinned column exists (uses public API)
        self._ensure_pin_column()

        logger.debug(f"Memory pin manager initialized (max pins: {max_pins_per_project})")

    def _ensure_pin_column(self):
        """Ensure the 'pinned' column exists in memories table"""
        try:
            # Use public API for schema check and modification
            if not self.db.check_table_column('memories', 'pinned'):
                self.db.add_column_if_missing('memories', 'pinned', 'INTEGER DEFAULT 0')
                self.db.create_index_if_missing(
                    'idx_memories_pinned',
                    "CREATE INDEX IF NOT EXISTS idx_memories_pinned ON memories(pinned) WHERE pinned = 1"
                )
                logger.info("Added 'pinned' column to memories table")
        except Exception as e:
            logger.error(f"Error ensuring pin column: {e}")

    def pin(
        self,
        memory_id: int,
        reason: Optional[str] = None,
        pinned_by: str = 'user'
    ) -> bool:
        """
        Pin a memory

        Args:
            memory_id: Memory ID to pin
            reason: Optional reason for pinning
            pinned_by: Who pinned it ('user' or 'auto')

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get memory to check if it exists and get project
            memory = self.db.get_memory_by_id(memory_id)
            if not memory:
                logger.warning(f"Cannot pin: memory {memory_id} not found")
                return False

            project_id = memory['project_id']

            # Check pin limit
            current_pins = self.db.get_pin_count(project_id)
            if current_pins >= self.max_pins_per_project:
                logger.warning(
                    f"Cannot pin: project has {current_pins}/{self.max_pins_per_project} pins"
                )
                return False

            # Check if already pinned
            if memory.get('pinned', 0) == 1:
                logger.debug(f"Memory {memory_id} is already pinned")
                return True

            # Build updated tags with pin metadata
            tags = memory.get('tags') or []
            if isinstance(tags, str):
                tags = json.loads(tags) if tags else []
            elif tags is None:
                tags = []

            pin_metadata = {
                'pinned_at': datetime.now().isoformat(),
                'pinned_by': pinned_by,
            }
            if reason:
                pin_metadata['pin_reason'] = reason

            tags.append(f"pin_metadata:{json.dumps(pin_metadata)}")

            # Pin the memory using public API
            result = self.db.set_memory_pinned(memory_id, True, json.dumps(tags))

            if result > 0:
                logger.info(f"Pinned memory {memory_id} (reason: {reason or 'none'})")
                return True
            return False

        except Exception as e:
            logger.error(f"Error pinning memory {memory_id}: {e}")
            return False

    def pin_by_path(
        self,
        file_path: str,
        project_path: str,
        reason: Optional[str] = None,
        pinned_by: str = 'user'
    ) -> bool:
        """
        Pin a memory by file path, creating a placeholder if memory doesn't exist.

        Args:
            file_path: Path to the file to pin
            project_path: Project path for context
            reason: Optional reason for pinning
            pinned_by: Who pinned it ('user' or 'auto')

        Returns:
            True if successful, False otherwise
        """
        try:
            # Look up existing memory by file path using public API
            project_id = self.db.get_or_create_project(project_path)
            memory = self.db.get_memory_by_path(project_id, file_path)

            if memory:
                # Memory exists, pin it
                memory_id = memory['id']
                logger.debug(f"Found existing memory {memory_id} for {file_path}")
                return self.pin(memory_id, reason, pinned_by)
            else:
                # No memory exists - create a placeholder using public API
                logger.info(f"No memory for {file_path}, creating placeholder")

                memory_id = self.db.create_pinned_placeholder(
                    project_id=project_id,
                    file_path=file_path,
                    verbatim=f"Pinned file: {file_path}",
                    gist="User pinned file for permanent retention",
                    salience='CRITICAL',
                    event_type='user_pinned'
                )

                logger.info(f"Created placeholder memory {memory_id} for {file_path}")

                # Add pin metadata
                return self._add_pin_metadata(memory_id, reason, pinned_by)

        except Exception as e:
            logger.error(f"Error pinning by path {file_path}: {e}")
            return False

    def _add_pin_metadata(
        self,
        memory_id: int,
        reason: Optional[str],
        pinned_by: str
    ) -> bool:
        """Add pin metadata to a memory's tags"""
        try:
            memory = self.db.get_memory_by_id(memory_id)
            if not memory:
                return False

            tags = memory.get('tags') or []
            if isinstance(tags, str):
                tags = json.loads(tags) if tags else []
            elif tags is None:
                tags = []

            pin_metadata = {
                'pinned_at': datetime.now().isoformat(),
                'pinned_by': pinned_by,
            }
            if reason:
                pin_metadata['pin_reason'] = reason

            tags.append(f"pin_metadata:{json.dumps(pin_metadata)}")

            # Update tags using public API
            result = self.db.set_memory_pinned(memory_id, True, json.dumps(tags))
            return result > 0

        except Exception as e:
            logger.error(f"Error adding pin metadata: {e}")
            return False

    def unpin(self, memory_id: int) -> bool:
        """
        Unpin a memory

        Args:
            memory_id: Memory ID to unpin

        Returns:
            True if successful, False otherwise
        """
        try:
            # Use public API to unpin
            result = self.db.set_memory_pinned(memory_id, False)

            if result > 0:
                logger.info(f"Unpinned memory {memory_id}")
                return True
            return True  # Memory might not exist, but that's not an error

        except Exception as e:
            logger.error(f"Error unpinning memory {memory_id}: {e}")
            return False

    def unpin_by_path(self, file_path: str, project_path: str) -> bool:
        """
        Unpin a memory by file path.

        Args:
            file_path: Path to the file to unpin
            project_path: Project path for context

        Returns:
            True if successful, False otherwise
        """
        try:
            # Look up memory by file path using public API
            project_id = self.db.get_or_create_project(project_path)
            memory = self.db.get_pinned_memory_by_path(project_id, file_path)

            if not memory:
                logger.debug(f"No pinned memory found for {file_path}")
                return True  # Not an error - just nothing to unpin

            return self.unpin(memory['id'])

        except Exception as e:
            logger.error(f"Error unpinning by path {file_path}: {e}")
            return False

    def is_pinned(self, memory_id: int) -> bool:
        """
        Check if a memory is pinned

        Args:
            memory_id: Memory ID to check

        Returns:
            True if pinned, False otherwise
        """
        try:
            memory = self.db.get_memory_by_id(memory_id)
            if not memory:
                return False

            return memory.get('pinned', 0) == 1

        except Exception as e:
            logger.error(f"Error checking pin status for {memory_id}: {e}")
            return False

    def get_pinned_memories(self, project_path: str) -> List[Dict[str, Any]]:
        """
        Get all pinned memories for a project

        Args:
            project_path: Project path

        Returns:
            List of pinned memory dicts
        """
        try:
            project_id = self.db.get_or_create_project(project_path)
            return self.db.get_pinned_memories(project_id)

        except Exception as e:
            logger.error(f"Error getting pinned memories: {e}")
            return []

    def get_pinned_ids(self, project_path: str) -> Set[int]:
        """
        Get set of pinned memory IDs for a project

        Args:
            project_path: Project path

        Returns:
            Set of memory IDs that are pinned
        """
        memories = self.get_pinned_memories(project_path)
        return {m['id'] for m in memories}

    def get_pin_count(self, project_id: int) -> int:
        """
        Get number of pinned memories for a project

        Args:
            project_id: Project ID

        Returns:
            Count of pinned memories
        """
        try:
            return self.db.get_pin_count(project_id)
        except Exception as e:
            logger.error(f"Error getting pin count: {e}")
            return 0

    def suggest_pins(
        self,
        project_path: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Suggest memories worth pinning

        Criteria:
        - High retention score
        - Frequently accessed
        - Resolution role
        - User-created (from CLI remember)

        Args:
            project_path: Project path
            limit: Maximum suggestions to return

        Returns:
            List of suggested memories with scores
        """
        try:
            project_id = self.db.get_or_create_project(project_path)

            # Get suggestions using public API
            candidates = self.db.get_suggested_pins(project_id, limit)

            suggestions = []
            for memory in candidates:
                suggestions.append({
                    'memory': memory,
                    'reason': self._generate_suggestion_reason(memory),
                    'confidence': self._calculate_suggestion_confidence(memory)
                })

            # Sort by confidence
            suggestions.sort(key=lambda s: s['confidence'], reverse=True)

            logger.debug(f"Generated {len(suggestions)} pin suggestions")
            return suggestions

        except Exception as e:
            logger.error(f"Error suggesting pins: {e}")
            return []

    def auto_pin_if_eligible(self, memory_id: int) -> bool:
        """
        Automatically pin memory if it meets auto-pin criteria

        Auto-pin criteria:
        - Salience = CRITICAL
        - event_type = 'user_created'
        - High retention score (>80)

        Args:
            memory_id: Memory ID to evaluate

        Returns:
            True if auto-pinned, False otherwise
        """
        try:
            memory = self.db.get_memory_by_id(memory_id)
            if not memory:
                return False

            # Check if already at pin limit
            project_id = memory['project_id']
            current_pins = self.db.get_pin_count(project_id)
            if current_pins >= self.max_pins_per_project:
                return False

            # Check auto-pin criteria
            is_critical = memory.get('salience') == 'CRITICAL'
            is_user_created = memory.get('event_type') == 'user_created'

            if is_critical or is_user_created:
                criteria = 'CRITICAL salience' if is_critical else 'user-created'
                return self.pin(
                    memory_id,
                    reason=f"Auto-pinned: {criteria}",
                    pinned_by='auto'
                )

            return False

        except Exception as e:
            logger.error(f"Error in auto-pin check: {e}")
            return False

    def _generate_suggestion_reason(self, memory: Dict[str, Any]) -> str:
        """Generate human-readable reason for pin suggestion"""
        reasons = []

        if memory.get('salience') == 'CRITICAL':
            reasons.append('Critical importance')

        if memory.get('access_count', 0) > 5:
            reasons.append(f"Accessed {memory['access_count']} times")

        if memory.get('event_type') == 'user_created':
            reasons.append('User-created memory')

        return '; '.join(reasons) if reasons else 'High value content'

    def _calculate_suggestion_confidence(self, memory: Dict[str, Any]) -> float:
        """Calculate confidence score for pin suggestion (0.0-1.0)"""
        score = 0.0

        # Salience contribution
        if memory.get('salience') == 'CRITICAL':
            score += 0.4
        elif memory.get('salience') == 'HIGH':
            score += 0.2

        # Access count contribution
        access_count = memory.get('access_count', 0)
        score += min(access_count * 0.05, 0.3)

        # Event type contribution
        if memory.get('event_type') == 'user_created':
            score += 0.3

        return min(score, 1.0)

    def get_statistics(self) -> Dict[str, Any]:
        """Get pinning statistics across all projects"""
        try:
            stats = self.db.get_pin_statistics()
            stats['max_pins_per_project'] = self.max_pins_per_project
            return stats
        except Exception as e:
            logger.error(f"Error getting pin statistics: {e}")
            return {}
