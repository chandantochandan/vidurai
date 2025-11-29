"""
Multi-Audience Gist Generator
Phase 5: Audience-Specific Memory Gisting

Generates tailored gists for different audiences:
- developer: Technical, preserves implementation details
- ai: Structured patterns for AI consumption
- manager: Impact-focused, outcome-oriented
- personal: First-person narrative style

Philosophy: "The same memory, told differently to different listeners"
विस्मृति भी विद्या है (Forgetting too is knowledge) - contextualized for each audience
"""

import re
from typing import Dict, Optional, Any
from dataclasses import dataclass

from vidurai.config.multi_audience_config import MultiAudienceConfig


class MultiAudienceGistGenerator:
    """
    Generate audience-specific gists from canonical gist

    v1: Rule-based generation (no LLM calls)
    v2: LLM-enhanced generation (future)

    Example:
        >>> generator = MultiAudienceGistGenerator()
        >>> canonical = "Fixed authentication bug in JWT validation"
        >>> gists = generator.generate(
        ...     verbatim="Long technical description...",
        ...     canonical_gist=canonical,
        ...     context={"type": "bugfix"}
        ... )
        >>> print(gists['developer'])
        "Fixed JWT token validation in auth middleware"
        >>> print(gists['manager'])
        "Auth system stabilized"
    """

    def __init__(
        self,
        base_gist_extractor: Optional[Any] = None,
        config: Optional[MultiAudienceConfig] = None
    ):
        """
        Initialize multi-audience gist generator

        Args:
            base_gist_extractor: Optional GistExtractor instance (for future LLM use)
            config: Optional configuration
        """
        self.extractor = base_gist_extractor
        self.config = config or MultiAudienceConfig()

        # Technical term patterns (preserve in developer gist)
        self.tech_patterns = [
            r'\b[A-Z][a-z]+Error\b',  # PythonError, TypeError
            r'\b[A-Z][a-z]+Exception\b',  # ValueError, etc.
            r'\bAPI\b', r'\bSQL\b', r'\bHTTP\b', r'\bREST\b',
            r'\bJSON\b', r'\bXML\b', r'\bCSV\b',
            r'\bJWT\b', r'\bOAuth\b', r'\bSSO\b',
            r'\bgit\b', r'\bnpm\b', r'\bpip\b',
            r'\b[a-z]+\.py\b', r'\b[a-z]+\.js\b', r'\b[a-z]+\.ts\b',  # Files
            r'\bfunction\b', r'\bclass\b', r'\bmethod\b',
        ]

        # Action verbs for manager gist
        self.action_verbs = [
            'fixed', 'implemented', 'updated', 'created', 'deployed',
            'resolved', 'improved', 'optimized', 'refactored', 'debugged',
            'added', 'removed', 'configured', 'integrated', 'tested',
        ]

        # Personal conversion patterns
        self.personal_conversions = {
            r'\bfixed\b': 'I fixed',
            r'\bimplemented\b': 'I implemented',
            r'\bupdated\b': 'I updated',
            r'\bcreated\b': 'I created',
            r'\bresolved\b': 'I resolved',
            r'\badded\b': 'I added',
            r'\blearned\b': 'I learned',
            r'\bdiscovered\b': 'I discovered',
        }

    def generate(
        self,
        verbatim: str,
        canonical_gist: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Generate audience-specific gists

        Args:
            verbatim: Full verbatim content (for context)
            canonical_gist: The canonical gist (base for all audiences)
            context: Optional metadata (type, file_path, etc.)

        Returns:
            Dictionary mapping audience -> gist
            {
                "developer": "...",
                "ai": "...",
                "manager": "...",
                "personal": "..."
            }

        Algorithm (v1 - rule-based):
            developer: canonical + preserve technical terms
            ai: "Pattern: <canonical>" with structure markers
            manager: extract action + outcome (shorter)
            personal: convert to first-person narrative
        """
        context = context or {}

        gists = {}

        for audience in self.config.audiences:
            if audience == 'developer':
                gists['developer'] = self._generate_developer_gist(
                    verbatim, canonical_gist, context
                )
            elif audience == 'ai':
                gists['ai'] = self._generate_ai_gist(
                    verbatim, canonical_gist, context
                )
            elif audience == 'manager':
                gists['manager'] = self._generate_manager_gist(
                    verbatim, canonical_gist, context
                )
            elif audience == 'personal':
                gists['personal'] = self._generate_personal_gist(
                    verbatim, canonical_gist, context
                )
            else:
                # Unknown audience: use canonical
                gists[audience] = canonical_gist

        return gists

    def _generate_developer_gist(
        self,
        verbatim: str,
        canonical_gist: str,
        context: Dict
    ) -> str:
        """
        Generate developer-focused gist

        Strategy:
        - Preserve technical terms from verbatim
        - Include file/line references if available
        - Keep implementation details
        - Slightly more verbose than canonical if needed

        Example:
            Canonical: "Fixed auth bug"
            Developer: "Fixed JWT token validation in auth.py line 42"
        """
        gist = canonical_gist

        # Extract technical terms from verbatim
        tech_terms = []
        for pattern in self.tech_patterns:
            matches = re.findall(pattern, verbatim, re.IGNORECASE)
            tech_terms.extend(matches)

        # Add file context if available and not in gist
        file_path = context.get('file_path', '') or context.get('file', '')
        if file_path and file_path not in gist:
            filename = file_path.split('/')[-1]
            # Only add if gist is short enough
            if len(gist) + len(filename) < 80:
                gist = f"{gist} in {filename}"

        # Add line number if available
        line_number = context.get('line_number') or context.get('line')
        if line_number and 'line' not in gist.lower():
            if len(gist) < 70:
                gist = f"{gist} (line {line_number})"

        # Ensure we don't exceed canonical by too much (allow up to 2.5x for context)
        if len(gist) > len(canonical_gist) * 2.5:
            gist = canonical_gist

        return gist

    def _generate_ai_gist(
        self,
        verbatim: str,
        canonical_gist: str,
        context: Dict
    ) -> str:
        """
        Generate AI-focused gist

        Strategy:
        - Add structural markers for AI parsing
        - Prefix with pattern type
        - Keep concise for token efficiency
        - Make searchable/indexable

        Example:
            Canonical: "Fixed auth bug"
            AI: "Pattern: Authentication error resolution"
        """
        event_type = context.get('event_type', context.get('type', 'event'))

        # Map event types to pattern categories
        pattern_map = {
            'bugfix': 'Bug resolution',
            'error': 'Error pattern',
            'feature': 'Feature implementation',
            'refactor': 'Code refactoring',
            'test': 'Test case',
            'diagnostic': 'Diagnostic',
            'deployment': 'Deployment',
            'config': 'Configuration',
        }

        pattern_type = pattern_map.get(event_type, 'Pattern')

        # For AI, we want structured but concise
        ai_gist = f"{pattern_type}: {canonical_gist}"

        # Ensure it's not too long (AI tokens are precious)
        if len(ai_gist) > 100:
            ai_gist = f"{pattern_type}: {canonical_gist[:80]}..."

        return ai_gist

    def _generate_manager_gist(
        self,
        verbatim: str,
        canonical_gist: str,
        context: Dict
    ) -> str:
        """
        Generate manager-focused gist

        Strategy:
        - Extract action verb + outcome
        - Remove technical jargon
        - Focus on impact/result
        - Very concise (max 10 words)

        Example:
            Canonical: "Fixed JWT token validation in auth middleware"
            Manager: "Auth system stabilized"
        """
        gist = canonical_gist.lower()

        # Extract action verb
        action = None
        for verb in self.action_verbs:
            if verb in gist:
                action = verb
                break

        # Extract outcome (after action verb)
        if action:
            # Get text after action verb
            parts = gist.split(action, 1)
            if len(parts) > 1:
                outcome = parts[1].strip()

                # Remove technical details
                outcome = re.sub(r'\bin\s+[a-z]+\.(py|js|ts)\b', '', outcome)
                outcome = re.sub(r'\bline\s+\d+\b', '', outcome)
                outcome = re.sub(r'\b[A-Z]{2,}\b', '', outcome)  # Acronyms

                # Simplify
                outcome = outcome.strip()
                if outcome:
                    # Capitalize action
                    manager_gist = f"{action.capitalize()} {outcome}"

                    # Ensure short
                    words = manager_gist.split()
                    if len(words) > 10:
                        manager_gist = ' '.join(words[:10])

                    return manager_gist

        # Fallback: simplify canonical
        simplified = re.sub(r'\bin\s+[a-z]+\.(py|js|ts)\b', '', canonical_gist)
        simplified = re.sub(r'\bline\s+\d+\b', '', simplified)
        simplified = simplified.strip()

        words = simplified.split()
        if len(words) > 8:
            simplified = ' '.join(words[:8])

        return simplified

    def _generate_personal_gist(
        self,
        verbatim: str,
        canonical_gist: str,
        context: Dict
    ) -> str:
        """
        Generate personal diary-style gist

        Strategy:
        - Convert to first-person ("I fixed...")
        - Add learning/discovery angle when possible
        - Keep personal and reflective
        - Narrative style

        Example:
            Canonical: "Fixed auth bug"
            Personal: "I fixed an authentication bug and learned about JWT tokens"
        """
        gist = canonical_gist.lower()

        # Try to convert action verbs to first-person
        personal_gist = gist
        for pattern, replacement in self.personal_conversions.items():
            personal_gist = re.sub(pattern, replacement, personal_gist, count=1)

        # If no conversion happened, prefix with "I worked on"
        if personal_gist == gist:
            personal_gist = f"I worked on {gist}"

        # Add learning aspect if it's a bug/error
        if 'bug' in gist or 'error' in gist or 'issue' in gist:
            # Check if there's a technical term we "learned about"
            tech_term = None
            for pattern in self.tech_patterns:
                match = re.search(pattern, verbatim, re.IGNORECASE)
                if match:
                    tech_term = match.group(0)
                    break

            if tech_term and len(personal_gist) < 60:
                personal_gist = f"{personal_gist} and learned about {tech_term}"

        # Capitalize first letter
        if personal_gist:
            personal_gist = personal_gist[0].upper() + personal_gist[1:]

        # Ensure not too long
        if len(personal_gist) > 100:
            words = personal_gist.split()
            personal_gist = ' '.join(words[:15])

        return personal_gist

    def get_statistics(self) -> Dict[str, Any]:
        """Get generator statistics"""
        return {
            'enabled': self.config.enabled,
            'audiences': self.config.audiences,
            'use_llm': self.config.use_llm,
            'version': 'v1_rule_based',
        }


# Convenience function for quick generation
def generate_audience_gists(
    verbatim: str,
    canonical_gist: str,
    context: Optional[Dict] = None,
    config: Optional[MultiAudienceConfig] = None
) -> Dict[str, str]:
    """
    Convenience function for generating audience gists

    Example:
        >>> gists = generate_audience_gists(
        ...     verbatim="Long description...",
        ...     canonical_gist="Fixed auth bug",
        ...     context={"type": "bugfix", "file": "auth.py"}
        ... )
        >>> print(gists['developer'])
        "Fixed auth bug in auth.py"
    """
    generator = MultiAudienceGistGenerator(config=config)
    return generator.generate(verbatim, canonical_gist, context)
