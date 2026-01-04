"""
Configuration Loader
Loads config.yaml and merges with environment variable overrides
Provides typed, validated access to all settings
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, validator

# Pydantic models for type-safe config access

class ServerConfig(BaseModel):
    """Server configuration"""
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8080)
    cors_enabled: bool = Field(default=True)
    allowed_origins: list = Field(default=["*"])

    @validator('port')
    def validate_port(cls, v):
        if not 1024 <= v <= 65535:
            raise ValueError('Port must be between 1024 and 65535')
        return v

class ViduriConfig(BaseModel):
    """Vidurai memory management settings"""
    enable_decay: bool = Field(default=False)
    reward_profile: str = Field(default="QUALITY")
    compression_threshold: int = Field(default=10)
    min_importance: float = Field(default=0.3)
    max_working_memory: int = Field(default=10)
    max_episodic_memory: int = Field(default=1000)
    compression_enabled: bool = Field(default=True)
    compression_model: str = Field(default="gpt-4o-mini")

    @validator('reward_profile')
    def validate_profile(cls, v):
        valid = ['QUALITY', 'BALANCED', 'COST_FOCUSED', 'COST']
        if v.upper() not in valid:
            raise ValueError(f'reward_profile must be one of {valid}')
        return v.upper()

    @validator('compression_threshold')
    def validate_threshold(cls, v):
        if v < 1:
            raise ValueError('compression_threshold must be >= 1')
        return v

    @validator('min_importance')
    def validate_importance(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('min_importance must be between 0.0 and 1.0')
        return v

class ProviderConfig(BaseModel):
    """AI provider configuration"""
    base_url: str
    model_prefix: Optional[str] = None
    api_version: Optional[str] = None

class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = Field(default="INFO")
    terminal_output: bool = Field(default=True)
    file_output: bool = Field(default=True)
    log_file: str = Field(default="logs/proxy.log")

    @validator('level')
    def validate_level(cls, v):
        valid = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid:
            raise ValueError(f'level must be one of {valid}')
        return v.upper()

class SessionConfig(BaseModel):
    """Session management configuration"""
    timeout_minutes: int = Field(default=60)
    persist_memory: bool = Field(default=True)
    memory_dir: str = Field(default=".vidurai_sessions")

    @validator('timeout_minutes')
    def validate_timeout(cls, v):
        if v < 1:
            raise ValueError('timeout_minutes must be >= 1')
        return v

class MetricsConfig(BaseModel):
    """Metrics tracking configuration"""
    track_savings: bool = Field(default=True)
    show_realtime: bool = Field(default=True)
    input_cost_per_million: float = Field(default=3.0)
    output_cost_per_million: float = Field(default=15.0)

class Config(BaseModel):
    """Complete proxy configuration"""
    server: ServerConfig
    vidurai: ViduriConfig
    ai_providers: Dict[str, ProviderConfig]
    logging: LoggingConfig
    session: SessionConfig
    metrics: MetricsConfig

class ConfigLoader:
    """Load and manage proxy configuration"""

    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "config.yaml"

        self.config_path = config_path
        self._config: Optional[Config] = None

    def load(self) -> Config:
        """Load configuration from YAML with environment overrides"""

        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {self.config_path}\n"
                f"Expected: {self.config_path.absolute()}"
            )

        with open(self.config_path) as f:
            config_dict = yaml.safe_load(f)

        config_dict = self._apply_env_overrides(config_dict)

        try:
            self._config = Config(**config_dict)
        except Exception as e:
            raise ValueError(f"Invalid configuration: {e}")

        return self._config

    def _apply_env_overrides(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides"""

        if os.getenv('PROXY_HOST'):
            config_dict['server']['host'] = os.getenv('PROXY_HOST')

        if os.getenv('PROXY_PORT'):
            config_dict['server']['port'] = int(os.getenv('PROXY_PORT'))

        if os.getenv('VIDURAI_ENABLE_DECAY'):
            config_dict['vidurai']['enable_decay'] = \
                os.getenv('VIDURAI_ENABLE_DECAY').lower() == 'true'

        if os.getenv('VIDURAI_REWARD_PROFILE'):
            config_dict['vidurai']['reward_profile'] = \
                os.getenv('VIDURAI_REWARD_PROFILE')

        if os.getenv('VIDURAI_COMPRESSION_THRESHOLD'):
            config_dict['vidurai']['compression_threshold'] = \
                int(os.getenv('VIDURAI_COMPRESSION_THRESHOLD'))

        if os.getenv('VIDURAI_MIN_IMPORTANCE'):
            config_dict['vidurai']['min_importance'] = \
                float(os.getenv('VIDURAI_MIN_IMPORTANCE'))

        if os.getenv('LOG_LEVEL'):
            config_dict['logging']['level'] = os.getenv('LOG_LEVEL')

        return config_dict

    def get(self) -> Config:
        """Get loaded configuration"""
        if self._config is None:
            raise RuntimeError("Configuration not loaded. Call load() first.")
        return self._config

    def reload(self) -> Config:
        """Reload configuration from file"""
        return self.load()

# Global singleton
_config_loader: Optional[ConfigLoader] = None

def get_config_loader() -> ConfigLoader:
    """Get global ConfigLoader instance"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader

def load_config() -> Config:
    """Convenience function to load configuration"""
    loader = get_config_loader()
    return loader.load()
