"""
Retention Scoring Engine
Multi-factor scoring system for memory retention decisions

Philosophy: "Value is multidimensional—salience, usage, role, and technical depth all matter"
विस्मृति भी विद्या है (Forgetting too is knowledge)

Research Foundation:
- Multi-criteria decision analysis (MCDA)
- Weighted scoring for importance estimation
- Temporal decay functions for recency
- Information value theory
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from loguru import logger

from vidurai.core.data_structures_v3 import SalienceLevel, Memory
from vidurai.core.memory_role_classifier import MemoryRole
from vidurai.core.entity_extractor import ExtractedEntities


@dataclass
class RetentionScore:
    """
    Comprehensive retention score for a memory

    Score Range: 0-200
    - 0-100: Normal memories
    - 100-200: Pinned memories (immune to forgetting)

    Components:
    - salience: 0-40 (CRITICAL=40, HIGH=30, MEDIUM=20, LOW=10, NOISE=0)
    - usage: 0-20 (access_count * 2, capped at 20)
    - recency: 0-15 (24h=15, 7d=10, 30d=5, older=0)
    - rl_value: 0-10 (from RL agent Q-value, if available)
    - technical_density: 0-10 (entity count, capped at 10)
    - root_cause: 0-15 (has root cause analysis)
    - role_priority: 0-20 (resolution=20, cause=18, attempted_fix=12, context=8, noise=0)
    - pin_bonus: +100 (if pinned)
    """
    total: float  # 0-200
    salience_component: float  # 0-40
    usage_component: float  # 0-20
    recency_component: float  # 0-15
    rl_component: float  # 0-10
    technical_density_component: float  # 0-10
    root_cause_component: float  # 0-15
    role_component: float  # 0-20
    pinned: bool  # If true, +100 bonus

    def should_forget(self, threshold: float = 30.0) -> bool:
        """
        Determine if memory should be forgotten

        Args:
            threshold: Minimum score to retain (default: 30)

        Returns:
            True if score below threshold (should forget)
        """
        return self.total < threshold

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return asdict(self)

    def get_breakdown(self) -> str:
        """Get human-readable score breakdown"""
        lines = [
            f"Total: {self.total:.1f}/200",
            f"  Salience: {self.salience_component:.1f}/40",
            f"  Usage: {self.usage_component:.1f}/20",
            f"  Recency: {self.recency_component:.1f}/15",
            f"  RL Value: {self.rl_component:.1f}/10",
            f"  Technical Density: {self.technical_density_component:.1f}/10",
            f"  Root Cause: {self.root_cause_component:.1f}/15",
            f"  Role Priority: {self.role_component:.1f}/20",
        ]
        if self.pinned:
            lines.append(f"  📌 PINNED: +100")

        return "\n".join(lines)


class RetentionScoreEngine:
    """
    Calculate retention scores for memories

    Combines multiple factors to determine memory value and retention priority.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize retention score engine

        Args:
            config: Optional configuration for weight tuning
        """
        self.config = config or {}

        # Weights (can be overridden via config)
        self.weights = {
            'salience': self.config.get('salience_weight', 1.0),
            'usage': self.config.get('usage_weight', 1.0),
            'recency': self.config.get('recency_weight', 1.0),
            'rl': self.config.get('rl_weight', 1.0),
            'technical_density': self.config.get('technical_density_weight', 1.0),
            'root_cause': self.config.get('root_cause_weight', 1.0),
            'role': self.config.get('role_weight', 1.0),
        }

        # Thresholds
        self.pin_bonus = 100.0
        self.forget_threshold = self.config.get('forget_threshold', 30.0)

        logger.debug(f"Retention score engine initialized with weights: {self.weights}")

    def calculate_score(
        self,
        memory: Memory,
        role: MemoryRole,
        entities: ExtractedEntities,
        rl_value: Optional[float] = None,
        pinned: bool = False
    ) -> RetentionScore:
        """
        Calculate comprehensive retention score

        Args:
            memory: Memory object
            role: Classified memory role
            entities: Extracted technical entities
            rl_value: Optional RL agent Q-value (0.0-1.0)
            pinned: Whether memory is pinned

        Returns:
            RetentionScore with total and component scores
        """
        # Component 1: Salience (0-40)
        salience_score = self._calculate_salience_score(memory.salience)

        # Component 2: Usage (0-20)
        usage_score = self._calculate_usage_score(memory.access_count)

        # Component 3: Recency (0-15)
        recency_score = self._calculate_recency_score(memory.last_accessed or memory.timestamp)

        # Component 4: RL Value (0-10)
        rl_score = self._calculate_rl_score(rl_value)

        # Component 5: Technical Density (0-10)
        tech_score = self._calculate_technical_density_score(entities)

        # Component 6: Root Cause (0-15)
        root_cause_score = self._calculate_root_cause_score(memory, role)

        # Component 7: Role Priority (0-20)
        role_score = self._calculate_role_score(role)

        # Sum components with weights
        total = (
            salience_score * self.weights['salience'] +
            usage_score * self.weights['usage'] +
            recency_score * self.weights['recency'] +
            rl_score * self.weights['rl'] +
            tech_score * self.weights['technical_density'] +
            root_cause_score * self.weights['root_cause'] +
            role_score * self.weights['role']
        )

        # Add pin bonus
        if pinned:
            total += self.pin_bonus

        return RetentionScore(
            total=total,
            salience_component=salience_score,
            usage_component=usage_score,
            recency_component=recency_score,
            rl_component=rl_score,
            technical_density_component=tech_score,
            root_cause_component=root_cause_score,
            role_component=role_score,
            pinned=pinned
        )

    def _calculate_salience_score(self, salience: SalienceLevel) -> float:
        """
        Calculate salience component (0-40)

        Mapping:
        - CRITICAL: 40
        - HIGH: 30
        - MEDIUM: 20
        - LOW: 10
        - NOISE: 0
        """
        salience_map = {
            SalienceLevel.CRITICAL: 40.0,
            SalienceLevel.HIGH: 30.0,
            SalienceLevel.MEDIUM: 20.0,
            SalienceLevel.LOW: 10.0,
            SalienceLevel.NOISE: 0.0,
        }
        return salience_map.get(salience, 0.0)

    def _calculate_usage_score(self, access_count: int) -> float:
        """
        Calculate usage component (0-20)

        Formula: min(access_count * 2, 20)
        """
        return min(access_count * 2.0, 20.0)

    def _calculate_recency_score(self, last_accessed: datetime) -> float:
        """
        Calculate recency component (0-15)

        Scoring:
        - Within 24h: 15
        - Within 7d: 10
        - Within 30d: 5
        - Older: 0
        """
        now = datetime.now()
        age = now - last_accessed

        if age <= timedelta(hours=24):
            return 15.0
        elif age <= timedelta(days=7):
            return 10.0
        elif age <= timedelta(days=30):
            return 5.0
        else:
            return 0.0

    def _calculate_rl_score(self, rl_value: Optional[float]) -> float:
        """
        Calculate RL component (0-10)

        Args:
            rl_value: Q-value from RL agent (0.0-1.0), or None

        Returns:
            Score 0-10 (rl_value * 10)
        """
        if rl_value is None:
            return 0.0

        # Normalize to 0-10 range
        return max(0.0, min(rl_value * 10.0, 10.0))

    def _calculate_technical_density_score(self, entities: ExtractedEntities) -> float:
        """
        Calculate technical density component (0-10)

        More technical entities → higher retention value

        Formula: min(entity_count, 10)
        """
        entity_count = entities.count()
        return min(float(entity_count), 10.0)

    def _calculate_root_cause_score(self, memory: Memory, role: MemoryRole) -> float:
        """
        Calculate root cause component (0-15)

        Returns 15 if:
        - Role is CAUSE, or
        - Memory text contains "root cause" keywords

        Otherwise: 0
        """
        if role == MemoryRole.CAUSE:
            return 15.0

        # Check for root cause keywords in text
        text = (memory.verbatim + " " + (memory.gist or "")).lower()
        root_cause_keywords = [
            'root cause',
            'the issue is',
            'the problem is',
            'caused by',
            'due to',
            'the reason is'
        ]

        for keyword in root_cause_keywords:
            if keyword in text:
                return 15.0

        return 0.0

    def _calculate_role_score(self, role: MemoryRole) -> float:
        """
        Calculate role priority component (0-20)

        Mapping:
        - RESOLUTION: 20
        - CAUSE: 18
        - ATTEMPTED_FIX: 12
        - CONTEXT: 8
        - NOISE: 0
        """
        role_map = {
            MemoryRole.RESOLUTION: 20.0,
            MemoryRole.CAUSE: 18.0,
            MemoryRole.ATTEMPTED_FIX: 12.0,
            MemoryRole.CONTEXT: 8.0,
            MemoryRole.NOISE: 0.0,
        }
        return role_map.get(role, 0.0)

    def calculate_batch(
        self,
        memories: list,
        roles: Dict[int, MemoryRole],
        entities: Dict[int, ExtractedEntities],
        rl_values: Optional[Dict[int, float]] = None,
        pinned_ids: Optional[set] = None
    ) -> Dict[int, RetentionScore]:
        """
        Calculate scores for multiple memories efficiently

        Args:
            memories: List of Memory objects
            roles: Dict mapping memory_id to MemoryRole
            entities: Dict mapping memory_id to ExtractedEntities
            rl_values: Optional dict mapping memory_id to RL Q-value
            pinned_ids: Optional set of pinned memory IDs

        Returns:
            Dict mapping memory_id to RetentionScore
        """
        scores = {}
        rl_values = rl_values or {}
        pinned_ids = pinned_ids or set()

        for memory in memories:
            memory_id = memory.id
            role = roles.get(memory_id, MemoryRole.CONTEXT)
            entity = entities.get(memory_id, ExtractedEntities())
            rl_value = rl_values.get(memory_id)
            pinned = memory_id in pinned_ids

            score = self.calculate_score(memory, role, entity, rl_value, pinned)
            scores[memory_id] = score

        logger.debug(f"Calculated retention scores for {len(memories)} memories")
        return scores

    def get_forget_candidates(
        self,
        scores: Dict[int, RetentionScore],
        threshold: Optional[float] = None
    ) -> list:
        """
        Get list of memory IDs that should be forgotten

        Args:
            scores: Dict mapping memory_id to RetentionScore
            threshold: Forget threshold (uses default if None)

        Returns:
            List of memory IDs with score < threshold
        """
        threshold = threshold or self.forget_threshold

        candidates = [
            memory_id
            for memory_id, score in scores.items()
            if score.should_forget(threshold)
        ]

        logger.info(f"Found {len(candidates)} forget candidates (threshold: {threshold})")
        return candidates

    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics"""
        return {
            'engine': 'retention_score_engine',
            'weights': self.weights,
            'pin_bonus': self.pin_bonus,
            'forget_threshold': self.forget_threshold,
            'score_range': [0, 200],
            'component_ranges': {
                'salience': [0, 40],
                'usage': [0, 20],
                'recency': [0, 15],
                'rl': [0, 10],
                'technical_density': [0, 10],
                'root_cause': [0, 15],
                'role': [0, 20],
            }
        }


# Convenience function
def calculate_retention_score(
    memory: Memory,
    role: MemoryRole,
    entities: ExtractedEntities,
    rl_value: Optional[float] = None,
    pinned: bool = False
) -> RetentionScore:
    """
    Convenience function to calculate retention score

    Example:
        from vidurai.core.memory_role_classifier import classify_memory_role
        from vidurai.core.entity_extractor import extract_entities

        memory = Memory(...)
        role = classify_memory_role(memory.verbatim).role
        entities = extract_entities(memory.verbatim)

        score = calculate_retention_score(memory, role, entities)
        print(f"Retention score: {score.total}")
        print(score.get_breakdown())
    """
    engine = RetentionScoreEngine()
    return engine.calculate_score(memory, role, entities, rl_value, pinned)
