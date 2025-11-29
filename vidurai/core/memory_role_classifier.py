"""
Memory Role Classification System
Classifies memories by their role in the development narrative

Philosophy: "Not all memories serve the same purpose"
विस्मृति भी विद्या है (Forgetting too is knowledge)

Research Foundation:
- Narrative memory: Events have roles (cause, attempt, resolution)
- Root cause analysis: Distinguishing symptoms from causes
- Learning theory: Successful outcomes more valuable than failures
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import re
from loguru import logger


class MemoryRole(Enum):
    """
    Role of a memory in the development narrative

    Priority for retention:
    RESOLUTION > CAUSE > ATTEMPTED_FIX > CONTEXT > NOISE
    """
    CAUSE = "cause"  # Root cause identification
    ATTEMPTED_FIX = "attempted_fix"  # Debugging attempts that failed
    RESOLUTION = "resolution"  # Successful solution
    CONTEXT = "context"  # Background information
    NOISE = "noise"  # Redundant or low-value content


@dataclass
class RoleClassificationResult:
    """Result of role classification"""
    role: MemoryRole
    confidence: float  # 0.0 to 1.0
    keywords_matched: List[str]
    reasoning: str  # Why this role was chosen


class MemoryRoleClassifier:
    """
    Classifies memory role using keyword matching and heuristics

    Classification priority (checked in order):
    1. RESOLUTION - Successful fix keywords
    2. CAUSE - Root cause identification
    3. ATTEMPTED_FIX - Debugging attempt keywords
    4. CONTEXT - General observations
    5. NOISE - Default for low-signal content
    """

    def __init__(self):
        """Initialize classifier with keyword patterns"""

        # RESOLUTION keywords (highest priority)
        self.resolution_patterns = [
            # Success indicators
            r'\b(fixed|solved|resolved|working now|stable now)\b',
            r'\bproblem (fixed|solved|resolved)\b',
            r'\bissue (fixed|solved|resolved)\b',
            r'\b(success|successful|works? correctly)\b',
            r'\b(deployed|merged|committed) (fix|solution)\b',
            r'\bno (more|longer) (error|issue|problem)',
            r'\btests? (pass|passing|passed)\b',
            r'\b(confirmed|verified) (fix|solution|working)\b',
            # Solution indicators
            r'\bsolution was to\b',
            r'\bthe fix was\b',
            r'\bfinal solution\b',
            r'\bthis (fixed|solved) it\b',
        ]

        # CAUSE keywords (root cause identification)
        self.cause_patterns = [
            r'\broot cause (was|is)\b',
            r'\bthe (real )?issue (was|is)\b',
            r'\bthe (real )?problem (was|is)\b',
            r'\bcaused by\b',
            r'\bdue to\b',
            r'\bbecause of\b',
            r'\bthe reason (was|is)\b',
            r'\bidentified cause\b',
            r'\bfound (the )?(cause|reason)\b',
            r'\btraced to\b',
            r'\boriginates from\b',
            r'\bsource of (error|issue|problem)\b',
        ]

        # ATTEMPTED_FIX keywords (unsuccessful attempts)
        self.attempted_fix_patterns = [
            # Attempt indicators
            r'\btried (to )?\b',
            r'\battempted (to )?\b',
            r'\bdebugging\b',
            r'\btesting (if|whether)\b',
            r'\bexperimenting with\b',
            r'\btrying different\b',
            # Failure indicators
            r'\bdid(n\'t| not) work\b',
            r'\bstill (failing|broken|error)\b',
            r'\bnot (successful|working)\b',
            r'\bfailed attempt\b',
            r'\bdidn\'t fix\b',
            r'\bdidn\'t solve\b',
            # Hypothesis testing
            r'\bmaybe (if|this|the)\b',
            r'\bwondering if\b',
            r'\bcould (it )?be\b',
        ]

        # CONTEXT keywords (background info)
        self.context_patterns = [
            r'\bfor context\b',
            r'\bbackground\b',
            r'\bhistory\b',
            r'\bpreviously\b',
            r'\bnote that\b',
            r'\brelevant:?\b',
            r'\brelated to\b',
            r'\bsee also\b',
            r'\breference\b',
        ]

        # NOISE indicators (low value)
        self.noise_patterns = [
            # Trivial content
            r'^(ok|okay|yes|no|hmm|uh)$',
            r'^\.+$',  # Just dots
            r'^\s*$',  # Empty
            # Very short and uninformative
            r'^.{1,10}$',  # Very short (handled separately)
        ]

        # Compile patterns for performance
        self.resolution_regex = [re.compile(p, re.IGNORECASE) for p in self.resolution_patterns]
        self.cause_regex = [re.compile(p, re.IGNORECASE) for p in self.cause_patterns]
        self.attempted_fix_regex = [re.compile(p, re.IGNORECASE) for p in self.attempted_fix_patterns]
        self.context_regex = [re.compile(p, re.IGNORECASE) for p in self.context_patterns]
        self.noise_regex = [re.compile(p, re.IGNORECASE) for p in self.noise_patterns]

        logger.debug("Memory role classifier initialized with pattern matching")

    def classify(
        self,
        verbatim: str,
        gist: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> RoleClassificationResult:
        """
        Classify memory role

        Args:
            verbatim: Full memory text
            gist: Summary (optional, used if provided)
            metadata: Additional context (event_type, tags, etc.)

        Returns:
            RoleClassificationResult with role and confidence
        """
        # Combine verbatim and gist for analysis
        text = verbatim
        if gist:
            text = f"{verbatim} {gist}"

        text_lower = text.lower()

        # Extract metadata hints
        event_type = metadata.get('event_type', '') if metadata else ''
        tags = metadata.get('tags', []) if metadata else []

        # Priority 1: Check for RESOLUTION
        resolution_matches = self._find_matches(text, self.resolution_regex)
        if resolution_matches:
            return RoleClassificationResult(
                role=MemoryRole.RESOLUTION,
                confidence=min(0.7 + len(resolution_matches) * 0.1, 1.0),
                keywords_matched=resolution_matches,
                reasoning=f"Matched resolution keywords: {', '.join(resolution_matches[:3])}"
            )

        # Priority 2: Check for CAUSE
        cause_matches = self._find_matches(text, self.cause_regex)
        if cause_matches:
            return RoleClassificationResult(
                role=MemoryRole.CAUSE,
                confidence=min(0.7 + len(cause_matches) * 0.1, 1.0),
                keywords_matched=cause_matches,
                reasoning=f"Matched cause keywords: {', '.join(cause_matches[:3])}"
            )

        # Priority 3: Check for ATTEMPTED_FIX
        attempted_fix_matches = self._find_matches(text, self.attempted_fix_regex)
        if attempted_fix_matches:
            return RoleClassificationResult(
                role=MemoryRole.ATTEMPTED_FIX,
                confidence=min(0.6 + len(attempted_fix_matches) * 0.1, 1.0),
                keywords_matched=attempted_fix_matches,
                reasoning=f"Matched attempted fix keywords: {', '.join(attempted_fix_matches[:3])}"
            )

        # Priority 4: Check for CONTEXT
        context_matches = self._find_matches(text, self.context_regex)
        if context_matches:
            return RoleClassificationResult(
                role=MemoryRole.CONTEXT,
                confidence=0.6,
                keywords_matched=context_matches,
                reasoning=f"Matched context keywords: {', '.join(context_matches[:3])}"
            )

        # Priority 5: Check for NOISE
        noise_matches = self._find_matches(text, self.noise_regex)
        if noise_matches or len(text.strip()) < 15:
            return RoleClassificationResult(
                role=MemoryRole.NOISE,
                confidence=0.8 if noise_matches else 0.6,
                keywords_matched=noise_matches,
                reasoning="Trivial content or very short text"
            )

        # Default: CONTEXT (neutral role for unclassified content)
        return RoleClassificationResult(
            role=MemoryRole.CONTEXT,
            confidence=0.4,  # Low confidence for default
            keywords_matched=[],
            reasoning="No strong indicators, defaulting to context"
        )

    def classify_batch(
        self,
        memories: List[Dict[str, Any]]
    ) -> Dict[int, RoleClassificationResult]:
        """
        Classify multiple memories efficiently

        Args:
            memories: List of memory dicts with 'id', 'verbatim', 'gist', 'metadata'

        Returns:
            Dict mapping memory_id to RoleClassificationResult
        """
        results = {}

        for memory in memories:
            memory_id = memory.get('id')
            verbatim = memory.get('verbatim', '')
            gist = memory.get('gist')
            metadata = memory.get('metadata')

            result = self.classify(verbatim, gist, metadata)
            results[memory_id] = result

        logger.debug(f"Classified {len(memories)} memories in batch")
        return results

    def get_role_priority(self, role: MemoryRole) -> int:
        """
        Get retention priority for a role (higher = more important)

        Returns:
            Priority score (0-20)
        """
        priority_map = {
            MemoryRole.RESOLUTION: 20,
            MemoryRole.CAUSE: 18,
            MemoryRole.ATTEMPTED_FIX: 12,
            MemoryRole.CONTEXT: 8,
            MemoryRole.NOISE: 0,
        }
        return priority_map.get(role, 0)

    def _find_matches(self, text: str, patterns: List[re.Pattern]) -> List[str]:
        """
        Find all pattern matches in text

        Returns:
            List of matched keywords/phrases
        """
        matches = []
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                # Extract the matched text
                matched_text = match.group(0)
                matches.append(matched_text)

        return matches

    def get_statistics(self) -> Dict[str, Any]:
        """Get classifier statistics"""
        return {
            'classifier': 'pattern_based',
            'pattern_counts': {
                'resolution': len(self.resolution_patterns),
                'cause': len(self.cause_patterns),
                'attempted_fix': len(self.attempted_fix_patterns),
                'context': len(self.context_patterns),
                'noise': len(self.noise_patterns),
            },
            'total_patterns': (
                len(self.resolution_patterns) +
                len(self.cause_patterns) +
                len(self.attempted_fix_patterns) +
                len(self.context_patterns) +
                len(self.noise_patterns)
            )
        }


# Convenience function
def classify_memory_role(
    verbatim: str,
    gist: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> RoleClassificationResult:
    """
    Convenience function to classify a single memory

    Example:
        result = classify_memory_role(
            "Fixed the JWT auth issue. Root cause was timezone mismatch.",
            metadata={'event_type': 'code_change'}
        )
        print(result.role)  # MemoryRole.RESOLUTION
        print(result.confidence)  # 0.8
    """
    classifier = MemoryRoleClassifier()
    return classifier.classify(verbatim, gist, metadata)
