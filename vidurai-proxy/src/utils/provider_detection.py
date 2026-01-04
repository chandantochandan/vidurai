"""
Provider Detection
Auto-detect AI provider from request headers and paths
Enables transparent proxying for multiple AI providers
"""

from typing import Optional
from loguru import logger

class ProviderDetector:
    """
    Automatically detects AI provider from HTTP requests

    Detection methods:
    1. URL path patterns (e.g., /v1/messages → Anthropic)
    2. API key prefixes (e.g., sk-ant- → Anthropic)
    3. Model name patterns (e.g., claude- → Anthropic)
    """

    # Known path patterns for each provider
    PATH_PATTERNS = {
        'anthropic': ['/v1/messages', '/v1/complete', 'claude', 'anthropic'],
        'openai': ['/v1/chat/completions', '/v1/completions', '/v1/embeddings', 'openai'],
        'google': ['/v1/models/', 'generativelanguage', 'gemini', 'google']
    }

    # API key prefixes for each provider
    KEY_PREFIXES = {
        'anthropic': ['sk-ant-'],
        'openai': ['sk-'],
        'google': ['AIza']
    }

    # Model name prefixes
    MODEL_PREFIXES = {
        'anthropic': ['claude-'],
        'openai': ['gpt-', 'text-', 'davinci', 'curie'],
        'google': ['gemini-', 'palm-']
    }

    def __init__(self, config):
        """
        Initialize detector with known providers from config

        Args:
            config: Config object with ai_providers section
        """
        self.config = config
        self.known_providers = list(config.ai_providers.keys())
        logger.debug(f"ProviderDetector initialized with providers: {self.known_providers}")

    def detect(
        self,
        path: str,
        auth_header: str = "",
        model: str = ""
    ) -> str:
        """
        Detect provider from request information

        Args:
            path: Request URL path
            auth_header: Authorization header value
            model: Model name from request body (optional)

        Returns:
            Provider name (e.g., 'anthropic', 'openai', 'google')

        Detection priority:
            1. Path-based detection (most reliable)
            2. Model name detection
            3. API key detection
            4. Default to 'anthropic' (most common for Claude Code)
        """

        # Try path-based detection first (most reliable)
        provider = self._detect_from_path(path)
        if provider:
            logger.debug(f"Provider detected from path: {provider}")
            return provider

        # Try model name detection
        if model:
            provider = self._detect_from_model(model)
            if provider:
                logger.debug(f"Provider detected from model: {provider}")
                return provider

        # Try auth header detection
        if auth_header:
            provider = self._detect_from_auth(auth_header)
            if provider:
                logger.debug(f"Provider detected from auth header: {provider}")
                return provider

        # Default to anthropic (most common for Claude Code)
        logger.debug("Could not detect provider, defaulting to 'anthropic'")
        return 'anthropic'

    def _detect_from_path(self, path: str) -> Optional[str]:
        """
        Detect provider from URL path

        Args:
            path: Request URL path

        Returns:
            Provider name or None
        """
        path_lower = path.lower()

        for provider, patterns in self.PATH_PATTERNS.items():
            if provider not in self.known_providers:
                continue

            for pattern in patterns:
                if pattern in path_lower:
                    return provider

        return None

    def _detect_from_auth(self, auth_header: str) -> Optional[str]:
        """
        Detect provider from API key format

        Args:
            auth_header: Authorization header (e.g., "Bearer sk-ant-...")

        Returns:
            Provider name or None
        """
        # Extract key from "Bearer <key>" format
        key = auth_header.replace('Bearer ', '').replace('bearer ', '').strip()

        if not key:
            return None

        for provider, prefixes in self.KEY_PREFIXES.items():
            if provider not in self.known_providers:
                continue

            for prefix in prefixes:
                if key.startswith(prefix):
                    return provider

        return None

    def _detect_from_model(self, model: str) -> Optional[str]:
        """
        Detect provider from model name

        Args:
            model: Model name (e.g., "claude-3-opus", "gpt-4")

        Returns:
            Provider name or None
        """
        model_lower = model.lower()

        for provider, prefixes in self.MODEL_PREFIXES.items():
            if provider not in self.known_providers:
                continue

            for prefix in prefixes:
                if model_lower.startswith(prefix):
                    return provider

        return None

    def get_provider_config(self, provider: str):
        """
        Get configuration for detected provider

        Args:
            provider: Provider name

        Returns:
            ProviderConfig object from configuration

        Raises:
            ValueError: If provider not configured
        """
        if provider not in self.config.ai_providers:
            raise ValueError(
                f"Provider '{provider}' not configured. "
                f"Available providers: {self.known_providers}"
            )

        return self.config.ai_providers[provider]

    def get_target_url(self, provider: str, path: str) -> str:
        """
        Construct target URL for forwarding request

        Args:
            provider: Provider name
            path: Original request path

        Returns:
            Complete URL for forwarding (e.g., https://api.anthropic.com/v1/messages)
        """
        provider_config = self.get_provider_config(provider)
        base_url = provider_config.base_url.rstrip('/')

        # Clean path
        clean_path = path.lstrip('/')

        return f"{base_url}/{clean_path}"
