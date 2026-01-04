"""
Logger Setup
Configures loguru with rich terminal output and rotating file logs
"""

import sys
from pathlib import Path
from loguru import logger
from rich.console import Console

console = Console()

def setup_logger(config) -> None:
    """
    Configure loguru logger based on config settings

    Args:
        config: Config object from config_loader

    Features:
        - Rich formatted terminal output (if enabled)
        - Rotating file logs with compression (if enabled)
        - Configurable log levels
        - Audit trail in files
    """

    # Remove default handler
    logger.remove()

    # Terminal output (if enabled)
    if config.logging.terminal_output:
        logger.add(
            sys.stderr,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
            level=config.logging.level,
            colorize=True,
            backtrace=True,
            diagnose=True
        )

    # File output (if enabled)
    if config.logging.file_output:
        # Create logs directory
        log_file = Path(config.logging.log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            log_file,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
            level=config.logging.level,
            rotation="10 MB",      # Rotate when file reaches 10MB
            retention="7 days",    # Keep logs for 7 days
            compression="zip",     # Compress rotated logs
            backtrace=True,
            diagnose=True,
            enqueue=True           # Async logging for better performance
        )

    # Log initialization
    logger.info("Logger initialized")
    logger.debug(f"Log level: {config.logging.level}")
    logger.debug(f"Terminal output: {config.logging.terminal_output}")
    logger.debug(f"File output: {config.logging.file_output}")
    if config.logging.file_output:
        logger.debug(f"Log file: {config.logging.log_file}")


def get_logger():
    """
    Get the configured logger instance

    Returns:
        Loguru logger instance
    """
    return logger
