"""
Configuration for Semantic Compression

Supports both file-based config and environment variables
Environment variables take precedence over file config
"""

import os
from typing import Dict, Any
from pathlib import Path


class CompressionConfig:
    """
    Compression configuration with safe defaults

    Default: DISABLED and conservative to avoid breaking existing workflows
    """

    def __init__(self, config_dict: Dict[str, Any] = None):
        """
        Initialize from dict or use defaults

        Args:
            config_dict: Optional config dict to override defaults
        """
        # Default configuration (safe and conservative)
        self.enabled = False
        self.frequency = "manual"  # manual, daily, weekly
        self.target_ratio = 0.4  # 60% reduction
        self.min_memories_to_consolidate = 5
        self.min_salience = "LOW"  # Only consolidate LOW/NOISE
        self.max_age_days = 30  # Only consolidate old memories
        self.group_by = ["file_path"]
        self.max_group_size = 50
        self.preserve_critical = True
        self.preserve_high = True
        self.keep_originals = False  # Delete after consolidation

        # Override with provided config
        if config_dict:
            self._apply_dict(config_dict)

        # Override with environment variables (highest priority)
        self._apply_env_vars()

    def _apply_dict(self, config_dict: Dict[str, Any]):
        """Apply configuration from dictionary"""
        for key, value in config_dict.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def _apply_env_vars(self):
        """Apply configuration from environment variables"""
        # Boolean flags
        if os.getenv('VIDURAI_SEMANTIC_COMPRESSION_ENABLED'):
            self.enabled = os.getenv('VIDURAI_SEMANTIC_COMPRESSION_ENABLED').lower() == 'true'

        # String values
        if os.getenv('VIDURAI_SEMANTIC_COMPRESSION_FREQUENCY'):
            self.frequency = os.getenv('VIDURAI_SEMANTIC_COMPRESSION_FREQUENCY')

        if os.getenv('VIDURAI_SEMANTIC_COMPRESSION_MIN_SALIENCE'):
            self.min_salience = os.getenv('VIDURAI_SEMANTIC_COMPRESSION_MIN_SALIENCE')

        # Numeric values
        if os.getenv('VIDURAI_SEMANTIC_COMPRESSION_TARGET_RATIO'):
            self.target_ratio = float(os.getenv('VIDURAI_SEMANTIC_COMPRESSION_TARGET_RATIO'))

        if os.getenv('VIDURAI_SEMANTIC_COMPRESSION_MIN_MEMORIES'):
            self.min_memories_to_consolidate = int(os.getenv('VIDURAI_SEMANTIC_COMPRESSION_MIN_MEMORIES'))

        if os.getenv('VIDURAI_SEMANTIC_COMPRESSION_MAX_AGE_DAYS'):
            self.max_age_days = int(os.getenv('VIDURAI_SEMANTIC_COMPRESSION_MAX_AGE_DAYS'))

    def to_dict(self) -> Dict[str, Any]:
        """Export as dictionary"""
        return {
            'enabled': self.enabled,
            'frequency': self.frequency,
            'target_ratio': self.target_ratio,
            'min_memories_to_consolidate': self.min_memories_to_consolidate,
            'min_salience': self.min_salience,
            'max_age_days': self.max_age_days,
            'group_by': self.group_by,
            'max_group_size': self.max_group_size,
            'preserve_critical': self.preserve_critical,
            'preserve_high': self.preserve_high,
            'keep_originals': self.keep_originals,
        }

    def __repr__(self) -> str:
        return f"CompressionConfig(enabled={self.enabled}, target_ratio={self.target_ratio})"


def load_compression_config(config_file: Path = None) -> CompressionConfig:
    """
    Load compression configuration

    Priority:
    1. Environment variables (highest)
    2. Config file (if provided)
    3. Defaults (lowest)

    Args:
        config_file: Optional path to YAML config file

    Returns:
        CompressionConfig instance
    """
    config_dict = {}

    # Load from YAML file if provided
    if config_file and config_file.exists():
        try:
            import yaml
            with open(config_file, 'r') as f:
                full_config = yaml.safe_load(f)
                config_dict = full_config.get('semantic_compression', {})
        except ImportError:
            # PyYAML not installed, skip file loading
            pass
        except Exception as e:
            print(f"Warning: Failed to load config from {config_file}: {e}")

    return CompressionConfig(config_dict)
