"""
Semantic Consolidation System
Batch job that consolidates related memories using semantic compression

Research Foundation:
- "The brain consolidates experiences during sleep, merging related episodes"
- "System consolidation: transformation from episodic to semantic memory"
- "Gist extraction preserves meaning while discarding surface details"

SF-V2 Enhancement:
- Intelligence-preserving compression (Cause → Fix → Result → Learning)
- Entity extraction and preservation
- Role-based analysis for smart consolidation

विस्मृति भी विद्या है (Forgetting too is knowledge)
जय विदुराई! 🕉️
"""

import os
import json
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict, field
from loguru import logger

from vidurai.core.data_structures_v3 import SalienceLevel

# SF-V2: Import new components
try:
    from vidurai.core.memory_role_classifier import MemoryRoleClassifier, MemoryRole
    from vidurai.core.entity_extractor import EntityExtractor, ExtractedEntities
    from vidurai.core.forgetting_ledger import get_ledger
    SF_V2_AVAILABLE = True
except ImportError:
    logger.warning("SF-V2 components not available, using legacy consolidation")
    SF_V2_AVAILABLE = False


@dataclass
class ConsolidationMetrics:
    """Metrics for a consolidation run"""
    run_timestamp: str
    project_path: str

    # Input stats
    memories_before: int
    tokens_before: int
    groups_processed: int

    # Output stats
    memories_after: int
    tokens_after: int
    memories_consolidated: int

    # Compression details
    compression_ratio: float
    salience_distribution_before: Dict[str, int]
    salience_distribution_after: Dict[str, int]

    # Safety
    critical_preserved: int
    high_preserved: int

    # Performance
    execution_time_seconds: float
    api_calls: int = 0
    cost_usd: float = 0.0

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class MemoryGroup:
    """Group of related memories for consolidation"""
    group_id: str
    memories: List[Dict]
    file_path: Optional[str] = None
    topic: Optional[str] = None
    time_span_days: int = 0
    total_tokens: int = 0

    def __len__(self) -> int:
        return len(self.memories)


