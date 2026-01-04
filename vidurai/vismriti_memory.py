"""
VismritiMemory - Intelligent Forgetting Memory System

The complete Vismriti Architecture implementation integrating:
- Phase 1: Gist/Verbatim Split (Fuzzy-Trace Theory)
- Phase 2: Salience Tagging (Dopamine-mediated)
- Phase 3A: Passive Decay (Synaptic Pruning)
- Phase 3B: Active Unlearning (Motivated Forgetting)
- Phase 4: Memory Ledger (Transparency)

Research Foundation: 104+ citations across neuroscience, AI, philosophy

विस्मृति भी विद्या है (Forgetting too is knowledge)
जय विदुराई! 🕉️
"""

import os
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path
from loguru import logger

from vidurai.core.data_structures_v3 import Memory, SalienceLevel, MemoryStatus
from vidurai.core.salience_classifier import SalienceClassifier
from vidurai.core.passive_decay import PassiveDecayEngine
from vidurai.core.active_unlearning import ActiveUnlearningEngine
from vidurai.core.memory_ledger import MemoryLedger

# Smart Query Sanitization: Stop words to filter out
# These common words add noise to searches and should be removed
STOP_WORDS = frozenset({
    # Question words
    "what", "which", "who", "whom", "whose", "where", "when", "why", "how",
    # Articles
    "a", "an", "the",
    # Prepositions
    "of", "in", "to", "for", "with", "on", "at", "from", "by", "about",
    "into", "through", "during", "before", "after", "above", "below",
    "between", "under", "over",
    # Conjunctions
    "and", "or", "but", "nor", "so", "yet",
    # Pronouns
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves",
    "you", "your", "yours", "yourself", "yourselves",
    "he", "him", "his", "himself", "she", "her", "hers", "herself",
    "it", "its", "itself", "they", "them", "their", "theirs", "themselves",
    # Common verbs
    "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "having", "do", "does", "did", "doing",
    "will", "would", "could", "should", "may", "might", "must", "shall",
    "can", "need", "dare", "ought", "used",
    # Common words
    "this", "that", "these", "those", "there", "here",
    "all", "each", "every", "both", "few", "more", "most", "other",
    "some", "such", "no", "not", "only", "own", "same", "than", "too",
    "very", "just", "also", "now", "then",
    # Project-related noise
    "project", "file", "code", "function", "class", "method",
    "tell", "show", "explain", "describe", "give", "find", "get",
})

# Phase 6: Event Bus integration
try:
    from vidurai.core.event_bus import EventBus, publish_event
    EVENT_BUS_AVAILABLE = True
except Exception:
    EVENT_BUS_AVAILABLE = False
    logger.warning("EventBus unavailable, event publishing disabled")

# v2.0: SQLite database backend
try:
    from vidurai.storage.database import MemoryDatabase, SalienceLevel as DBSalienceLevel
    DATABASE_AVAILABLE = True
except Exception:
    DATABASE_AVAILABLE = False
    logger.warning("Database storage unavailable, using in-memory only")

# Optional gist extraction (requires OpenAI API key)
try:
    from vidurai.core.gist_extractor import GistExtractor
    GIST_EXTRACTION_AVAILABLE = True
except Exception:
    GIST_EXTRACTION_AVAILABLE = False
    logger.warning("Gist extraction unavailable (OpenAI API key not set)")

# Optional RL agent integration
try:
    from vidurai.core.rl_agent_v2 import VismritiRLAgent, RewardProfile
    RL_AGENT_AVAILABLE = True
except Exception:
    RL_AGENT_AVAILABLE = False
    RewardProfile = None
    logger.warning("RL Agent unavailable")

# Memory aggregation (v2.0: Forgetting reform)
try:
    from vidurai.core.memory_aggregator import MemoryAggregator
    AGGREGATION_AVAILABLE = True
except Exception:
    AGGREGATION_AVAILABLE = False
    logger.warning("Memory aggregation unavailable")

# Semantic consolidation (v2.0: Batch compression)
try:
    from vidurai.core.semantic_consolidation import SemanticConsolidationJob
    from vidurai.config.compression_config import load_compression_config
    CONSOLIDATION_AVAILABLE = True
except Exception:
    CONSOLIDATION_AVAILABLE = False
    logger.warning("Semantic consolidation unavailable")

# Retention policies (v2.0: RL-driven decision layer)
try:
    from vidurai.core.retention_policy import (
        RetentionPolicy, RuleBasedPolicy, RLPolicy,
        create_retention_policy, RetentionContext, RetentionOutcome, RetentionAction
    )
    RETENTION_POLICY_AVAILABLE = True
except Exception:
    RETENTION_POLICY_AVAILABLE = False
    logger.warning("Retention policy layer unavailable")

# Multi-audience gist generation (Phase 5: Audience-Specific Memory Gisting)
try:
    from vidurai.core.multi_audience_gist import MultiAudienceGistGenerator
    from vidurai.config.multi_audience_config import MultiAudienceConfig
    MULTI_AUDIENCE_AVAILABLE = True
