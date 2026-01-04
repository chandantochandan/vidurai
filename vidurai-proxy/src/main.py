"""
Vidurai Proxy Server - Main Entry Point
Universal AI memory management proxy server
"""

import os
import sys
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger

# Add parent directory to path for version import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from version import __version__

from src.utils.config_loader import load_config
from src.utils.logger import setup_logger
from src.utils.provider_detection import ProviderDetector
from src.utils.session_manager import SessionManager
from src.utils.metrics_tracker import MetricsTracker
from src.utils.terminal_ui import TerminalUI
from src.routes.proxy_routes import router, init_routes

# Global instances
config = None
session_manager = None
metrics_tracker = None
terminal_ui = None

# Detect serverless environment (Vercel, AWS Lambda, etc.)
IS_SERVERLESS = os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME") or os.getenv("LAMBDA_TASK_ROOT")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Handles startup and shutdown
    NOTE: Disabled in serverless environments
    """
    global config, session_manager, metrics_tracker, terminal_ui

    # Startup
    logger.info("Starting Vidurai Proxy Server...")

    # Load config
    config = load_config()
    setup_logger(config)

    # Initialize components
    provider_detector = ProviderDetector(config)
    session_manager = SessionManager(config)
    metrics_tracker = MetricsTracker(config)
    terminal_ui = TerminalUI(config)

    # Initialize routes
    init_routes(config, provider_detector, session_manager, metrics_tracker, terminal_ui)

    # Show startup banner
    terminal_ui.show_startup_banner()

    logger.info("Vidurai Proxy Server started successfully")

    # Yield control to FastAPI
    yield

    # Shutdown
    logger.info("Shutting down Vidurai Proxy Server...")

    # Persist all sessions
    if session_manager:
        session_manager.persist_all_sessions()

    # Show shutdown summary
    if metrics_tracker and terminal_ui:
        global_metrics = metrics_tracker.get_global_metrics()
        terminal_ui.show_shutdown({
            'requests': global_metrics['requests'],
            'tokens_saved': global_metrics['tokens_saved'],
            'cost_saved': global_metrics['cost_saved']
        })

    logger.info("Vidurai Proxy Server shutdown complete")


# Create FastAPI app (disable lifespan in serverless)
app = FastAPI(
    title="Vidurai Proxy Server",
    description="Universal AI Memory Management Proxy",
    version=__version__,
    lifespan=lifespan if not IS_SERVERLESS else None
)

# Initialize components for serverless (no lifespan support)
if IS_SERVERLESS:
    logger.info("Serverless environment detected - initializing components directly")
    config = load_config()
    # Disable file-based persistence in serverless
    config.session.persist_memory = False

    provider_detector = ProviderDetector(config)
    session_manager = SessionManager(config)
    metrics_tracker = MetricsTracker(config)
    terminal_ui = TerminalUI(config)

    # Initialize routes with components
    init_routes(config, provider_detector, session_manager, metrics_tracker, terminal_ui)
    logger.info("Serverless initialization complete")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint (must be before router with catch-all)
@app.get("/")
async def root():
    """Root endpoint with server info"""
    return {
        "service": "Vidurai Proxy Server",
        "version": __version__,
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics"
    }

# Include routes (has catch-all, so must be last)
app.include_router(router)


def main():
    """
    Main entry point for running the server
    Can be called directly or via uvicorn
    """
    import uvicorn

    # Load config for port
    cfg = load_config()

    uvicorn.run(
        "src.main:app",
        host=cfg.server.host,
        port=cfg.server.port,
        reload=False,  # Set to True for development
        log_level=cfg.logging.level.lower()
    )


if __name__ == "__main__":
    main()