@dataclass
class CompressedMemory:
    """
    SF-V2: Intelligence-preserving compressed memory format

    Format: Cause → Fix → Result → Learning

    Philosophy: Preserve meaning, not verbatim. Keep entities, not noise.
    """
    # Structured compression
    cause: str  # What was the problem? (root cause)
    fix: str    # What did we do? (attempted solutions + final fix)
    result: str  # What happened? (outcome)
    learning: str  # What did we learn? (pattern/principle)

    # Preserved technical details
    entities: ExtractedEntities  # MUST NEVER BE LOST

    # Metadata
    occurrence_count: int
    time_span_days: int
    first_timestamp: datetime
    last_timestamp: datetime
    file_path: Optional[str] = None
    line_number: Optional[int] = None

    # Role breakdown
    role_distribution: Dict[str, int] = field(default_factory=dict)  # {role: count}

    def to_gist(self) -> str:
        """Generate concise gist for display"""
        return f"{self.cause} → {self.fix} → {self.result}"

    def to_verbatim(self) -> str:
        """
        Generate verbatim text from compressed format

        Format:
        Cause: <cause>
        Fix: <fix>
        Result: <result>
        Learning: <learning>
        Entities: <compact entity list>
        """
        lines = [
            f"[Consolidated from {self.occurrence_count} memories over {self.time_span_days} days]",
            "",
            f"Cause: {self.cause}",
            f"Fix: {self.fix}",
            f"Result: {self.result}",
            f"Learning: {self.learning}",
            "",
            f"Technical Details: {self.entities.to_compact_string()}",
        ]

        if self.file_path:
            lines.append(f"Primary File: {self.file_path}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for storage"""
        data = {
            'cause': self.cause,
            'fix': self.fix,
            'result': self.result,
            'learning': self.learning,
            'entities': self.entities.to_dict(),
            'occurrence_count': self.occurrence_count,
            'time_span_days': self.time_span_days,
            'first_timestamp': self.first_timestamp.isoformat(),
            'last_timestamp': self.last_timestamp.isoformat(),
            'file_path': self.file_path,
            'line_number': self.line_number,
            'role_distribution': self.role_distribution,
        }
        return data


class SemanticConsolidationJob:
    """
    Periodic batch job that consolidates related memories

    Philosophy: "Sleep consolidates memories, we do too"
    """

    def __init__(
        self,
        db,  # MemoryDatabase instance
        config: Optional[Dict] = None
    ):
        """
        Initialize consolidation job

        Args:
            db: MemoryDatabase instance
            config: Configuration dict (optional, uses defaults if not provided)
        """
        self.db = db
        self.config = config or self._default_config()

        # Metrics storage
        self.metrics_dir = Path.home() / ".vidurai" / "consolidation_metrics"
        self.metrics_dir.mkdir(parents=True, exist_ok=True)

        # SF-V2: Initialize intelligent compression components
        if SF_V2_AVAILABLE:
            self.role_classifier = MemoryRoleClassifier()
            self.entity_extractor = EntityExtractor()
            self.use_smart_compression = True
            logger.info("SF-V2: Smart compression enabled")
        else:
            self.role_classifier = None
            self.entity_extractor = None
            self.use_smart_compression = False
            logger.info("SF-V2: Using legacy consolidation")

        logger.info(
            f"Semantic consolidation job initialized "
            f"(enabled: {self.config['enabled']}, "
            f"target_ratio: {self.config['target_ratio']}, "
            f"smart_compression: {self.use_smart_compression})"
        )

    def _default_config(self) -> Dict:
        """Default configuration"""
        return {
            'enabled': False,  # Safe default: disabled
            'target_ratio': 0.4,  # 60% reduction
            'min_memories_to_consolidate': 5,
            'min_salience': 'LOW',  # Only consolidate LOW/NOISE
            'max_age_days': 30,  # Only consolidate old memories
            'group_by': ['file_path'],  # Group by file
            'max_group_size': 50,
            'preserve_critical': True,
            'preserve_high': True,
            'keep_originals': False,  # Delete originals after consolidation
        }

    def run(
        self,
        project_path: str,
        dry_run: bool = False
    ) -> ConsolidationMetrics:
        """
        Run consolidation job on a project

        Args:
            project_path: Project to consolidate
            dry_run: If True, don't actually modify database

        Returns:
            ConsolidationMetrics with results
        """
        start_time = datetime.now()
        logger.info(f"Starting consolidation job for {project_path} (dry_run: {dry_run})")

        # Check if enabled
        if not self.config['enabled']:
            logger.warning("Consolidation is disabled in config")
            return self._empty_metrics(project_path, start_time)

        # Get all memories for project
        all_memories = self._get_consolidatable_memories(project_path)

        if not all_memories:
            logger.info("No memories found for consolidation")
            return self._empty_metrics(project_path, start_time)

        # Calculate initial stats
        memories_before = len(all_memories)
        tokens_before = sum(self._estimate_tokens(m['verbatim']) for m in all_memories)
        salience_before = self._count_by_salience(all_memories)

        logger.info(
            f"Found {memories_before} consolidatable memories "
            f"({tokens_before} tokens)"
        )

        # Group memories by similarity
        groups = self._group_memories(all_memories)
        logger.info(f"Grouped into {len(groups)} groups")

        # Consolidate each group
        consolidated_memories = []
        memories_removed = []

        for group in groups:
            if len(group) < self.config['min_memories_to_consolidate']:
                logger.debug(f"Skipping group {group.group_id}: too few memories ({len(group)})")
                continue

            # Create consolidated memory
            consolidated = self._consolidate_group(group)

            if consolidated:
                consolidated_memories.append(consolidated)
                memories_removed.extend([m['id'] for m in group.memories])
                logger.debug(
                    f"Consolidated {len(group)} memories into 1 "
                    f"(group: {group.group_id})"
                )

        # Apply changes to database (if not dry run)
        if not dry_run and consolidated_memories:
            self._apply_consolidation(
                project_path,
                consolidated_memories,
                memories_removed
            )
            logger.info(
                f"Applied consolidation: {len(consolidated_memories)} new, "
                f"{len(memories_removed)} removed"
            )

        # Calculate final stats
        memories_after = memories_before - len(memories_removed) + len(consolidated_memories)
        tokens_after = (
            tokens_before -
            sum(self._estimate_tokens(self.db.get_memory_by_id(mid)['verbatim'])
                for mid in memories_removed if self.db.get_memory_by_id(mid)) +
            sum(self._estimate_tokens(m['verbatim']) for m in consolidated_memories)
        )

        # Count preserved critical/high
        critical_preserved = salience_before.get('CRITICAL', 0)
        high_preserved = salience_before.get('HIGH', 0)

        # Build metrics
        execution_time = (datetime.now() - start_time).total_seconds()
        compression_ratio = 1.0 - (tokens_after / tokens_before) if tokens_before > 0 else 0.0

        metrics = ConsolidationMetrics(
            run_timestamp=start_time.isoformat(),
            project_path=project_path,
            memories_before=memories_before,
            tokens_before=tokens_before,
            groups_processed=len(groups),
            memories_after=memories_after,
            tokens_after=tokens_after,
            memories_consolidated=len(consolidated_memories),
            compression_ratio=compression_ratio,
            salience_distribution_before=salience_before,
            salience_distribution_after=self._count_by_salience(
                [m for m in all_memories if m['id'] not in memories_removed] +
                consolidated_memories
            ),
            critical_preserved=critical_preserved,
            high_preserved=high_preserved,
            execution_time_seconds=execution_time,
        )

        # Save metrics
        self._save_metrics(metrics)

        # SF-V2: Log to forgetting ledger (if not dry run)
        if not dry_run and SF_V2_AVAILABLE and consolidated_memories:
            try:
                ledger = get_ledger()

                # Count preserved entities and roles
                entities_preserved = 0
                root_causes_preserved = 0
                resolutions_preserved = 0

                for memory in consolidated_memories:
                    tags = memory.get('tags', '[]')
                    if isinstance(tags, str):
                        tags = json.loads(tags)

                    # Extract entity count from tags
                    for tag in tags:
                        if tag.startswith('entities_preserved:'):
                            entities_preserved += int(tag.split(':')[1])
                        elif tag.startswith('roles:'):
                            roles_json = tag.split(':', 1)[1]
                            roles = json.loads(roles_json)
                            root_causes_preserved += roles.get('cause', 0)
                            resolutions_preserved += roles.get('resolution', 0)

                # Log consolidation event
                ledger.log_consolidation(
                    project_path=project_path,
                    memories_before=memories_before,
                    memories_after=memories_after,
                    memories_removed=memories_removed,
                    consolidated_into=[],  # IDs not available at this point
                    entities_preserved=entities_preserved,
                    root_causes_preserved=root_causes_preserved,
                    resolutions_preserved=resolutions_preserved,
                    action='compress_aggressive' if compression_ratio > 0.5 else 'compress_light',
                    reason=f"Consolidation job: {len(groups)} groups processed",
                    policy='semantic_consolidation'
                )

                logger.debug(f"Logged consolidation event to forgetting ledger")

            except Exception as e:
                logger.error(f"Error logging to forgetting ledger: {e}")

        logger.info(
            f"Consolidation complete: {memories_before} → {memories_after} memories, "
            f"{compression_ratio:.1%} compression, {execution_time:.1f}s"
        )

        return metrics

    def _get_consolidatable_memories(self, project_path: str) -> List[Dict]:
        """
        Get memories eligible for consolidation

        Filters:
        - Salience <= min_salience (LOW/NOISE by default)
        - Age >= max_age_days (old memories only)
        - Not already consolidated
        """
        try:
            # Get project ID
            project_id = self.db.get_or_create_project(project_path)

            # Query database
            cursor = self.db.conn.cursor()

            # Build query
            min_salience = self.config['min_salience']
            max_age_days = self.config['max_age_days']

            # Salience filter
            salience_levels = []
            if min_salience == 'NOISE':
                salience_levels = ['NOISE']
            elif min_salience == 'LOW':
                salience_levels = ['NOISE', 'LOW']
            elif min_salience == 'MEDIUM':
                salience_levels = ['NOISE', 'LOW', 'MEDIUM']

            placeholders = ','.join('?' * len(salience_levels))

            sql = f"""
                SELECT
                    id, verbatim, gist, salience, event_type,
                    file_path, line_number, tags,
                    created_at, access_count
                FROM memories
                WHERE project_id = ?
                    AND salience IN ({placeholders})
                    AND created_at <= datetime('now', '-{max_age_days} days')
                    AND (tags IS NULL OR tags NOT LIKE '%consolidated%')
                ORDER BY file_path, created_at
            """

            params = [project_id] + salience_levels
            cursor.execute(sql, params)

            results = cursor.fetchall()
            memories = [dict(row) for row in results]

            return memories

        except Exception as e:
            logger.error(f"Error getting consolidatable memories: {e}")
            return []

    def _group_memories(self, memories: List[Dict]) -> List[MemoryGroup]:
        """
        Group memories by similarity

        Groups by: file_path (and optionally topic in future)
        """
        groups = {}
        group_by = self.config['group_by']

        for memory in memories:
            # Build group key
            key_parts = []

            if 'file_path' in group_by:
                file_path = memory.get('file_path') or 'unknown'
                key_parts.append(f"file:{file_path}")

            group_key = "|".join(key_parts) if key_parts else "default"

            # Add to group
            if group_key not in groups:
                groups[group_key] = []

            groups[group_key].append(memory)

        # Convert to MemoryGroup objects
        memory_groups = []
        for group_id, group_memories in groups.items():
            # Calculate time span
            if group_memories:
                dates = [
                    datetime.fromisoformat(m['created_at'])
                    for m in group_memories
                ]
                time_span = (max(dates) - min(dates)).days
            else:
                time_span = 0

            # Calculate total tokens
            total_tokens = sum(
                self._estimate_tokens(m['verbatim'])
                for m in group_memories
            )

            # Extract file path
            file_path = group_memories[0].get('file_path') if group_memories else None

            memory_groups.append(MemoryGroup(
                group_id=group_id,
                memories=group_memories,
                file_path=file_path,
                time_span_days=time_span,
                total_tokens=total_tokens
            ))

        # Sort by size (largest first)
        memory_groups.sort(key=lambda g: len(g.memories), reverse=True)

        return memory_groups

    def _consolidate_group(self, group: MemoryGroup) -> Optional[Dict]:
        """
        Consolidate a group of memories into a single summary

        SF-V2: Intelligence-preserving compression (Cause → Fix → Result → Learning)
        Legacy: Simple text-based consolidation
        """
        if not group.memories:
            return None

        # Use smart compression if available
        if self.use_smart_compression:
            return self._smart_consolidate_group(group)
        else:
            return self._legacy_consolidate_group(group)

    def _smart_consolidate_group(self, group: MemoryGroup) -> Optional[Dict]:
        """
        SF-V2: Intelligence-preserving compression

        Steps:
        1. Classify role for each memory (cause/attempted_fix/resolution/context/noise)
        2. Extract entities from all memories
        3. Identify cause, attempted fixes, and resolution
        4. Synthesize Cause → Fix → Result → Learning format
        5. Preserve all entities
        """
        if not group.memories:
            return None

        # Step 1: Classify roles for all memories
        role_results = {}
        role_distribution = {}

        for memory in group.memories:
            result = self.role_classifier.classify(
                verbatim=memory['verbatim'],
                gist=memory.get('gist'),
                metadata={'event_type': memory.get('event_type')}
            )
            role_results[memory['id']] = result
            role_distribution[result.role.value] = role_distribution.get(result.role.value, 0) + 1

        # Step 2: Extract entities from all memories
        all_entities = ExtractedEntities()
        for memory in group.memories:
            entities = self.entity_extractor.extract(memory['verbatim'])
            all_entities = all_entities.merge(entities)

        # Step 3: Identify key memories by role
        cause_memories = [m for m in group.memories if role_results[m['id']].role == MemoryRole.CAUSE]
        attempted_fix_memories = [m for m in group.memories if role_results[m['id']].role == MemoryRole.ATTEMPTED_FIX]
        resolution_memories = [m for m in group.memories if role_results[m['id']].role == MemoryRole.RESOLUTION]
        context_memories = [m for m in group.memories if role_results[m['id']].role == MemoryRole.CONTEXT]

        # Step 4: Synthesize compressed format
        # Cause: Use first CAUSE memory, or infer from errors
        if cause_memories:
            cause = self._extract_cause(cause_memories[0])
        elif all_entities.error_types:
            cause = f"Recurring issue: {', '.join(all_entities.error_types[:3])}"
        else:
            cause = f"Issue in {group.file_path or 'codebase'}"

        # Fix: Combine attempted fixes + resolution
        fix_parts = []
        if attempted_fix_memories:
            # Summarize attempts
            fix_parts.append(f"Tried {len(attempted_fix_memories)} approaches")
        if resolution_memories:
            # Use actual resolution
            fix_parts.append(self._extract_fix(resolution_memories[-1]))  # Last resolution
        else:
            fix_parts.append("No clear resolution recorded")

        fix = "; ".join(fix_parts)

        # Result: Check if resolved
        if resolution_memories:
            result = self._extract_result(resolution_memories[-1])
        else:
            result = "Ongoing/unresolved"

        # Learning: Extract pattern or principle
        learning = self._extract_learning(group.memories, role_results, all_entities)

        # Step 5: Create CompressedMemory
        first_date = datetime.fromisoformat(group.memories[0]['created_at'])
        last_date = datetime.fromisoformat(group.memories[-1]['created_at'])

        compressed = CompressedMemory(
            cause=cause,
            fix=fix,
            result=result,
            learning=learning,
            entities=all_entities,
            occurrence_count=len(group.memories),
            time_span_days=group.time_span_days,
            first_timestamp=first_date,
            last_timestamp=last_date,
            file_path=group.file_path,
            line_number=group.memories[0].get('line_number'),
            role_distribution=role_distribution
        )

        # Convert to dict for database storage
        consolidated = {
            'verbatim': compressed.to_verbatim(),
            'gist': compressed.to_gist(),
            'salience': 'LOW',  # Consolidated memories are LOW salience
            'event_type': group.memories[0]['event_type'],
            'file_path': group.file_path,
            'line_number': group.memories[0].get('line_number'),
            'tags': json.dumps([
                'consolidated',
                'sf_v2_compressed',
                f'occurrences:{len(group.memories)}',
                f'time_span_days:{group.time_span_days}',
                f'first:{first_date.isoformat()}',
                f'last:{last_date.isoformat()}',
                f'entities_preserved:{all_entities.count()}',
                f'roles:{json.dumps(role_distribution)}'
            ]),
        }

        logger.debug(
            f"Smart compression: {len(group.memories)} memories → "
            f"Cause/Fix/Result/Learning + {all_entities.count()} entities"
        )

        return consolidated

    def _legacy_consolidate_group(self, group: MemoryGroup) -> Optional[Dict]:
        """
        Legacy consolidation (pre-SF-V2)

        Simple text-based compression without role classification
        """
        if not group.memories:
            return None

        # Extract key information
        first_memory = group.memories[0]
        last_memory = group.memories[-1]

        # Count occurrences
        occurrence_count = len(group.memories)

        # Get date range
        first_date = datetime.fromisoformat(first_memory['created_at'])
        last_date = datetime.fromisoformat(last_memory['created_at'])

        # Build consolidated gist
        base_gist = first_memory['gist']

        # Create summary
        if group.time_span_days > 0:
            time_text = f"{group.time_span_days} day{'s' if group.time_span_days > 1 else ''}"
        else:
            time_text = "same day"

        consolidated_gist = (
            f"{base_gist} "
            f"(consolidated: ×{occurrence_count} occurrences over {time_text})"
        )

        # Build consolidated verbatim (first + last for context)
        consolidated_verbatim = (
            f"[Consolidated from {occurrence_count} memories]\n"
            f"First: {first_memory['verbatim'][:100]}\n"
            f"Last: {last_memory['verbatim'][:100]}"
        )

        # Preserve metadata
        consolidated = {
            'verbatim': consolidated_verbatim,
            'gist': consolidated_gist,
            'salience': 'LOW',  # Consolidated memories are LOW salience
            'event_type': first_memory['event_type'],
            'file_path': first_memory.get('file_path'),
            'line_number': first_memory.get('line_number'),
            'tags': json.dumps([
                'consolidated',
                f'occurrences:{occurrence_count}',
                f'time_span_days:{group.time_span_days}',
                f'first:{first_date.isoformat()}',
                f'last:{last_date.isoformat()}'
            ]),
        }

        return consolidated

    def _extract_cause(self, memory: Dict[str, Any]) -> str:
        """Extract cause from a CAUSE-classified memory"""
        text = memory['verbatim']

        # Try to extract root cause sentence
        lines = text.split('\n')
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in ['root cause', 'issue is', 'problem is', 'caused by']):
                return line.strip()

        # Fallback: use gist or first line
        return memory.get('gist') or lines[0][:100]

    def _extract_fix(self, memory: Dict[str, Any]) -> str:
        """Extract fix from a RESOLUTION-classified memory"""
        text = memory['verbatim']

        # Try to extract fix sentence
        lines = text.split('\n')
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in ['fixed', 'solved', 'solution was', 'the fix']):
                return line.strip()

        # Fallback: use gist or first line
        return memory.get('gist') or lines[0][:100]

    def _extract_result(self, memory: Dict[str, Any]) -> str:
        """Extract result from a RESOLUTION-classified memory"""
        text = memory['verbatim']

        # Look for result indicators
        lines = text.split('\n')
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in ['working now', 'tests pass', 'deployed', 'confirmed']):
                return line.strip()

        # Default: Fixed
        return "Fixed"

    def _extract_learning(
        self,
        memories: List[Dict[str, Any]],
        role_results: Dict[int, Any],
        entities: ExtractedEntities
    ) -> str:
        """
        Extract learning/pattern from consolidated memories

        Returns a principle or pattern learned from this episode
        """
        # Check if there's a clear pattern
        if len(memories) >= 10:
            # Recurring issue
            return f"Watch for similar issues in {entities.file_paths[0] if entities.file_paths else 'codebase'}"

        # Check for resolution
        resolution_count = sum(1 for m in memories if role_results[m['id']].role == MemoryRole.RESOLUTION)
        if resolution_count > 0:
            return "Solution verified and working"

        # Check for common error type
        if entities.error_types:
            error_type = entities.error_types[0]
            return f"Common {error_type} pattern - investigate carefully"

        # Default
        return "Monitor for recurrence"

    def _apply_consolidation(
        self,
        project_path: str,
        consolidated_memories: List[Dict],
        memory_ids_to_remove: List[int]
    ):
        """Apply consolidation changes to database"""
        try:
            project_id = self.db.get_or_create_project(project_path)
            cursor = self.db.conn.cursor()

            # Store consolidated memories
            for memory in consolidated_memories:
                from vidurai.storage.database import SalienceLevel as DBSalienceLevel

                self.db.store_memory(
                    project_path=project_path,
                    verbatim=memory['verbatim'],
                    gist=memory['gist'],
                    salience=DBSalienceLevel[memory['salience']],
                    event_type=memory['event_type'],
                    file_path=memory.get('file_path'),
                    line_number=memory.get('line_number'),
                    tags=json.loads(memory['tags']) if isinstance(memory['tags'], str) else memory['tags'],
                    retention_days=7  # Consolidated memories have short retention
                )

            # Remove original memories (if configured)
            if not self.config['keep_originals'] and memory_ids_to_remove:
                placeholders = ','.join('?' * len(memory_ids_to_remove))
                cursor.execute(
                    f"DELETE FROM memories WHERE id IN ({placeholders})",
                    memory_ids_to_remove
                )

                # Also delete from FTS
                cursor.execute(
                    f"DELETE FROM memories_fts WHERE memory_id IN ({placeholders})",
                    memory_ids_to_remove
                )

            self.db.conn.commit()
            logger.debug(
                f"Applied consolidation: {len(consolidated_memories)} stored, "
                f"{len(memory_ids_to_remove)} removed"
            )

        except Exception as e:
            logger.error(f"Error applying consolidation: {e}")
            self.db.conn.rollback()

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation: ~4 chars per token"""
        return len(text) // 4

    def _count_by_salience(self, memories: List[Dict]) -> Dict[str, int]:
        """Count memories by salience level"""
        counts = {}
        for memory in memories:
            salience = memory.get('salience', 'UNKNOWN')
            counts[salience] = counts.get(salience, 0) + 1
        return counts

    def _empty_metrics(
        self,
        project_path: str,
        start_time: datetime
    ) -> ConsolidationMetrics:
        """Create empty metrics (when nothing to consolidate)"""
        return ConsolidationMetrics(
            run_timestamp=start_time.isoformat(),
            project_path=project_path,
            memories_before=0,
            tokens_before=0,
            groups_processed=0,
            memories_after=0,
            tokens_after=0,
            memories_consolidated=0,
            compression_ratio=0.0,
            salience_distribution_before={},
            salience_distribution_after={},
            critical_preserved=0,
            high_preserved=0,
            execution_time_seconds=0.0,
        )

    def _save_metrics(self, metrics: ConsolidationMetrics):
        """Save metrics to JSONL file"""
        try:
            metrics_file = self.metrics_dir / "consolidation_metrics.jsonl"

            with open(metrics_file, 'a') as f:
                f.write(json.dumps(metrics.to_dict()) + '\n')

            logger.debug(f"Metrics saved to {metrics_file}")

        except Exception as e:
            logger.error(f"Error saving metrics: {e}")

    def get_recent_metrics(self, limit: int = 10) -> List[Dict]:
        """Get recent consolidation metrics"""
        try:
            metrics_file = self.metrics_dir / "consolidation_metrics.jsonl"

            if not metrics_file.exists():
                return []

            metrics = []
            with open(metrics_file, 'r') as f:
                for line in f:
                    metrics.append(json.loads(line))

            # Return most recent
            return metrics[-limit:]

        except Exception as e:
            logger.error(f"Error reading metrics: {e}")
            return []
