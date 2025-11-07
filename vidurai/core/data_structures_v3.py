"""
Data Structures v3 - Vismriti Architecture
Implements research-backed dual-trace memory with salience tagging

Research Foundation:
- Fuzzy-Trace Theory: Verbatim + Gist traces (Reyna & Brainerd)
- Dopamine-mediated consolidation (VTA→BLA pathway)
- Categorical salience levels inspired by biological tagging

जय विदुराई! 🕉️
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


class SalienceLevel(Enum):
    """
    Categorical salience levels based on dopamine tagging research

    Research: Dopamine modulates learning signals that facilitate
    consolidation of events (VTA→BLA pathway strength mapping)

    References:
    - "Dopamine and fear memory formation in the human amygdala" (PMC)
    - "Dopamine activity on perceptual salience for recognition memory"
    """
    CRITICAL = 100    # Strong dopamine signal (explicit commands, credentials)
    HIGH = 75         # Medium dopamine (bug fixes, breakthroughs, rewards)
    MEDIUM = 50       # Baseline dopamine (normal work)
    LOW = 25          # Weak dopamine (casual interactions)
    NOISE = 5         # No dopamine signal (raw logs, typos)

    def __str__(self):
        return self.name

    @property
    def description(self):
        """Human-readable description"""
        descriptions = {
            SalienceLevel.CRITICAL: "Critical - Never forgets (explicit 'remember', API keys)",
            SalienceLevel.HIGH: "High - Durable (bug fixes, breakthroughs, important events)",
            SalienceLevel.MEDIUM: "Medium - Normal retention (regular work)",
            SalienceLevel.LOW: "Low - Short-term (casual interactions)",
            SalienceLevel.NOISE: "Noise - Immediate decay (raw logs, typos)"
        }
        return descriptions.get(self, "Unknown")


class MemoryStatus(Enum):
    """
    Memory lifecycle states

    Research: Engrams exist in different states (from silent to active)
    based on retrievability

    References:
    - "From Engrams to Pathologies of the Brain" (Frontiers)
    - "Endogenous engram silencing" mechanism
    """
    ACTIVE = "active"              # Currently accessible
    CONSOLIDATED = "consolidated"  # Stable, protected (EWC-style)
    PRUNED = "pruned"             # Deleted via passive decay (synaptic pruning)
    UNLEARNED = "unlearned"       # Deleted via active forgetting (motivated)
    SILENCED = "silenced"         # Engram exists but suppressed

    def __str__(self):
        return self.value.title()


@dataclass
class Memory:
    """
    Dual-trace memory representation

    Research Foundation: Fuzzy-Trace Theory (FTT)

    FTT posits two parallel, independent representations:
    1. Verbatim Traces: Precise, literal details (surface features)
    2. Gist Traces: Bottom-line semantic meaning

    Key Finding: "Verbatim traces become inaccessible at a faster rate
    than gist traces" - This enables intelligent forgetting.

    Neural Correlates (hypothesized):
    - Posterior hippocampus: Verbatim/detail processing
    - Anterior hippocampus: Gist/semantic processing

    References:
    - "Fuzzy-trace theory" (Wikipedia, comprehensive overview)
    - "Tracking relation between gist and item memory" (eLife)
    - "Neural correlates of gist-based recognition" (PMC)

    जय विदुराई! 🕉️
    """

    # Dual traces (Fuzzy-Trace Theory)
    verbatim: str                      # Surface-level, literal details
    gist: str                          # Bottom-line semantic meaning

    # Salience (dopamine-mediated tagging)
    salience: SalienceLevel = SalienceLevel.MEDIUM

    # Temporal metadata
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0

    # State management
    status: MemoryStatus = MemoryStatus.ACTIVE

    # User-defined context
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Neural correlate mapping (hypothetical)
    engram_id: Optional[str] = None           # Unique engram identifier
    anterior_hippocampus_weight: float = 0.7  # Gist processing weight
    posterior_hippocampus_weight: float = 0.3 # Detail processing weight

    def __post_init__(self):
        """Validate memory creation"""
        if not self.verbatim and not self.gist:
            raise ValueError("Memory must have either verbatim or gist (or both)")

        # Auto-generate engram ID if not provided
        if self.engram_id is None:
            import hashlib
            content = f"{self.verbatim}{self.gist}{self.created_at}"
            self.engram_id = hashlib.sha256(content.encode()).hexdigest()[:16]

    def access(self):
        """Record memory access (affects decay calculations)"""
        self.last_accessed = datetime.now()
        self.access_count += 1

    def age_days(self) -> int:
        """Get memory age in days"""
        return (datetime.now() - self.created_at).days

    def days_since_access(self) -> int:
        """Get days since last access"""
        return (datetime.now() - self.last_accessed).days

    def is_verbatim_only(self) -> bool:
        """Check if memory is verbatim-only (faster decay)"""
        return bool(self.verbatim) and not bool(self.gist)

    def is_gist_only(self) -> bool:
        """Check if memory is gist-only (slower decay)"""
        return bool(self.gist) and not bool(self.verbatim)

    def __repr__(self):
        return f"Memory(gist='{self.gist[:50]}...', salience={self.salience.name}, status={self.status.value})"
