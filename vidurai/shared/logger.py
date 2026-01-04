"""
Structured Logging Configuration for Vidurai
Provides correlation ID support for request tracing

Usage:
    from vidurai.shared.logger import logger, set_correlation_id
    
    # Set correlation ID for current context
    set_correlation_id("req-123")
    
    # Log with automatic correlation ID injection
    logger.info("Processing request", extra={"user_id": "user-456"})
"""

import contextvars
from loguru import logger

# Context variable for correlation ID
correlation_id_ctx = contextvars.ContextVar("correlation_id", default=None)


def correlation_id_filter(record):
    """
    Loguru filter to inject correlation ID into log records
    
    Args:
        record: Loguru log record
        
    Returns:
        bool: Always True to allow all records
    """
    cid = correlation_id_ctx.get()
    if cid:
        record["extra"]["correlation_id"] = cid
    return True


def set_correlation_id(correlation_id: str):
    """
    Set correlation ID for current context
    
    Args:
        correlation_id: Unique identifier for request/operation tracing
    """
    correlation_id_ctx.set(correlation_id)


def get_correlation_id() -> str:
    """
    Get current correlation ID
    
    Returns:
        Current correlation ID or None if not set
    """
    return correlation_id_ctx.get()


# Configure loguru with correlation ID support
logger.configure(patcher=correlation_id_filter)

# Export logger for use throughout the application
__all__ = ["logger", "set_correlation_id", "get_correlation_id"]