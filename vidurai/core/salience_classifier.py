"""
Salience Classifier
Classifies memory importance based on dopamine-tagging research

Research Foundation:
- Dopamine-mediated consolidation (VTA→BLA pathway)
- "Emotional salience is one type of relevance cue"
- "Reward signal facilitates consolidation of inconspicuous stimuli"

Biological Mapping:
- CRITICAL = Very strong dopamine release (explicit commands, credentials)
- HIGH = Strong dopamine (reward from bug fix, breakthrough)
- MEDIUM = Baseline dopamine (normal work)
- LOW = Weak dopamine (casual interaction)
- NOISE = No dopamine signal (system logs)

जय विदुराई! 🕉️
"""

from vidurai.core.data_structures_v3 import SalienceLevel, Memory
from typing import Dict, List


class SalienceClassifier:
    """
    Classify memory salience (importance) based on biological tagging

    Research: "The brain automatically filters experiences, preserving
    memories of important information and allowing the rest to fade"

    Implementation uses rule-based + ML hybrid approach
    """

    def __init__(self):
        """Initialize salience classifier with keyword rules"""

        # CRITICAL keywords (strong dopamine signal)
        self.critical_keywords = [
            "remember this", "important", "critical", "must not forget",
            "api key", "password", "secret", "credential", "token",
            "never forget", "always remember"
        ]

        # HIGH salience indicators (reward signal)
        self.high_keywords = [
            "solved", "fixed", "bug fix", "breakthrough", "aha moment",
            "finally works", "success", "resolved", "found solution",
            "critical error resolved", "major milestone"
        ]

        # LOW salience indicators (weak signal)
        self.low_keywords = [
            "hello", "hi", "test", "testing", "just checking",
            "hmm", "uh", "um", "maybe", "not sure"
        ]

        # NOISE indicators (no signal)
        self.noise_keywords = [
            "log:", "debug:", "trace:", "timestamp:", "system:"
        ]

    def classify(self, memory: Memory) -> SalienceLevel:
        """
        Classify memory salience

        Research Mapping:
        - CRITICAL: Strong dopamine (explicit user command, credentials)
        - HIGH: Medium dopamine (reward from achievement)
        - MEDIUM: Baseline dopamine (normal activity)
        - LOW: Weak dopamine (casual, low importance)
        - NOISE: No dopamine (automatic system events)

        Args:
            memory: Memory object to classify

        Returns:
            SalienceLevel enum
        """

        verbatim_lower = memory.verbatim.lower() if memory.verbatim else ""
        gist_lower = memory.gist.lower() if memory.gist else ""
        combined = f"{verbatim_lower} {gist_lower}"

        # Rule 1: CRITICAL - Explicit user commands
        if any(kw in combined for kw in self.critical_keywords):
            return SalienceLevel.CRITICAL

        # Rule 2: CRITICAL - Security/credentials metadata
        if memory.metadata:
            mem_type = memory.metadata.get("type", "").lower()
            if mem_type in ["credential", "api_key", "password", "secret"]:
                return SalienceLevel.CRITICAL

        # Rule 3: HIGH - Bug fixes and breakthroughs (reward signal)
        if any(kw in combined for kw in self.high_keywords):
            return SalienceLevel.HIGH

        if memory.metadata and memory.metadata.get("solved_bug"):
            return SalienceLevel.HIGH

        # Rule 4: NOISE - System logs (no dopamine)
        if any(kw in combined for kw in self.noise_keywords):
            return SalienceLevel.NOISE

        if memory.metadata and memory.metadata.get("type") == "system_log":
            return SalienceLevel.NOISE

        # Rule 5: LOW - Casual interactions
        if any(kw in verbatim_lower for kw in self.low_keywords):
            return SalienceLevel.LOW

        # Rule 6: LOW - Very short verbatim (likely trivial)
        if memory.verbatim and len(memory.verbatim) < 20:
            return SalienceLevel.LOW

        # Default: MEDIUM (normal work, baseline dopamine)
        return SalienceLevel.MEDIUM

    def classify_batch(self, memories: List[Memory]) -> Dict[str, int]:
        """
        Classify multiple memories and return statistics

        Returns:
            Dictionary with count per salience level
        """
        stats = {level.name: 0 for level in SalienceLevel}

        for memory in memories:
            salience = self.classify(memory)
            memory.salience = salience
            stats[salience.name] += 1

        return stats

    def explain_classification(self, memory: Memory) -> str:
        """
        Explain why a memory received its salience classification

        Returns natural language explanation
        """
        salience = self.classify(memory)

        explanations = {
            SalienceLevel.CRITICAL: "Contains explicit 'remember' command or credentials",
            SalienceLevel.HIGH: "Represents achievement, bug fix, or breakthrough (reward signal)",
            SalienceLevel.MEDIUM: "Normal work activity (baseline importance)",
            SalienceLevel.LOW: "Casual interaction or brief comment",
            SalienceLevel.NOISE: "System-generated log or raw data"
        }

        return explanations.get(salience, "Unknown classification")