except Exception:
    MULTI_AUDIENCE_AVAILABLE = False
    logger.warning("Multi-audience gist generation unavailable")


class VismritiMemory:
    """
    Vismriti Memory System - Intelligent Forgetting Architecture

    Research: "Forgetting is not a void; it is an active and intelligent process"

    Features:
    - Dual-trace memory (verbatim + gist)
    - Categorical salience (dopamine-inspired)
    - Differential decay (verbatim faster than gist)
    - Active unlearning (gradient ascent)
    - Complete transparency (memory ledger)

    Usage:
        >>> memory = VismritiMemory()
        >>> memory.remember("Fixed auth bug in auth.py", metadata={"solved_bug": True})
        >>> memories = memory.recall("auth bug")
        >>> ledger = memory.get_ledger()
        >>> memory.forget("temporary test data")
    """

    def __init__(
        self,
        enable_decay: bool = True,
        enable_gist_extraction: bool = False,
        enable_rl_agent: bool = False,
        enable_aggregation: bool = True,  # NEW: Enable by default
        retention_policy: str = "rule_based",  # NEW: "rule_based" or "rl_based"
        retention_policy_config: Optional[Dict[str, Any]] = None,  # NEW: Policy config
        enable_multi_audience: bool = False,  # Phase 5: Enable multi-audience gists
        multi_audience_config: Optional[Dict[str, Any]] = None,  # Phase 5: Custom config
        project_path: Optional[str] = None
    ):
        """
        Initialize VismritiMemory system

        Args:
            enable_decay: Enable passive decay (default: True)
            enable_gist_extraction: Extract gist from verbatim (default: False, requires OpenAI key)
            enable_rl_agent: Enable RL agent integration (default: False)
            enable_aggregation: Enable memory aggregation (default: True) - NEW
            retention_policy: Retention policy type: "rule_based" or "rl_based" (default: "rule_based") - NEW
            retention_policy_config: Configuration for retention policy (default: None) - NEW
            enable_multi_audience: Enable multi-audience gist generation (default: False) - Phase 5
            multi_audience_config: Custom configuration for multi-audience (default: None) - Phase 5
            project_path: Project path for persistent storage (default: current directory)
        """

        # [CTO Mandate] Force canonical absolute path to prevent split-brain projects
        # This is the SINGLE SOURCE OF TRUTH for path normalization
        # All paths like '.', './', '../foo', 'relative/path' become absolute
        raw_path = project_path or os.getcwd()
        self._project_path = os.path.abspath(raw_path)
        self._project_id: Optional[int] = None  # Lazy-loaded, refreshed on path change

        # Core components (in-memory cache for backward compatibility)
        self.memories: List[Memory] = []

        # v2.0: SQLite database backend
        self.db = None
        if DATABASE_AVAILABLE:
            try:
                self.db = MemoryDatabase()
                # Initialize project_id now that db is available
                self._project_id = self.db.get_or_create_project(self._project_path)
                logger.info(f"Database backend initialized for project: {self._project_path}")
            except Exception as e:
                logger.warning(f"Failed to initialize database: {e}, using in-memory only")

        # v2.0: Memory aggregation system
        self.aggregator = None
        if enable_aggregation and AGGREGATION_AVAILABLE:
            self.aggregator = MemoryAggregator(aggregation_window=7)  # 7 days
            logger.info("Memory aggregation enabled")

        # v2.0: Retention policy layer (rule-based or RL-based)
        self.retention_policy = None
        if RETENTION_POLICY_AVAILABLE:
            try:
                policy_config = retention_policy_config or {}
                self.retention_policy = create_retention_policy(
                    policy_type=retention_policy,
                    **policy_config
                )
                logger.info(f"Retention policy initialized: {self.retention_policy.name}")
            except Exception as e:
                logger.warning(f"Failed to initialize retention policy: {e}, retention decisions disabled")

        # Phase 5: Multi-Audience Gist Generation
        self.multi_audience_generator = None
        self.multi_audience_config = None
        if enable_multi_audience and MULTI_AUDIENCE_AVAILABLE:
            try:
                # Create config from dict or use defaults
                if multi_audience_config:
                    self.multi_audience_config = MultiAudienceConfig(**multi_audience_config)
                else:
                    self.multi_audience_config = MultiAudienceConfig(enabled=True)

                # Create generator
                self.multi_audience_generator = MultiAudienceGistGenerator(
                    config=self.multi_audience_config
                )
                logger.info(
                    f"Multi-audience gist generation enabled: "
                    f"audiences={self.multi_audience_config.audiences}"
                )
            except Exception as e:
                logger.warning(f"Failed to initialize multi-audience generator: {e}")

        # Phase 1: Gist Extraction (optional)
        self.enable_gist_extraction = enable_gist_extraction and GIST_EXTRACTION_AVAILABLE
        if self.enable_gist_extraction:
            self.gist_extractor = GistExtractor(model="gpt-4o-mini")
        else:
            self.gist_extractor = None

        # Phase 2: Salience Classification
        self.salience_classifier = SalienceClassifier()

        # Phase 3A: Passive Decay
        self.decay_engine = PassiveDecayEngine(enable_decay=enable_decay)

        # Phase 3B: Active Unlearning
        if enable_rl_agent and RL_AGENT_AVAILABLE:
            self.rl_agent = VismritiRLAgent(reward_profile=RewardProfile.QUALITY_FOCUSED)
        else:
            self.rl_agent = None

        self.unlearning_engine = ActiveUnlearningEngine(self.rl_agent)

        # Configuration
        self.enable_decay = enable_decay

        logger.info(
            f"VismritiMemory initialized: "
            f"gist={self.enable_gist_extraction}, decay={enable_decay}, "
            f"rl_agent={self.rl_agent is not None}, "
            f"aggregation={self.aggregator is not None}, "
            f"multi_audience={self.multi_audience_generator is not None}"
        )

    # -------------------------------------------------------------------------
    # v2.5: Project Identity Properties (Auto-refresh on context switch)
    # -------------------------------------------------------------------------

    @property
    def project_path(self) -> str:
        """Get current project path"""
        return self._project_path

    @project_path.setter
    def project_path(self, value: str) -> None:
        """
        Set project path and auto-refresh project_id.

        This is the CRITICAL FIX for context switching:
        When daemon switches projects, setting this property
        automatically updates the project_id in the database.

        [CTO Mandate] Also canonicalizes path to prevent split-brain.
        """
        # [CTO Mandate] Force canonical absolute path
        canonical_path = os.path.abspath(value)
        self._project_path = canonical_path
        # AUTO-REFRESH ID: Ensure we read/write to correct project
        if self.db:
            self._project_id = self.db.get_or_create_project(canonical_path)
            logger.debug(f"Project context switched: {canonical_path} (ID: {self._project_id})")

    @property
    def project_id(self) -> Optional[int]:
        """
        Get current project ID (lazy-loaded).

        Returns the cached project_id, or fetches it if not set.
        """
        if self._project_id is None and self.db:
            self._project_id = self.db.get_or_create_project(self._project_path)
        return self._project_id

    def _sanitize_query(self, query: str) -> List[str]:
        """
        Sanitize query for intersection search.

        CTO Mandate: The Intersection Rule
        - Lowercase the query
        - Split into tokens
        - Remove stop words
        - Return list of meaningful keywords

        Args:
            query: Raw user query (e.g., "What was the architecture of project civi")

        Returns:
            List of keywords (e.g., ["architecture", "civi"])

        Example:
            >>> self._sanitize_query("What was the architecture of project civi")
            ['architecture', 'civi']
        """
        if not query:
            return []

        # Lowercase and split on whitespace/punctuation
        import re
        tokens = re.split(r'[\s\-_.,;:!?"\'/\\()[\]{}]+', query.lower())

        # Filter out stop words and empty tokens
        keywords = [
            token for token in tokens
            if token and token not in STOP_WORDS and len(token) > 1
        ]

        logger.debug(f"Query sanitized: '{query}' -> {keywords}")
        return keywords

    def remember(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        salience: Optional[SalienceLevel] = None,
        extract_gist: bool = True,
        created_at: Optional[datetime] = None  # Sprint 1.5: Allow historical timestamps
    ) -> Memory:
        """
        Store a new memory with intelligent processing

        Process:
        1. Split into verbatim + gist (if extraction enabled)
        2. Classify salience (dopamine-tagging simulation)
        3. Create Memory object
        4. Store in memory list

        Research: "All incoming data is immediately split into two
        independent representations: verbatim and gist"

        Args:
            content: Raw content to remember
            metadata: Additional context
            salience: Override salience classification (optional)
            extract_gist: Extract gist from content (default: True)
            created_at: Optional historical timestamp for ingested memories (Sprint 1.5)
                       If None, current time is used. This enables ingestion of
                       historical ChatGPT conversations with preserved timestamps.

        Returns:
            Created Memory object

        Example:
            >>> memory.remember(
            ...     "Fixed authentication bug in auth.py",
            ...     metadata={"type": "bugfix", "file": "auth.py"}
            ... )

            # Sprint 1.5: Ingestion with historical timestamp
            >>> from datetime import datetime
            >>> memory.remember(
            ...     "User asked about authentication",
            ...     metadata={"type": "chatgpt_import", "source": "openai_export"},
            ...     created_at=datetime(2024, 6, 15, 10, 30, 0)
            ... )
        """

        metadata = metadata or {}

        # Phase 1: Gist/Verbatim Split
        verbatim = content

        if self.enable_gist_extraction and extract_gist and self.gist_extractor:
            try:
                gist = self.gist_extractor.extract(verbatim, context=metadata)
            except Exception as e:
                logger.warning(f"Gist extraction failed: {e}, using verbatim as gist")
                gist = verbatim[:100]  # Fallback: truncate verbatim
        else:
            gist = verbatim  # No extraction, gist = verbatim

        # Create memory object
        memory = Memory(
            verbatim=verbatim,
            gist=gist,
            metadata=metadata
        )

        # Phase 2: Salience Classification
        if salience:
            memory.salience = salience  # User override
        else:
            memory.salience = self.salience_classifier.classify(memory)

        # Store in-memory (for backward compatibility)
        self.memories.append(memory)

        # v2.0: Check for aggregation BEFORE storing to database
        should_aggregate = False
        aggregated = None
        matching_memory_id = None

        if self.aggregator and self.db:
            try:
                # Get recent similar memories
                recent_memories = self.db.get_recent_similar_memories(
                    project_path=self.project_path,
                    file_path=metadata.get('file'),
                    event_type=metadata.get('type', 'generic'),
                    hours_back=168  # 7 days
                )

                # Check if this should be aggregated
                should_aggregate, matching_memory = self.aggregator.should_aggregate(
                    memory, recent_memories
                )

                if should_aggregate:
                    # Create or update aggregation
                    aggregated = self.aggregator.aggregate(memory, matching_memory)

                    # Update salience based on repetition
                    memory.salience = aggregated.get_adjusted_salience()

                    # Use aggregated gist
                    gist = aggregated.to_summary_gist()

                    # Get matching memory ID for update (if exists)
                    if matching_memory:
                        matching_memory_id = matching_memory.get('id')

                    logger.info(
                        f"Aggregated memory: {aggregated.occurrence_count} occurrences, "
                        f"salience adjusted to {memory.salience.name}"
                    )

            except Exception as e:
                logger.error(f"Aggregation failed: {e}, storing normally")
                should_aggregate = False

        # v2.0: Store or update in database
        if self.db:
            try:
                # Map SalienceLevel to DBSalienceLevel
                db_salience = DBSalienceLevel[memory.salience.name]

                # Determine retention based on salience
                retention_days = {
                    DBSalienceLevel.CRITICAL: None,  # Never expire
                    DBSalienceLevel.HIGH: 90,
                    DBSalienceLevel.MEDIUM: 30,
                    DBSalienceLevel.LOW: 7,
                    DBSalienceLevel.NOISE: 1
                }.get(db_salience, 30)

                # Get tags (include aggregation metadata if applicable)
                tags = metadata.get('tags', [])
                if aggregated:
                    agg_metadata = self.aggregator.get_storage_metadata(aggregated)
                    tags = agg_metadata['tags']

                # Update existing memory if aggregated, otherwise create new
                memory_id = None
                if should_aggregate and matching_memory_id:
                    # Update existing memory with new aggregated data
                    self.db.update_memory_aggregation(
                        memory_id=matching_memory_id,
                        new_gist=gist,
                        new_salience=db_salience.name,
                        occurrence_count=aggregated.occurrence_count,
                        tags=tags
                    )
                    memory_id = matching_memory_id
                else:
                    # Store new memory (Sprint 1.5: with optional created_at)
                    memory_id = self.db.store_memory(
                        project_path=self.project_path,
                        verbatim=verbatim,
                        gist=gist,
                        salience=db_salience,
                        event_type=metadata.get('type', 'generic'),
                        file_path=metadata.get('file'),
                        line_number=metadata.get('line'),
                        tags=tags,
                        retention_days=retention_days,
                        created_at=created_at  # Sprint 1.5: Historical timestamp support
                    )

                # Phase 5: Generate and store audience-specific gists
                if self.multi_audience_generator and memory_id:
                    try:
                        # Build context for gist generation
                        gist_context = {
                            'event_type': metadata.get('type', 'generic'),
                            'file_path': metadata.get('file'),
                            'file': metadata.get('file'),
                            'line_number': metadata.get('line'),
                            'line': metadata.get('line'),
                            'salience': memory.salience.name,
                        }

                        # Generate audience-specific gists
                        audience_gists = self.multi_audience_generator.generate(
                            verbatim=verbatim,
                            canonical_gist=gist,
                            context=gist_context
                        )

                        # Store in database
                        self.db.store_audience_gists(memory_id, audience_gists)

                        logger.debug(
                            f"Generated {len(audience_gists)} audience gists: "
                            f"{list(audience_gists.keys())}"
                        )

                    except Exception as e:
                        logger.error(f"Failed to generate/store audience gists: {e}")

            except Exception as e:
                logger.error(f"Failed to store in database: {e}")

        logger.debug(
            f"Memory stored: gist='{gist[:50]}...', "
            f"salience={memory.salience.name}, "
            f"engram_id={memory.engram_id[:8]}"
        )

        # Phase 6: Publish memory.created event
        if EVENT_BUS_AVAILABLE:
            try:
                publish_event(
                    "memory.created",
                    source="vismriti",
                    project_path=self.project_path,
                    memory_id=memory.engram_id,
                    gist=gist[:100],  # Truncate for event payload
                    salience=memory.salience.name,
                    memory_type=metadata.get('type', 'generic'),
                    file_path=metadata.get('file'),
                    aggregated=should_aggregate
                )
            except Exception as e:
                logger.error(f"Failed to publish memory.created event: {e}")

        return memory

    def recall(
        self,
        query: str,
        min_salience: Optional[SalienceLevel] = None,
        top_k: int = 10,
        include_forgotten: bool = False,
        audience: Optional[str] = None  # Phase 5: Audience-specific recall
    ) -> List[Memory]:
        """
        Retrieve memories matching query

        Phase 4: Reconstruction (not just keyword search)

        Research: "When user asks question, engine does not do simple
        keyword search. It reconstructs from durable gist memory."

        Args:
            query: Search query
            min_salience: Minimum salience level to include
            top_k: Maximum number of results
            include_forgotten: Include pruned/unlearned memories
            audience: Optional audience perspective (e.g., "developer", "ai", "manager", "personal") - Phase 5

        Returns:
            List of matching memories (sorted by relevance)

        Note:
            If audience is specified and multi-audience gists are available,
            the Memory objects will have their gist replaced with the
            audience-specific version for that perspective.
        """

        query_lower = query.lower()
        matches = []

        for memory in self.memories:
            # Filter by status
            if not include_forgotten and memory.status in [
                MemoryStatus.PRUNED,
                MemoryStatus.UNLEARNED
            ]:
                continue

            # Filter by salience
            if min_salience and memory.salience.value < min_salience.value:
                continue

            # Simple keyword matching (can be enhanced with semantic search)
            gist_lower = memory.gist.lower() if memory.gist else ""
            verbatim_lower = memory.verbatim.lower() if memory.verbatim else ""

            if query_lower in gist_lower or query_lower in verbatim_lower:
                # Record access (affects decay calculations)
                memory.access()
                matches.append(memory)

        # Sort by salience (higher first), then recency
        matches.sort(
            key=lambda m: (m.salience.value, m.created_at),
            reverse=True
        )

        results = matches[:top_k]

        logger.debug(f"Recall query '{query}': {len(results)} matches found")

        return results

    def forget(
        self,
        query: str,
        method: str = "simple_suppress",
        confirmation: bool = True
    ) -> Dict:
        """
        Actively forget memories matching query

        Phase 3B: Active Unlearning (Motivated Forgetting)

        Research: "This is motivated forgetting - conscious decision
        to suppress unwanted memories (lateral PFC → hippocampus)"

        Args:
            query: What to forget (search query)
            method: "gradient_ascent" or "simple_suppress"
            confirmation: Require explicit confirmation (safety)

        Returns:
            Statistics about forgetting operation

        Example:
            >>> memory.forget("temporary test data", confirmation=False)
            >>> memory.forget("debug logs", method="simple_suppress", confirmation=False)
        """

        # Find memories to forget
        memories_to_forget = self.recall(
            query,
            include_forgotten=False  # Don't forget already forgotten
        )

        if not memories_to_forget:
            logger.info(f"No memories found matching '{query}'")
            return {
                "memories_found": 0,
                "unlearned": 0,
                "query": query
            }

        # Safety confirmation
        if confirmation:
            logger.warning(
                f"About to forget {len(memories_to_forget)} memories. "
                f"Set confirmation=False to proceed."
            )
            return {
                "memories_found": len(memories_to_forget),
                "unlearned": 0,
                "confirmation_required": True,
                "message": "Set confirmation=False to proceed"
            }

        # Active unlearning
        stats = self.unlearning_engine.forget(
            memories_to_forget,
            method=method,
            explanation=f"User requested: '{query}'"
        )

        stats["query"] = query

        logger.info(
            f"Forgot {stats['unlearned']} memories matching '{query}' "
            f"via {method}"
        )

        return stats

    def run_decay_cycle(self) -> Dict:
        """
        Run passive decay cycle (simulates sleep cleanup)

        Phase 3A: Passive Decay (Synaptic Pruning)

        Research: "Sleep is to take out the garbage" - REM and SWS
        perform targeted memory cleanup

        Returns:
            Statistics about pruned memories
        """

        if not self.enable_decay:
            logger.info("Decay disabled, no pruning performed")
            return {"pruned": 0}

        stats = self.decay_engine.prune_batch(self.memories)

        logger.info(
            f"Decay cycle complete: {stats['pruned']} memories pruned"
        )

        return stats

    def get_ledger(
        self,
        include_pruned: bool = False,
        format: str = "dataframe"
    ):
        """
        Get transparent memory ledger

        Phase 4: Memory Ledger (Transparency)

        Research: "To make architecture perfectly transparent, present
        as 'Memory Ledger' users can inspect"

        Args:
            include_pruned: Include forgotten memories
            format: "dataframe" or "dict"

        Returns:
            Memory ledger (DataFrame or dict)
        """

        ledger = MemoryLedger(self.memories, self.decay_engine)

        if format == "dataframe":
            return ledger.get_ledger(include_pruned=include_pruned)
        elif format == "dict":
            df = ledger.get_ledger(include_pruned=include_pruned)
            return df.to_dict(orient="records")
        else:
            raise ValueError(f"Unknown format: {format}")

    def export_ledger(self, filepath: str = "memory_ledger.csv"):
        """Export memory ledger to CSV"""
        ledger = MemoryLedger(self.memories, self.decay_engine)
        return ledger.export_csv(filepath)

    def get_statistics(self) -> Dict:
        """Get comprehensive statistics about memory system"""
        ledger = MemoryLedger(self.memories, self.decay_engine)
        stats = ledger.get_statistics()

        # Add aggregation metrics if available
        if self.aggregator:
            stats['aggregation'] = self.aggregator.get_metrics()

        # Add database stats if available
        if self.db:
            try:
                db_stats = self.db.get_statistics(self.project_path)
                stats['database'] = db_stats
            except:
                pass

        return stats

    def get_aggregation_metrics(self) -> Dict:
        """
        Get metrics about memory aggregation

        Returns:
            Dict with aggregation statistics including:
            - memories_aggregated: Number of unique aggregated memories
            - occurrences_consolidated: Total occurrences prevented from duplication
            - duplicates_prevented: Number of duplicate writes prevented
            - cache_size: Current aggregation cache size
            - compression_ratio: Ratio of occurrences to unique memories
        """
        if not self.aggregator:
            return {
                'enabled': False,
                'message': 'Aggregation not enabled'
            }

        metrics = self.aggregator.get_metrics()
        metrics['enabled'] = True
        return metrics

    def run_semantic_consolidation(
        self,
        dry_run: bool = False,
        config: Optional[Dict] = None
    ):
        """
        Run semantic consolidation job on current project

        This consolidates related old memories into summaries,
        reducing database size while preserving important information.

        Args:
            dry_run: If True, don't modify database (just show what would happen)
            config: Optional config dict to override defaults

        Returns:
            ConsolidationMetrics with results

        Example:
            >>> memory = VismritiMemory()
            >>> metrics = memory.run_semantic_consolidation(dry_run=True)
            >>> print(f"Would consolidate {metrics.memories_consolidated} memories")
        """
        if not CONSOLIDATION_AVAILABLE:
            logger.error("Semantic consolidation not available")
            return None

        if not self.db:
            logger.error("Database not available for consolidation")
            return None

        # Load config
        if config:
            from vidurai.config.compression_config import CompressionConfig
            compression_config = CompressionConfig(config)
        else:
            compression_config = load_compression_config()

        # Create consolidation job
        job = SemanticConsolidationJob(
            db=self.db,
            config=compression_config.to_dict()
        )

        # Run consolidation
        metrics = job.run(
            project_path=self.project_path,
            dry_run=dry_run
        )

        logger.info(
            f"Consolidation {'(dry run) ' if dry_run else ''}complete: "
            f"{metrics.memories_before} → {metrics.memories_after} memories, "
            f"{metrics.compression_ratio:.1%} compression"
        )

        return metrics

    def _build_retention_context(self) -> Optional['RetentionContext']:
        """
        Build retention context from current memory state

        Returns:
            RetentionContext with current metrics, or None if database unavailable
        """
        if not self.db or not RETENTION_POLICY_AVAILABLE:
            return None

        try:
            # Get database statistics
            stats = self.db.get_statistics(self.project_path)

            # Extract salience counts
            by_salience = stats.get('by_salience', {})
            high_count = by_salience.get('HIGH', 0) + by_salience.get('CRITICAL', 0)
            medium_count = by_salience.get('MEDIUM', 0)
            low_count = by_salience.get('LOW', 0)
            noise_count = by_salience.get('NOISE', 0)

            # Calculate age metrics
            avg_age = stats.get('avg_age_days', 0.0)
            oldest = stats.get('oldest_age_days', 0.0)

            # Estimate size and tokens
            total_memories = stats.get('total', 0)
            estimated_tokens = total_memories * 100  # Rough estimate: 100 tokens per memory

            # Activity metrics (last 24 hours)
            # TODO: Add database methods to track these properly
            memories_added = 0  # Placeholder
            memories_accessed = 0  # Placeholder

            context = RetentionContext(
                total_memories=total_memories,
                high_salience_count=high_count,
                medium_salience_count=medium_count,
                low_salience_count=low_count,
                noise_salience_count=noise_count,
                avg_age_days=avg_age,
                oldest_memory_days=oldest,
                total_size_mb=total_memories * 0.001,  # Rough estimate
                estimated_tokens=estimated_tokens,
                memories_added_last_day=memories_added,
                memories_accessed_last_day=memories_accessed,
                project_path=self.project_path
            )

            return context

        except Exception as e:
            logger.error(f"Failed to build retention context: {e}")
            return None

    def _execute_retention_action(
        self,
        action: 'RetentionAction',
        context: 'RetentionContext'
    ) -> Optional['RetentionOutcome']:
        """
        Execute a retention action

        Args:
            action: Action to execute
            context: Current context (for before metrics)

        Returns:
            RetentionOutcome with results
        """
        import time

        if not RETENTION_POLICY_AVAILABLE:
            return None

        start_time = time.time()
        memories_before = context.total_memories
        consolidations = 0
        decays = 0
        errors = 0
        tokens_saved = 0

        try:
            if action == RetentionAction.DO_NOTHING:
                logger.debug("Retention action: DO_NOTHING")
                pass

            elif action == RetentionAction.COMPRESS_LIGHT:
                logger.info("Retention action: COMPRESS_LIGHT")
                if CONSOLIDATION_AVAILABLE and self.db:
                    config = {
                        'enabled': True,
                        'target_ratio': 0.4,  # 60% reduction target
                        'min_salience': 'LOW',
                        'max_age_days': 30,
                    }
                    metrics = self.run_semantic_consolidation(dry_run=False, config=config)
                    if metrics:
                        consolidations = metrics.groups_consolidated
                        tokens_saved = metrics.tokens_saved

            elif action == RetentionAction.COMPRESS_AGGRESSIVE:
                logger.info("Retention action: COMPRESS_AGGRESSIVE")
                if CONSOLIDATION_AVAILABLE and self.db:
                    config = {
                        'enabled': True,
                        'target_ratio': 0.6,  # 80% reduction target
                        'min_salience': 'MEDIUM',  # More aggressive: include MEDIUM
                        'max_age_days': 14,  # Shorter window
                    }
                    metrics = self.run_semantic_consolidation(dry_run=False, config=config)
                    if metrics:
                        consolidations = metrics.groups_consolidated
                        tokens_saved = metrics.tokens_saved

            elif action == RetentionAction.DECAY_LOW_VALUE:
                logger.info("Retention action: DECAY_LOW_VALUE")
                # Trigger decay on LOW/NOISE memories
                # For now, this is handled by automatic expiration
                # Future: implement explicit decay trigger
                decays = 0  # Placeholder

            elif action == RetentionAction.CONSOLIDATE_AND_DECAY:
                logger.info("Retention action: CONSOLIDATE_AND_DECAY")
                # Run both consolidation and decay
                if CONSOLIDATION_AVAILABLE and self.db:
                    config = {
                        'enabled': True,
                        'target_ratio': 0.5,  # 70% reduction
                        'min_salience': 'LOW',
                        'max_age_days': 30,
                    }
                    metrics = self.run_semantic_consolidation(dry_run=False, config=config)
                    if metrics:
                        consolidations = metrics.groups_consolidated
                        tokens_saved = metrics.tokens_saved
                # Also trigger decay
                decays = 0  # Placeholder

        except Exception as e:
            logger.error(f"Error executing retention action {action.value}: {e}")
            errors += 1

        # Get updated stats
        memories_after = memories_before
        if self.db:
            try:
                updated_stats = self.db.get_statistics(self.project_path)
                memories_after = updated_stats.get('total', memories_before)
            except:
                pass

        execution_time_ms = (time.time() - start_time) * 1000

        outcome = RetentionOutcome(
            action=action,
            memories_before=memories_before,
            memories_after=memories_after,
            tokens_saved=tokens_saved,
            consolidations_performed=consolidations,
            decays_performed=decays,
            errors_encountered=errors,
            execution_time_ms=execution_time_ms
        )

        return outcome

    def evaluate_and_execute_retention(self) -> Optional[Dict[str, Any]]:
        """
        Evaluate current memory state and execute retention policy

        This is the main entry point for RL-driven retention decisions.
        Called periodically (e.g., daily, or after N memories stored).

        Returns:
            Dict with action, outcome, and learning status

        Example:
            >>> memory = VismritiMemory(retention_policy="rl_based")
            >>> result = memory.evaluate_and_execute_retention()
            >>> print(f"Action: {result['action']}, Compression: {result['outcome']['compression_ratio']}")
        """
        if not self.retention_policy or not RETENTION_POLICY_AVAILABLE:
            logger.debug("Retention policy not available")
            return None

        # Build context
        context = self._build_retention_context()
        if not context:
            logger.warning("Could not build retention context")
            return None

        # Decide action
        action = self.retention_policy.decide_action(context)
        logger.info(f"Retention policy decision: {action.value} (policy: {self.retention_policy.name})")

        # Execute action
        outcome = self._execute_retention_action(action, context)
        if not outcome:
            logger.warning("Could not execute retention action")
            return None

        # Learn from outcome
        self.retention_policy.learn_from_outcome(context, action, outcome)

        # Return results
        result = {
            'policy': self.retention_policy.name,
            'context': context.to_dict(),
            'action': action.value,
            'outcome': outcome.to_dict(),
        }

        logger.info(
            f"Retention execution complete: {action.value} - "
            f"{outcome.memories_before} → {outcome.memories_after} memories "
            f"({outcome.compression_ratio:.1%} compression)"
        )

        return result

    def print_summary(self):
        """Print human-readable summary"""
        ledger = MemoryLedger(self.memories, self.decay_engine)
        ledger.print_summary()

    def get_context_for_ai(
        self,
        query: Optional[str] = None,
        max_tokens: int = 2000,
        audience: Optional[str] = None  # Phase 5: Audience-specific context
    ) -> str:
        """
        Format memories as context for AI (v2.0 - Claude Code integration)

        This method retrieves relevant project memories and formats them
        as markdown context that can be injected into AI prompts.

        Args:
            query: Optional query to filter relevant memories
            max_tokens: Maximum tokens to return (rough estimate)
            audience: Optional audience perspective (e.g., "developer", "ai", "manager", "personal") - Phase 5

        Returns:
            Formatted markdown context string

        Example:
            >>> context = memory.get_context_for_ai(query="authentication")
            >>> print(context)
            # VIDURAI PROJECT CONTEXT

            Project: my-project

            ## CRITICAL Priority Memories
            - **Fixed auth bug in login flow**
              - File: `auth.py`
              - Age: 2 days ago

        Phase 5 Example:
            >>> context = memory.get_context_for_ai(query="auth", audience="developer")
            # Returns developer-focused gists with technical details

            >>> context = memory.get_context_for_ai(query="auth", audience="manager")
            # Returns manager-focused gists with impact summaries
        """
        if not self.db:
            logger.warning("Database not available, using in-memory recall")
            # Fallback to in-memory
            memories = self.recall(query=query or "", top_k=20)
            if not memories:
                return "[No relevant project context found]"

            context = "# VIDURAI PROJECT CONTEXT\n\n"
            context += f"Project: {Path(self.project_path).name}\n\n"

            for mem in memories[:10]:
                context += f"- **{mem.gist[:100]}**\n"
                if mem.metadata.get('file'):
                    context += f"  - File: `{mem.metadata['file']}`\n"
                context += "\n"

            return context

        # Use database for efficient query
        try:
            # Smart Query Sanitization for intersection search
            keywords = self._sanitize_query(query) if query else None

            memories = self.db.recall_memories(
                project_path=self.project_path,
                query=query,
                min_salience=DBSalienceLevel.MEDIUM,
                limit=20,
                keywords=keywords  # Pass sanitized keywords for intersection search
            )

            if not memories:
                return "[No relevant project context found]"

            # Format as markdown
            context = "# VIDURAI PROJECT CONTEXT\n\n"
            context += f"Project: {Path(self.project_path).name}\n\n"

            # Group by salience
            by_salience = {}
            for mem in memories:
                salience = mem['salience']
                if salience not in by_salience:
                    by_salience[salience] = []
                by_salience[salience].append(mem)

            # Phase 5: Enrich memories with audience-specific gists if requested
            if audience and self.db:
                try:
                    for mem in memories:
                        audience_gists = self.db.get_audience_gists(
                            mem['id'],
                            audiences=[audience]
                        )
                        if audience in audience_gists:
                            mem['audience_gist'] = audience_gists[audience]
                        else:
                            mem['audience_gist'] = mem['gist']  # Fallback to canonical
                except Exception as e:
                    logger.warning(f"Failed to enrich with audience gists: {e}")
                    # Set fallback for all
                    for mem in memories:
                        mem['audience_gist'] = mem['gist']
            else:
                # No audience specified, use canonical gist
                for mem in memories:
                    mem['audience_gist'] = mem['gist']

            # Output in priority order
            for salience in ['CRITICAL', 'HIGH', 'MEDIUM']:
                if salience not in by_salience:
                    continue

                context += f"## {salience} Priority Memories\n\n"
                for mem in by_salience[salience][:5]:  # Limit per category
                    # Use audience-specific gist if available
                    gist_to_display = mem.get('audience_gist', mem['gist'])
                    context += f"- **{gist_to_display}**\n"
                    if mem['file_path']:
                        context += f"  - File: `{mem['file_path']}`\n"

                    # Calculate age
                    created_at = datetime.fromisoformat(mem['created_at'])
                    age_days = (datetime.now() - created_at).days
                    if age_days == 0:
                        age_str = "today"
                    elif age_days == 1:
                        age_str = "1 day ago"
                    else:
                        age_str = f"{age_days} days ago"
                    context += f"  - Age: {age_str}\n"
                    context += "\n"

            # Truncate if too long (rough token estimate: 1 token ≈ 4 chars)
            max_chars = max_tokens * 4
            if len(context) > max_chars:
                context = context[:max_chars] + "\n\n[Context truncated...]"

            # Phase 6: Publish memory.context_retrieved event
            if EVENT_BUS_AVAILABLE:
                try:
                    publish_event(
                        "memory.context_retrieved",
                        source="vismriti",
                        project_path=self.project_path,
                        query=query or "all",
                        memory_count=len(memories),
                        audience=audience,
                        context_length=len(context)
                    )
                except Exception as e:
                    logger.error(f"Failed to publish memory.context_retrieved event: {e}")

            return context

        except Exception as e:
            logger.error(f"Error getting context for AI: {e}")
            return f"[Error retrieving context: {e}]"

    def __len__(self) -> int:
        """Get number of active memories"""
        return sum(
            1 for m in self.memories
            if m.status == MemoryStatus.ACTIVE
        )

    def __repr__(self):
        active = len(self)
        total = len(self.memories)
        return (
            f"VismritiMemory(active={active}, total={total}, "
            f"gist_extraction={self.enable_gist_extraction}, "
            f"decay={self.enable_decay})"
        )
