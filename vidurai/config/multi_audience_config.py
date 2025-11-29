"""
Multi-Audience Gist Configuration
Phase 5: Multi-Audience Gist System

Manages configuration for audience-specific gist generation.
"""

import os
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class MultiAudienceConfig:
    """
    Configuration for multi-audience gist generation

    Attributes:
        enabled: Whether to generate audience-specific gists
        audiences: List of audience types to generate
        use_llm: Whether to use LLM for generation (v2 feature, not implemented yet)

    Environment Variables:
        VIDURAI_MULTI_AUDIENCE_ENABLED: "true" or "false"
        VIDURAI_MULTI_AUDIENCE_USE_LLM: "true" or "false" (future)
    """

    enabled: bool = field(default_factory=lambda:
        os.getenv('VIDURAI_MULTI_AUDIENCE_ENABLED', 'false').lower() == 'true'
    )

    audiences: List[str] = field(default_factory=lambda: [
        'developer',
        'ai',
        'manager',
        'personal'
    ])

    use_llm: bool = field(default_factory=lambda:
        os.getenv('VIDURAI_MULTI_AUDIENCE_USE_LLM', 'false').lower() == 'true'
    )

    # Future: per-audience configuration
    # audience_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self):
        """Validate configuration"""
        # Ensure audiences list is not empty
        if not self.audiences:
            self.audiences = ['developer', 'ai', 'manager', 'personal']

        # Remove duplicates while preserving order
        seen = set()
        unique_audiences = []
        for aud in self.audiences:
            if aud not in seen:
                seen.add(aud)
                unique_audiences.append(aud)
        self.audiences = unique_audiences

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'enabled': self.enabled,
            'audiences': self.audiences,
            'use_llm': self.use_llm,
        }


def load_multi_audience_config(
    config_dict: Dict[str, Any] = None
) -> MultiAudienceConfig:
    """
    Load multi-audience configuration

    Priority:
    1. Explicit config_dict parameter
    2. Environment variables
    3. Defaults

    Args:
        config_dict: Optional configuration dictionary

    Returns:
        MultiAudienceConfig instance

    Example:
        >>> config = load_multi_audience_config({'enabled': True})
        >>> print(config.audiences)
        ['developer', 'ai', 'manager', 'personal']
    """
    if config_dict:
        return MultiAudienceConfig(**config_dict)
    else:
        return MultiAudienceConfig()


# Convenience function for checking if feature is enabled
def is_multi_audience_enabled() -> bool:
    """Check if multi-audience gist generation is enabled"""
    config = MultiAudienceConfig()
    return config.enabled
