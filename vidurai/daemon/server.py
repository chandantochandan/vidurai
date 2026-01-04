#!/usr/bin/env python3
"""
Vidurai Ghost Daemon - The Invisible Infrastructure Layer
Runs as OS-level service, provides universal context to all AI tools

v2.1: Added Named Pipe IPC transport for VS Code extension
v2.2: Added Archiver, Retention, Pinning integrations
v2.2.0-Guardian: Moved to vidurai.daemon package (Phase 7.0)

Path Safety Rule: All data paths use Path.home() / ".vidurai"
Explicit Import Rule: All imports are relative or absolute (no implicit)
"""

import os
import sys
import asyncio
from pathlib import Path
import logging
import logging.handlers
from typing import Set, Dict, Any, Optional
from datetime import datetime
import json
from threading import Thread
from queue import Queue

# CRITICAL: Set Windows Proactor Event Loop BEFORE any other asyncio imports
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import uvicorn

# Phase 7.0: Relative imports within the daemon package
from .auto_detector import AutoDetector
from .metrics_collector import MetricsCollector
from .mcp_bridge import MCPBridge
from .smart_file_watcher import SmartFileWatcher
from .intelligence.context_mediator import ContextMediator

# Project Brain imports (relative)
from .project_brain import ProjectScanner, ErrorWatcher, ContextBuilder, MemoryStore

# Version (relative import)
from .version import __version__

# IPC Server (v2.1 - Named Pipe transport, relative)
from .ipc import IPCServer, IPCMessage, IPCResponse, IPC_PROTOCOL_VERSION, get_pipe_path

# v2.2: Archiver and Retention (relative)
from .archiver.archiver import get_archiver, ArchiverOptions

# v2.2: Database and Pinning
from vidurai.storage.database import MemoryDatabase
from vidurai.core.retention_policy import create_retention_policy, RetentionContext, RetentionAction
from vidurai.core.memory_pinning import MemoryPinManager

# v2.3: Vismriti AI Memory Engine (SDK Integration)
from vidurai.vismriti_memory import VismritiMemory
from .intelligence.event_adapter import EventAdapter

# v2.4: Cognitive Control API - RewardProfile for dynamic RL agent configuration
try:
    from vidurai.core.rl_agent_v2 import RewardProfile
    REWARD_PROFILE_AVAILABLE = True
except ImportError:
    REWARD_PROFILE_AVAILABLE = False
    RewardProfile = None

# v2.6 Glass Box Protocol: SearchController is the SINGLE entry point for context
# This replaces all inline `from vidurai.core.oracle import get_oracle` calls
from vidurai.core.controllers.search_controller import get_controller, SearchController

# v2.7 Phase 3: StateLinker for user focus tracking (Reality Grounding)
from vidurai.core.state import StateLinker

# Phase 7.1: Log Rotation (The Disk Saver)
# Use RotatingFileHandler to prevent vidurai.log from growing infinitely
VIDURAI_HOME = Path.home() / ".vidurai"
VIDURAI_HOME.mkdir(parents=True, exist_ok=True)
LOG_FILE = VIDURAI_HOME / "vidurai.log"

# Configure root logger with both console and rotating file handlers
logger = logging.getLogger("vidurai.daemon")
logger.setLevel(logging.INFO)

# Console handler for debugging
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))

# Rotating file handler: 10MB max, keep 5 backups
file_handler = logging.handlers.RotatingFileHandler(
    LOG_FILE,
    maxBytes=10_000_000,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))

# Add handlers
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Also configure basicConfig for other loggers
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

app = FastAPI(
    title="Vidurai Ghost Daemon",
    version=__version__,
    description="Universal AI Context Protocol"
)

# CORS for browser extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
watched_projects: Dict[str, Observer] = {}
active_websockets: Set[WebSocket] = set()
event_queue: Queue = Queue()
metrics = {
    "files_watched": 0,
    "changes_detected": 0,
    "tokens_saved": 0,
    "contexts_served": 0,
    "started_at": datetime.now().isoformat(),
    "last_activity": None
}

# Global instances
auto_detector = AutoDetector()
metrics_collector = MetricsCollector()
mcp_bridge = MCPBridge()
context_mediator = ContextMediator()

# Project Brain instances
memory_store = MemoryStore()
project_scanner = ProjectScanner(memory_store)
error_watcher = ErrorWatcher()
context_builder = ContextBuilder(project_scanner, error_watcher)

# IPC Server instance (v2.1)
ipc_server: Optional[IPCServer] = None

# v2.2: Archiver, Database, Retention, and Pinning instances
archiver = None
memory_db: Optional[MemoryDatabase] = None
pin_manager: Optional[MemoryPinManager] = None
retention_task: Optional[asyncio.Task] = None

# v2.3: Vismriti AI Memory Engine instance
vismriti_brain: Optional[VismritiMemory] = None

# v2.6 Glass Box Protocol: SearchController singleton (initialized after brain)
search_controller: Optional[SearchController] = None

# v2.7 Phase 3: StateLinker singleton for user focus tracking
state_linker: Optional[StateLinker] = None


async def _remember_async(memory_args: Dict[str, Any]) -> None:
    """
    Async Firewall (Commandment II): Offload SDK calls to thread pool.
    This prevents blocking the event loop if SDK operations are slow.
    """
    global vismriti_brain
    if not memory_args:
        logger.debug("[Vismriti] Skipped: no memory_args")
        return
    # NOTE: Must use `is None` not truthiness because VismritiMemory.__len__
    # returns 0 when empty, causing `not vismriti_brain` to be True!
    if vismriti_brain is None:
        logger.warning("[Vismriti] Skipped: brain not initialized yet")
        return
    try:
        logger.info(f"[Vismriti] Storing: {memory_args['content'][:60]}...")
        await asyncio.to_thread(
            vismriti_brain.remember,
            content=memory_args['content'],
            metadata=memory_args.get('metadata'),
            salience=memory_args.get('salience'),
            extract_gist=memory_args.get('extract_gist', False)
        )
        logger.info(f"[Vismriti] ✓ Stored successfully")
    except Exception as e:
        logger.error(f"[Vismriti] Remember failed: {e}")


async def handle_ipc_message(client, message: IPCMessage) -> IPCResponse:
    """
    Handle incoming IPC messages from VS Code extension.

    This is the main entry point for all IPC communication.
    Maps IPC message types to internal handlers.
    """
    # v2.4: Declare globals that are modified in background task
    global vismriti_brain

    try:
        msg_type = message.type
        msg_data = message.data or {}

        logger.debug(f"IPC: Received {msg_type} from client {client.id}")

        # v2.5: ATOMIC CONTEXT SWITCH (Rule IV: Switch-First Commandment)
        # Detect and handle project context switch BEFORE any processing.
        # This ensures all subsequent sdk.remember() calls go to the correct project.
        # Rule II: Use .get() chains for None-safety on untrusted IPC input
        project_root = msg_data.get('project_path') or msg_data.get('project')
        if not project_root and message.data:
            project_root = message.data.get('project_root')

        if project_root and vismriti_brain is not None:
            try:
                # Normalize path to absolute for consistent comparison
                project_root = os.path.abspath(project_root)

                # Context Guard: Validate project path exists
                if not os.path.exists(project_root):
                    logger.warning(f"⚠️ Invalid project path (not found): {project_root}")
                    # Don't crash - just skip the switch
                else:
                    if vismriti_brain.project_path != project_root:
                        logger.info(f"🔀 RPC Context Switch: {vismriti_brain.project_path} -> {project_root}")
                        # RULE IV: Assignment MUST happen FIRST before any other processing
                        vismriti_brain.project_path = project_root
            except Exception as e:
                # Context Guard: Don't crash the Daemon on path errors
                logger.error(f"❌ Context switch failed: {e}")

        # Ping/Pong for connection testing
        if msg_type == 'ping':
            return IPCResponse(type='pong', id=message.id, ok=True)

        # Phase 7.0: Handshake Protocol
        # Client must send handshake immediately after connect
        elif msg_type == 'handshake':
            client_name = msg_data.get('client_name', 'unknown')
            client_version = msg_data.get('version', 'unknown')

            # Store client metadata
            client.complete_handshake(client_name, client_version)

            return IPCResponse(
                type='handshake_ack',
                id=message.id,
                ok=True,
                data={
                    'server_version': __version__,
                    'protocol_version': IPC_PROTOCOL_VERSION,
                    'client_id': client.id,
                    'message': f'Welcome {client_name} v{client_version}'
                }
            )

        # File edit events from extension
        elif msg_type == 'file_edit':
            file_path = msg_data.get('file', '')
            gist = msg_data.get('gist', '')
            change_type = msg_data.get('change', 'modify')

            # Add to context mediator
            event = {
                'event': 'file_changed',
                'path': file_path,
                'gist': gist,
                'change_type': change_type,
                'timestamp': datetime.now().isoformat(),
                'source': 'ipc'
            }
            context_mediator.add_event(event)

            # Update metrics
            metrics["changes_detected"] += 1
            metrics["last_activity"] = datetime.now().isoformat()

            # Broadcast to WebSocket clients
            await broadcast_event(event)

            # v2.3: Send to Vismriti AI Memory Engine (Async Firewall)
            memory_args = EventAdapter.adapt(msg_data, 'file_edit')
            if memory_args:
                asyncio.create_task(_remember_async(memory_args))

            return IPCResponse(type='ack', id=message.id, ok=True)

        # Terminal events from extension
        elif msg_type == 'terminal':
            cmd = msg_data.get('cmd', '')
            code = msg_data.get('code')
            output = msg_data.get('out', '')
            error_output = msg_data.get('err', '')

            # Add to context mediator
            event = {
                'event': 'terminal_output',
                'command': cmd,
                'exit_code': code,
                'output': output,
                'error': error_output,
                'timestamp': datetime.now().isoformat(),
                'source': 'ipc'
            }
            context_mediator.add_event(event)

            # If error, capture it
            if code != 0 and error_output:
                try:
                    error_ctx = error_watcher.capture_error_context(error_output, cmd)
                    memory_store.save_error(error_ctx)
                except Exception as e:
                    logger.error(f"Failed to capture terminal error: {e}")

            # v2.3: Send to Vismriti AI Memory Engine (Async Firewall)
            memory_args = EventAdapter.adapt(msg_data, 'terminal')
            if memory_args:
                asyncio.create_task(_remember_async(memory_args))

            return IPCResponse(type='ack', id=message.id, ok=True)

        # Diagnostic events from extension
        elif msg_type == 'diagnostic':
            file_path = msg_data.get('file', '')
            severity = msg_data.get('sev', 0)
            msg_text = msg_data.get('msg', '')
            line = msg_data.get('ln')

            severity_map = {0: 'error', 1: 'warning', 2: 'info', 3: 'hint'}

            event = {
                'event': 'diagnostic',
                'file': file_path,
                'severity': severity_map.get(severity, 'error'),
                'message': msg_text,
                'line': line,
                'timestamp': datetime.now().isoformat(),
                'source': 'ipc'
            }
            context_mediator.add_event(event)

            # v2.2: Update active_state table (Zombie Killer pattern)
            # Errors/warnings → UPSERT, Info/hint → DELETE (file is clean)
            if memory_db and file_path:
                try:
                    if severity in (0, 1):  # error or warning
                        error_count = 1 if severity == 0 else 0
                        warning_count = 1 if severity == 1 else 0
                        memory_db.upsert_file_state(
                            file_path=file_path,
                            project_path=msg_data.get('project', ''),
                            has_errors=(severity == 0),
                            error_count=error_count,
                            warning_count=warning_count,
                            error_summary=msg_text[:200] if msg_text else ''
                        )
                    else:  # info or hint → file is clean
                        memory_db.clear_file_state(file_path)
                except Exception as e:
                    logger.debug(f"Active state update error (non-fatal): {e}")

            # v2.3: Send to Vismriti AI Memory Engine (Async Firewall)
            # Note: EventAdapter returns None for info/hint (Zombie Killer compliance)
            memory_args = EventAdapter.adapt(msg_data, 'diagnostic')
            if memory_args:
                asyncio.create_task(_remember_async(memory_args))

            return IPCResponse(type='ack', id=message.id, ok=True)

        # Context request from extension
        elif msg_type == 'context':
            query = msg_data.get('query', '')
            max_tokens = msg_data.get('maxTokens', 2000)

            # Build context
            context = context_builder.build_context(
                trigger_type="ipc_request",
                user_prompt=query
            )
            formatted = context_builder.format_context(context, "claude_code")

            metrics["contexts_served"] += 1

            return IPCResponse(
                type='context',
                id=message.id,
                ok=True,
                data={
                    'context': formatted,
                    'count': len(context.get('memories', [])),
                    'tokens': len(formatted) // 4  # Rough estimate
                }
            )

        # Stats request
        elif msg_type == 'stats':
            return IPCResponse(
                type='stats',
                id=message.id,
                ok=True,
                data={
                    'projects': len(watched_projects),
                    'files': metrics.get('files_watched', 0),
                    'changes': metrics.get('changes_detected', 0),
                    'contexts': metrics.get('contexts_served', 0),
                    'uptime': (datetime.now() - datetime.fromisoformat(metrics["started_at"])).total_seconds()
                }
            )

        # Recall memories
        elif msg_type == 'recall':
            query = msg_data.get('query', '')
            limit = msg_data.get('limit', 10)

            # Use context mediator for recall
            memories = context_mediator.get_recent_events(limit)

            return IPCResponse(
                type='recall',
                id=message.id,
                ok=True,
                data={
                    'memories': memories,
                    'count': len(memories)
                }
            )

        # v2.1: Request-response pattern (Oracle API)
        # v2.6 Glass Box Protocol: All context queries go through SearchController
        elif msg_type == 'request':
            method = msg_data.get('method', '')
            params = msg_data.get('params', {})

            if method == 'get_context':
                # v2.6 Glass Box Protocol: Use SearchController (single entry point)
                try:
                    # Ensure controller is initialized with latest dependencies
                    controller = get_controller(
                        brain_instance=vismriti_brain,
                        whisperer=context_mediator.whisperer,
                        pin_manager=pin_manager
                    )

                    audience = params.get('audience', 'developer')
                    project = params.get('project_path')
                    include_raw = params.get('include_raw', False)

                    # v2.5 Audience Profiles: Pass client's intent raw, let Oracle decide defaults
                    # If client sends include_memories=True/False, Oracle respects it (Rule I: User Veto)
                    # If client sends nothing (None), Oracle uses AUDIENCE_PROFILES default
                    client_include_memories = params.get('include_memories')  # None if not specified

                    # v2.5: Context Guard - Fall back to brain's project if not specified
                    if not project and vismriti_brain:
                        project = vismriti_brain.project_path
                        logger.debug(f"[get_context] Using brain's project: {project}")

                    # v2.5: Guard - Return error if no project context available
                    if not project:
                        logger.warning("[get_context] No active project context")
                        return IPCResponse(
                            type='response',
                            id=message.id,
                            ok=False,
                            error="No active project context. Open a folder in VS Code first."
                        )

                    # v2.6 Glass Box: Controller wraps Oracle with standardized error handling
                    ctx_response = controller.get_context(
                        audience=audience,
                        project_path=project,
                        include_raw=include_raw,
                        include_memories=client_include_memories  # Pass None to let Oracle decide
                    )

                    if not ctx_response.success:
                        return IPCResponse(
                            type='response',
                            id=message.id,
                            ok=False,
                            error=ctx_response.error or "Context retrieval failed"
                        )

                    # v2.5: Combined context is now the Oracle's formatted output
                    # (memories/pins included based on AUDIENCE_PROFILES)
                    combined_context = ctx_response.formatted
                    memory_context = None  # Kept for backwards compatibility in response

                    return IPCResponse(
                        type='response',
                        id=message.id,
                        ok=True,
                        data={
                            'context': combined_context,
                            'oracle_context': ctx_response.formatted,
                            'memory_context': memory_context,
                            'files_with_errors': ctx_response.files_with_errors,
                            'total_errors': ctx_response.total_errors,
                            'total_warnings': ctx_response.total_warnings,
                            'audience': ctx_response.audience,
                            'timestamp': ctx_response.timestamp,
                            'raw': None  # Raw data not in ContextResponse
                        }
                    )
                except Exception as e:
                    logger.error(f"SearchController error: {e}")
                    return IPCResponse(
                        type='response',
                        id=message.id,
                        ok=False,
                        error=f"SearchController error: {str(e)}"
                    )

            elif method == 'get_file_state':
                # Query state for a specific file
                # Note: get_file_context is Oracle-specific, accessed via controller.oracle
                try:
                    controller = get_controller(
                        brain_instance=vismriti_brain,
                        whisperer=context_mediator.whisperer,
                        pin_manager=pin_manager
                    )

                    file_path = params.get('file_path', '')
                    if not file_path:
                        return IPCResponse(
                            type='response',
                            id=message.id,
                            ok=False,
                            error="file_path is required"
                        )

                    # Access Oracle through controller for file-specific queries
                    state = controller.oracle.get_file_context(file_path)

                    return IPCResponse(
                        type='response',
                        id=message.id,
                        ok=True,
                        data={
                            'file_path': file_path,
                            'has_issues': state is not None,
                            'state': state
                        }
                    )
                except Exception as e:
                    logger.error(f"File state error: {e}")
                    return IPCResponse(
                        type='response',
                        id=message.id,
                        ok=False,
                        error=str(e)
                    )

            elif method == 'get_summary':
                # Quick summary of current state
                # v2.6 Glass Box: Use SearchController.get_summary()
                try:
                    controller = get_controller(
                        brain_instance=vismriti_brain,
                        whisperer=context_mediator.whisperer,
                        pin_manager=pin_manager
                    )

                    project = params.get('project_path')
                    summary = controller.get_summary(project)

                    return IPCResponse(
                        type='response',
                        id=message.id,
                        ok=True,
                        data=summary
                    )
                except Exception as e:
                    logger.error(f"Summary error: {e}")
                    return IPCResponse(
                        type='response',
                        id=message.id,
                        ok=False,
                        error=str(e)
                    )

            elif method == 'get_dashboard_state':
                # v2.2: Glass Box Dashboard state
                # v2.6 Glass Box: Use SearchController.get_dashboard_summary()
                try:
                    controller = get_controller(
                        brain_instance=vismriti_brain,
                        whisperer=context_mediator.whisperer,
                        pin_manager=pin_manager
                    )

                    project = params.get('project_path')
                    dashboard = controller.get_dashboard_summary(project)

                    return IPCResponse(
                        type='response',
                        id=message.id,
                        ok=True,
                        data=dashboard
                    )
                except Exception as e:
                    logger.error(f"Dashboard state error: {e}")
                    return IPCResponse(
                        type='response',
                        id=message.id,
                        ok=False,
                        error=str(e)
                    )

            else:
                return IPCResponse(
                    type='response',
                    id=message.id,
                    ok=False,
                    error=f"Unknown method: {method}"
                )

        # v2.2: Pin memory (supports memory_id OR file_path)
        elif msg_type == 'pin':
            try:
                memory_id = msg_data.get('memory_id')
                file_path = msg_data.get('file_path')
                project_path = msg_data.get('project_path', '')
                reason = msg_data.get('reason', 'User pinned')

                if not memory_id and not file_path:
                    return IPCResponse(
                        type='error',
                        id=message.id,
                        ok=False,
                        error="memory_id or file_path is required"
                    )

                if pin_manager:
                    if file_path:
                        # Pin by file path (creates placeholder if needed)
                        success = pin_manager.pin_by_path(
                            file_path=file_path,
                            project_path=project_path,
                            reason=reason,
                            pinned_by='user'
                        )
                        return IPCResponse(
                            type='ack',
                            id=message.id,
                            ok=success,
                            data={'pinned': success, 'file_path': file_path}
                        )
                    else:
                        # Pin by memory ID
                        success = pin_manager.pin(
                            memory_id=memory_id,
                            reason=reason,
                            pinned_by='user'
                        )
                        return IPCResponse(
                            type='ack',
                            id=message.id,
                            ok=success,
                            data={'pinned': success, 'memory_id': memory_id}
                        )
                else:
                    return IPCResponse(
                        type='error',
                        id=message.id,
                        ok=False,
                        error="Pin manager not initialized"
                    )
            except Exception as e:
                logger.error(f"Pin error: {e}")
                return IPCResponse(
                    type='error',
                    id=message.id,
                    ok=False,
                    error=str(e)
                )

        # v2.2: Unpin memory (supports memory_id OR file_path)
        elif msg_type == 'unpin':
            try:
                memory_id = msg_data.get('memory_id')
                file_path = msg_data.get('file_path')
                project_path = msg_data.get('project_path', '')

                if not memory_id and not file_path:
                    return IPCResponse(
                        type='error',
                        id=message.id,
                        ok=False,
                        error="memory_id or file_path is required"
                    )

                if pin_manager:
                    if file_path:
                        # Unpin by file path - find memory ID first
                        success = pin_manager.unpin_by_path(
                            file_path=file_path,
                            project_path=project_path
                        )
                        return IPCResponse(
                            type='ack',
                            id=message.id,
                            ok=success,
                            data={'unpinned': success, 'file_path': file_path}
                        )
                    else:
                        # Unpin by memory ID
                        success = pin_manager.unpin(memory_id=memory_id)
                        return IPCResponse(
                            type='ack',
                            id=message.id,
                            ok=success,
                            data={'unpinned': success, 'memory_id': memory_id}
                        )
                else:
                    return IPCResponse(
                        type='error',
                        id=message.id,
                        ok=False,
                        error="Pin manager not initialized"
                    )
            except Exception as e:
                logger.error(f"Unpin error: {e}")
                return IPCResponse(
                    type='error',
                    id=message.id,
                    ok=False,
                    error=str(e)
                )

        # v2.2: Get pinned memories
        elif msg_type == 'get_pinned':
            try:
                project_path = msg_data.get('project_path', '')

                if pin_manager:
                    pinned = pin_manager.get_pinned_memories(project_path)
                    return IPCResponse(
                        type='response',
                        id=message.id,
                        ok=True,
                        data={
                            'pinned': pinned,
                            'count': len(pinned)
                        }
                    )
                else:
                    return IPCResponse(
                        type='error',
                        id=message.id,
                        ok=False,
                        error="Pin manager not initialized"
                    )
            except Exception as e:
                logger.error(f"Get pinned error: {e}")
                return IPCResponse(
                    type='error',
                    id=message.id,
                    ok=False,
                    error=str(e)
                )

        # v2.7 Phase 3: Focus update from VS Code (StateLinker)
        elif msg_type == 'focus':
            try:
                file_path = msg_data.get('file', '')
                line = msg_data.get('line')
                column = msg_data.get('column')
                selection = msg_data.get('selection', '')
                project_root = msg_data.get('project_root') or msg_data.get('project_path')

                # Glass Box: Reality Grounding - StateLinker validates paths exist
                if state_linker:
                    success = state_linker.update_focus({
                        'file': file_path,
                        'line': line,
                        'column': column,
                        'selection': selection,
                        'project_root': project_root
                    })

                    if success:
                        logger.debug(f"[StateLinker] Focus updated: {file_path}:{line}")
                        return IPCResponse(
                            type='ack',
                            id=message.id,
                            ok=True,
                            data={
                                'file': file_path,
                                'line': line,
                                'accepted': True
                            }
                        )
                    else:
                        # Reality Grounding: Path failed validation
                        logger.debug(f"[StateLinker] Focus rejected (file not found): {file_path}")
                        return IPCResponse(
                            type='ack',
                            id=message.id,
                            ok=False,
                            data={'accepted': False, 'reason': 'file_not_found'}
                        )
                else:
                    return IPCResponse(
                        type='error',
                        id=message.id,
                        ok=False,
                        error="StateLinker not initialized"
                    )

            except Exception as e:
                logger.error(f"Focus update error: {e}")
                return IPCResponse(
                    type='error',
                    id=message.id,
                    ok=False,
                    error=str(e)
                )

        # v2.7 Phase 3: Get current user state (StateLinker)
        elif msg_type == 'get_focus':
            try:
                if state_linker:
                    active_file = state_linker.get_active_file()
                    active_line = state_linker.get_active_line()
                    selection = state_linker.get_selection()
                    recent_files = state_linker.get_recent_files(limit=5)

                    return IPCResponse(
                        type='response',
                        id=message.id,
                        ok=True,
                        data={
                            'active_file': str(active_file) if active_file else None,
                            'active_line': active_line,
                            'selection': selection,
                            'recent_files': [str(f) for f in recent_files],
                            'stats': state_linker.get_stats()
                        }
                    )
                else:
                    return IPCResponse(
                        type='error',
                        id=message.id,
                        ok=False,
                        error="StateLinker not initialized"
                    )

            except Exception as e:
                logger.error(f"Get focus error: {e}")
                return IPCResponse(
                    type='error',
                    id=message.id,
                    ok=False,
                    error=str(e)
                )

        # v2.7 Phase 3: Resolve fuzzy path (StateLinker)
        elif msg_type == 'resolve_path':
            try:
                partial_path = msg_data.get('path', '')

                if not partial_path:
                    return IPCResponse(
                        type='error',
                        id=message.id,
                        ok=False,
                        error="path is required"
                    )

                if state_linker:
                    resolved = state_linker.resolve_fuzzy_path(partial_path)

                    return IPCResponse(
                        type='response',
                        id=message.id,
                        ok=resolved is not None,
                        data={
                            'partial': partial_path,
                            'resolved': str(resolved) if resolved else None,
                            'found': resolved is not None
                        }
                    )
                else:
                    return IPCResponse(
                        type='error',
                        id=message.id,
                        ok=False,
                        error="StateLinker not initialized"
                    )

            except Exception as e:
                logger.error(f"Resolve path error: {e}")
                return IPCResponse(
                    type='error',
                    id=message.id,
                    ok=False,
                    error=str(e)
                )

        # v2.4: Cognitive Control API - Set RL Agent configuration
        elif msg_type == 'set_config':
            try:
                profile_str = msg_data.get('profile', '')

                # Validate profile value
                valid_profiles = ['cost_focused', 'balanced', 'quality_focused']
                if profile_str not in valid_profiles:
                    return IPCResponse(
                        type='error',
                        id=message.id,
                        ok=False,
                        error=f"Invalid profile: '{profile_str}'. Valid options: {valid_profiles}"
                    )

                # Check if RewardProfile is available
                if not REWARD_PROFILE_AVAILABLE:
                    return IPCResponse(
                        type='error',
                        id=message.id,
                        ok=False,
                        error="RewardProfile not available (RL agent module not loaded)"
                    )

                # Check if Vismriti brain is initialized
                # NOTE: Must use `is None` not truthiness because VismritiMemory.__len__
                # returns 0 when empty, causing `not vismriti_brain` to be True!
                if vismriti_brain is None:
                    return IPCResponse(
                        type='error',
                        id=message.id,
                        ok=False,
                        error="Vismriti brain not initialized yet"
                    )

                # Check if RL agent is enabled
                if not vismriti_brain.rl_agent:
                    return IPCResponse(
                        type='error',
                        id=message.id,
                        ok=False,
                        error="RL agent not enabled. Initialize VismritiMemory with enable_rl_agent=True"
                    )

                # Map string to RewardProfile enum
                profile_map = {
                    'cost_focused': RewardProfile.COST_FOCUSED,
                    'balanced': RewardProfile.BALANCED,
                    'quality_focused': RewardProfile.QUALITY_FOCUSED
                }
                new_profile = profile_map[profile_str]
                old_profile = vismriti_brain.rl_agent.reward_profile

                # Update the RL agent's reward profile
                vismriti_brain.rl_agent.reward_profile = new_profile

                logger.info(f"[Cognitive Control] Profile changed: {old_profile.value} -> {new_profile.value}")

                return IPCResponse(
                    type='ack',
                    id=message.id,
                    ok=True,
                    data={
                        'profile': new_profile.value,
                        'previous_profile': old_profile.value,
                        'message': f"RL agent profile updated to: {new_profile.value}"
                    }
                )

            except Exception as e:
                logger.error(f"set_config error: {e}")
                return IPCResponse(
                    type='error',
                    id=message.id,
                    ok=False,
                    error=str(e)
                )

        # Unknown message type
        else:
            logger.warning(f"IPC: Unknown message type: {msg_type}")
            return IPCResponse(
                type='error',
                id=message.id,
                ok=False,
                error=f"Unknown message type: {msg_type}"
            )

    except Exception as e:
        logger.error(f"IPC: Error handling message: {e}")
        return IPCResponse(
            type='error',
            id=message.id,
            ok=False,
            error=str(e)
        )

# Pydantic models
class ContextRequest(BaseModel):
    user_prompt: str
    ai_platform: str = "Unknown"

class ErrorReport(BaseModel):
    error_text: str
    command: Optional[str] = None

class SmartContextRequest(BaseModel):
    user_prompt: str = ""
    platform: str = "chatgpt_web"  # chatgpt_web, claude_code, terminal


class RPCRequest(BaseModel):
    """
    HTTP RPC Bridge request model.
    Allows Python scripts and Jupyter notebooks to talk to the Daemon.
    """
    type: str  # Message type (e.g., 'request', 'pin', 'context')
    data: Optional[Dict[str, Any]] = None
    id: Optional[str] = None  # Optional request ID for correlation
    project_path: Optional[str] = None  # Context switch hint


class ViduraiFileHandler(FileSystemEventHandler):
    """Watches file changes and broadcasts via WebSocket"""

    def __init__(self, project_path: str):
        self.project_path = project_path
        super().__init__()

    def should_ignore(self, path: str) -> bool:
        """Check if path should be ignored"""
        ignore_patterns = {
            '.git', 'node_modules', '__pycache__', '.venv', 'venv',
            'dist', 'build', '.next', 'target', '.pytest_cache'
        }

        path_obj = Path(path)
        return any(pattern in path_obj.parts for pattern in ignore_patterns)

    def on_modified(self, event):
        if event.is_directory or self.should_ignore(event.src_path):
            return

        file_path = Path(event.src_path)

        logger.info(f"📝 File changed: {file_path.name}")
        metrics["changes_detected"] += 1
        metrics["last_activity"] = datetime.now().isoformat()

        # Put event in queue for async processing
        event_queue.put({
            "event": "file_changed",
            "path": str(file_path),
            "project": self.project_path,
            "filename": file_path.name,
            "timestamp": datetime.now().isoformat()
        })

async def broadcast_event(message: Dict[str, Any]):
    """Send event to all WebSocket clients"""
    dead_connections = set()

    for ws in active_websockets:
        try:
            await ws.send_json(message)
        except:
            dead_connections.add(ws)

    # Clean up dead connections
    active_websockets.difference_update(dead_connections)

    if dead_connections:
        logger.info(f"🧹 Cleaned {len(dead_connections)} dead connections")

async def process_event_queue():
    """Background task to process file events from queue"""
    while True:
        try:
            if not event_queue.empty():
                event = event_queue.get_nowait()

                # Add event to context mediator for intelligence
                context_mediator.add_event(event)

                # Broadcast to WebSocket clients
                await broadcast_event(event)
            await asyncio.sleep(0.1)  # Small delay to avoid busy loop
        except Exception as e:
            logger.error(f"Error processing event queue: {e}")
            await asyncio.sleep(1)

@app.on_event("startup")
async def startup_event():
    """Start background tasks and auto-detect projects on app startup"""
    global ipc_server

    # 🧠 BRAIN BIOPSY: Prove correct SDK is loaded
    try:
        import vidurai
        logger.info(f"🧠 LOADED SDK VERSION: {vidurai.__version__}")
        logger.info(f"📍 SDK LOCATION: {vidurai.__file__}")
    except Exception as e:
        logger.warning(f"⚠️ SDK verification failed: {e}")

    # Start event queue processor
    asyncio.create_task(process_event_queue())

    # Start IPC Server FIRST (v2.2: Fast startup - <200ms to listening)
    logger.info("")
    logger.info("🔌 Starting IPC Server...")
    try:
        ipc_server = IPCServer(message_handler=handle_ipc_message)
        await ipc_server.start()
        logger.info(f"   ✓ IPC listening on: {ipc_server.pipe_path}")
    except Exception as e:
        logger.error(f"   ✗ Failed to start IPC server: {e}")
        logger.error("     VS Code extension will not be able to connect via Named Pipe")
        ipc_server = None

    # ⚡ DAEMON IS NOW READY FOR CONNECTIONS
    logger.info("")
    logger.info("⚡ Daemon ready for IPC! (Background initialization starting...)")
    logger.info("")

    # v2.2: Move all heavy initialization to background task
    asyncio.create_task(_background_initialization())


async def _background_initialization():
    """
    Background initialization task (v2.2).
    Runs heavy operations without blocking IPC server startup.
    """
    global archiver, memory_db, pin_manager, retention_task, vismriti_brain

    import time
    start_time = time.time()

    # Process any offline buffer files
    try:
        from ipc import scan_buffer_files, process_buffer_files
        buffer_files = scan_buffer_files()
        if buffer_files:
            logger.info(f"📦 Found {len(buffer_files)} offline buffer file(s)")
            stats = await process_buffer_files(handle_ipc_message)
            logger.info(f"   ✓ Processed {stats['events']} buffered events from {stats['files']} file(s)")
            if stats['errors'] > 0:
                logger.warning(f"   ⚠ {stats['errors']} buffer processing errors")
    except Exception as e:
        logger.debug(f"Buffer processing skipped: {e}")

    logger.info("🚀 Running auto-detection...")
    logger.info("")

    # Detect editors
    editors = auto_detector.detect_active_editors()
    if editors:
        logger.info(f"📝 Detected editors: {', '.join(editors.keys())}")

    # Auto-discover projects
    projects = auto_detector.auto_discover_projects(max_projects=5)

    logger.info("")
    logger.info(f"👁️  Auto-watching {len(projects)} projects...")

    # Watch each project
    for project in projects:
        try:
            result = await watch_project(str(project))
            if result.get("status") == "watching":
                logger.info(f"   ✓ Watching: {project.name}")
        except Exception as e:
            logger.error(f"   ✗ Failed to watch {project.name}: {e}")

    logger.info("")
    logger.info("✅ Auto-detection complete!")
    logger.info("")

    # Initialize Project Brain (v2.2: Lazy Loading)
    logger.info("🧠 Initializing Project Brain...")

    # Try to load previous projects from memory
    saved_projects = memory_store.load_projects()
    if saved_projects:
        project_scanner.projects = saved_projects
        logger.info(f"   Loaded {len(saved_projects)} projects from memory")

    # v2.5: LAZY LOADING - Skip initial scan entirely for <0.1s startup
    # Scan happens on-demand when first file event arrives
    # IRONCLAD RULE I: Non-Blocking Startup - daemon must be ready in <0.1s
    logger.info("   ⚡ Lazy mode enabled - scan deferred until first file event")
    discovered = project_scanner.scan_all_projects(lazy=True)
    logger.info(f"   ✓ Project scanner ready (lazy mode, {len(discovered)} projects cached)")

    # Load previous errors
    saved_errors = memory_store.load_errors(limit=5)
    if saved_errors:
        for err in reversed(saved_errors):  # Add oldest first
            error_watcher.recent_errors.append(err)
        logger.info(f"   Loaded {len(saved_errors)} recent errors")

    logger.info("✅ Project Brain ready!")
    logger.info("")

    # v2.2: Initialize Archiver, Database, Pinning, and Retention
    logger.info("📦 Initializing Storage & Retention Layer...")

    # Initialize MemoryDatabase (shared instance)
    try:
        memory_db = MemoryDatabase()
        logger.info("   ✓ MemoryDatabase initialized")
    except Exception as e:
        logger.error(f"   ✗ MemoryDatabase failed: {e}")
        memory_db = None

    # Initialize Archiver (Hot→Cold tiered storage)
    try:
        archiver = get_archiver(ArchiverOptions(
            hot_retention_days=7,
            cold_retention_days=90,
            archive_interval_minutes=60,
            debug=False
        ))
        await archiver.start()
        logger.info("   ✓ Archiver started (Hot: 7d, Cold: 90d)")
    except Exception as e:
        logger.error(f"   ✗ Archiver failed: {e}")
        archiver = None

    # Initialize Pin Manager
    try:
        if memory_db:
            pin_manager = MemoryPinManager(memory_db)
            logger.info("   ✓ Pin Manager initialized")
        else:
            logger.warning("   ⚠ Pin Manager skipped (no database)")
    except Exception as e:
        logger.error(f"   ✗ Pin Manager failed: {e}")
        pin_manager = None

    # Start Retention Scheduler (background task)
    try:
        retention_task = asyncio.create_task(run_retention_scheduler())
        logger.info("   ✓ Retention scheduler started (1h interval)")
    except Exception as e:
        logger.error(f"   ✗ Retention scheduler failed: {e}")
        retention_task = None

    logger.info("✅ Storage & Retention Layer ready!")
    logger.info("")

    # v2.3: Initialize Vismriti AI Memory Engine
    global vismriti_brain
    logger.info("🧠 Initializing Vismriti AI Memory Engine...")
    try:
        import os
        vismriti_brain = VismritiMemory(
            enable_decay=True,
            enable_gist_extraction=False,  # Gist comes from VS Code
            enable_rl_agent=True,           # Enable Q-learning agent
            enable_aggregation=True,
            retention_policy="rule_based",
            project_path=os.getcwd()
        )
        logger.info("   ✓ Vismriti AI Engine activated")
        logger.info(f"   ✓ RL Agent: enabled, Decay: enabled")
    except Exception as e:
        logger.error(f"   ✗ Vismriti initialization failed: {e}")
        logger.warning("   ⚠ SDK memory features disabled (daemon continues)")
        vismriti_brain = None

    logger.info("")

    # v2.7 Phase 3: Initialize StateLinker for user focus tracking
    global state_linker
    logger.info("🔗 Initializing StateLinker...")
    try:
        import os
        state_linker = StateLinker(project_root=Path(os.getcwd()))
        logger.info("   ✓ StateLinker ready (Reality Grounding enabled)")
    except Exception as e:
        logger.error(f"   ✗ StateLinker failed: {e}")
        state_linker = None

    # v2.6 Phase 1.5: Initialize Vector Engine (Heavy ML - runs in background thread)
    logger.info("🔮 Initializing Vector Intelligence...")
    try:
        # Glass Box: Lazy import - VectorEngine lazy-loads sentence-transformers
        from vidurai.core.intelligence import VectorEngine

        vector_engine = VectorEngine()
        logger.info("   ✓ VectorEngine created (model lazy-loads on first use)")

        # Trigger backfill in background thread (non-blocking)
        import threading

        def _backfill_worker():
            try:
                logger.info("   🔮 Starting vector backfill (background thread)...")
                count = vector_engine.backfill_vectors()
                if count > 0:
                    logger.info(f"   ✓ Vector backfill complete: {count} memories vectorized")
                else:
                    logger.info("   ✓ Vector backfill: no missing vectors")
            except Exception as e:
                logger.warning(f"   ⚠ Vector backfill error (non-fatal): {e}")

        backfill_thread = threading.Thread(target=_backfill_worker, daemon=True)
        backfill_thread.start()
        logger.info("   ✓ Vector backfill started (background thread)")

    except ImportError as e:
        logger.warning(f"   ⚠ VectorEngine not available: {e}")
        logger.warning("   ⚠ Vector search disabled (daemon continues)")
    except Exception as e:
        logger.error(f"   ✗ VectorEngine failed: {e}")

    logger.info("")

    # v2.8 Phase 4: Start Maintenance Loop (Archiver + DreamCycle)
    logger.info("🌙 Starting Maintenance Loop...")
    try:
        maintenance_task = asyncio.create_task(_maintenance_loop())
        logger.info("   ✓ Maintenance loop started (24h interval)")
    except Exception as e:
        logger.error(f"   ✗ Maintenance loop failed: {e}")

    logger.info("")

    elapsed = time.time() - start_time
    logger.info(f"🏁 Background initialization complete! ({elapsed:.1f}s)")


async def run_retention_scheduler():
    """
    Background task to run retention policy decisions.
    Runs every hour to prune/consolidate memories.
    """
    global memory_db

    policy = create_retention_policy('rule_based')
    logger.info("[Retention] Scheduler active - checking every 1 hour")

    while True:
        try:
            await asyncio.sleep(3600)  # 1 hour

            if not memory_db:
                logger.debug("[Retention] Skipped - no database")
                continue

            # Build retention context from current DB state
            try:
                # Get memory counts by salience
                stats = memory_db.get_active_state_summary()
                total_memories = memory_db.count_memories() if hasattr(memory_db, 'count_memories') else 0

                # Build context (simplified - full implementation would query all metrics)
                context = RetentionContext(
                    total_memories=total_memories,
                    high_salience_count=stats.get('files_with_errors', 0),
                    medium_salience_count=0,
                    low_salience_count=0,
                    noise_salience_count=0,
                    avg_age_days=7.0,  # Default estimate
                    oldest_memory_days=30.0,  # Default estimate
                    total_size_mb=0.0,
                    estimated_tokens=total_memories * 50,  # Rough estimate
                    memories_added_last_day=stats.get('total_errors', 0),
                    memories_accessed_last_day=0,
                    project_path=''
                )

                # Get policy decision
                action = policy.decide_action(context)

                if action != RetentionAction.DO_NOTHING:
                    logger.info(f"[Retention] Action decided: {action.value}")
                    # Execute the action (cleanup expired memories)
                    if hasattr(memory_db, 'cleanup_expired'):
                        cleaned = memory_db.cleanup_expired()
                        logger.info(f"[Retention] Cleaned {cleaned} expired memories")
                else:
                    logger.debug("[Retention] No action needed")

            except Exception as e:
                logger.error(f"[Retention] Context build error: {e}")

        except asyncio.CancelledError:
            logger.info("[Retention] Scheduler stopped")
            break
        except Exception as e:
            logger.error(f"[Retention] Scheduler error: {e}")
            await asyncio.sleep(60)  # Wait a bit before retrying


async def _maintenance_loop():
    """
    v2.8 Phase 4: Maintenance loop for archival and RL training.

    Glass Box Protocol: Dream Cycle Safety
    - Runs every 24 hours
    - Captures all exceptions (never kills daemon)

    Sequence:
    1. MemoryArchiver.flush_archived_memories() - SQLite→Parquet
    2. DreamCycle.run() - Offline RL training on archived data
    """
    from pathlib import Path

    # Track last run (file-based for persistence across restarts)
    last_run_file = Path.home() / '.vidurai' / 'last_maintenance_run'

    logger.info("[Maintenance] Loop active - checking every 24 hours")

    while True:
        try:
            # Wait 24 hours between runs
            await asyncio.sleep(24 * 3600)  # 24 hours

            logger.info("[Maintenance] Starting maintenance cycle...")

            # Phase 4 Step 1: Flush archived memories to Parquet
            try:
                from vidurai.core.archival import MemoryArchiver

                archiver_instance = MemoryArchiver()
                archived_count = archiver_instance.flush_archived_memories()

                if archived_count > 0:
                    logger.info(f"[Maintenance] Archived {archived_count} memories to Parquet")
                else:
                    logger.debug("[Maintenance] No memories to archive")

            except ImportError as e:
                logger.warning(f"[Maintenance] MemoryArchiver not available: {e}")
            except Exception as e:
                # Glass Box: Dream Cycle Safety - never crash
                logger.error(f"[Maintenance] Archiver error (daemon safe): {e}")

            # Phase 4 Step 2: Run Dream Cycle (offline RL training)
            try:
                from vidurai.core.rl import DreamCycle

                dreamer = DreamCycle()
                stats = dreamer.run()

                if stats.get('success'):
                    logger.info(
                        f"[Maintenance] Dream cycle complete: "
                        f"{stats.get('episodes', 0)} episodes, "
                        f"reward={stats.get('total_reward', 0):.2f}"
                    )
                else:
                    error = stats.get('error', 'Unknown error')
                    logger.warning(f"[Maintenance] Dream cycle failed: {error}")

            except ImportError as e:
                logger.warning(f"[Maintenance] DreamCycle not available: {e}")
            except Exception as e:
                # Glass Box: Dream Cycle Safety - never crash
                logger.error(f"[Maintenance] Dream cycle error (daemon safe): {e}")

            # Update last run timestamp
            try:
                last_run_file.parent.mkdir(parents=True, exist_ok=True)
                last_run_file.write_text(datetime.now().isoformat())
            except Exception:
                pass  # Non-critical

            logger.info("[Maintenance] Maintenance cycle complete")

        except asyncio.CancelledError:
            logger.info("[Maintenance] Loop stopped")
            break
        except Exception as e:
            # Glass Box: Dream Cycle Safety - capture ALL exceptions
            logger.error(f"[Maintenance] Loop error (daemon safe): {e}")
            await asyncio.sleep(3600)  # Wait 1 hour before retrying


@app.on_event("shutdown")
async def shutdown_event():
    """Graceful shutdown of background services"""
    global ipc_server, archiver, retention_task, memory_db

    logger.info("🛑 Shutting down services...")

    # v2.2: Stop retention scheduler
    if retention_task:
        logger.info("   Stopping retention scheduler...")
        retention_task.cancel()
        try:
            await retention_task
        except asyncio.CancelledError:
            pass
        retention_task = None
        logger.info("   ✓ Retention scheduler stopped")

    # v2.2: Stop archiver
    if archiver:
        logger.info("   Stopping archiver...")
        await archiver.stop()
        archiver = None
        logger.info("   ✓ Archiver stopped")

    # v2.2: Close database
    if memory_db:
        logger.info("   Closing database...")
        memory_db.close()
        memory_db = None
        logger.info("   ✓ Database closed")

    # Stop IPC server
    if ipc_server:
        logger.info("   Stopping IPC server...")
        await ipc_server.stop()
        ipc_server = None
        logger.info("   ✓ IPC server stopped")

    # Stop all file watchers
    for path, observer in watched_projects.items():
        logger.info(f"   Stopping watcher: {path}")
        observer.stop()
        observer.join(timeout=2)

    logger.info("✅ Shutdown complete")


@app.get("/health")
def health_check():
    """Health endpoint for monitoring"""
    uptime = (datetime.now() - datetime.fromisoformat(metrics["started_at"])).total_seconds()

    # IPC status
    ipc_status = {
        "enabled": ipc_server is not None,
        "pipe_path": ipc_server.pipe_path if ipc_server else None,
        "clients": ipc_server.client_count if ipc_server else 0
    }

    return {
        "status": "alive",
        "version": __version__,
        "uptime_seconds": uptime,
        "uptime_human": f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m",
        "watched_projects": len(watched_projects),
        "active_connections": len(active_websockets),
        "ipc": ipc_status,
        "metrics": metrics
    }

@app.get("/metrics")
def get_metrics():
    """Return detailed metrics for monitoring"""
    collector_metrics = metrics_collector.get_summary()

    return {
        **metrics,
        **collector_metrics,
        "watched_projects": len(watched_projects),
        "active_connections": len(active_websockets),
        "projects_list": list(watched_projects.keys())
    }

@app.post("/context/prepare")
async def prepare_intelligent_context(request: ContextRequest):
    """
    Prepare intelligent context for AI based on user's prompt
    This is the core of Vidurai's intelligence
    """
    try:
        # Use context mediator to prepare intelligent context
        intelligent_context = context_mediator.prepare_context_for_ai(
            request.user_prompt,
            request.ai_platform
        )

        metrics["contexts_served"] += 1

        return {
            "status": "success",
            "context": intelligent_context,
            "platform": request.ai_platform,
            "user_state": context_mediator.user_state,
            "length": len(intelligent_context)
        }
    except Exception as e:
        logger.error(f"Error preparing context: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


@app.post("/api/rpc")
async def http_rpc_bridge(request: RPCRequest):
    """
    HTTP RPC Bridge - Allows Python scripts/Jupyter to talk to Daemon.

    This wraps handle_ipc_message for HTTP clients that cannot use Named Pipes.
    Follows the same protocol as the IPC transport.

    Constraint (FastAPI Hook): We use a mock client for HTTP requests
    to avoid circular imports and keep handle_ipc_message accessible.
    """
    from datetime import datetime

    try:
        # Build IPC message from HTTP request
        # Merge project_path into data if provided at top level
        data = request.data or {}
        if request.project_path:
            data['project_path'] = request.project_path

        message = IPCMessage(
            v=IPC_PROTOCOL_VERSION,
            type=request.type,
            ts=int(datetime.now().timestamp() * 1000),
            id=request.id,
            data=data
        )

        # Create a mock client for HTTP requests
        class HTTPClient:
            id = "http"

        # Call the IPC message handler
        response = await handle_ipc_message(HTTPClient(), message)

        # Convert IPCResponse to dict for JSON serialization
        return {
            "v": response.v,
            "type": response.type,
            "ts": response.ts,
            "id": response.id,
            "ok": response.ok,
            "data": response.data,
            "error": response.error
        }

    except Exception as e:
        logger.error(f"HTTP RPC error: {e}")
        return {
            "ok": False,
            "error": str(e),
            "type": "error"
        }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    active_websockets.add(websocket)

    client_info = websocket.client
    logger.info(f"🔌 WebSocket connected from {client_info}. Total: {len(active_websockets)}")

    # Send initial state
    await websocket.send_json({
        "event": "connected",
        "message": "Vidurai Ghost Daemon connected",
        "watched_projects": list(watched_projects.keys()),
        "metrics": metrics
    })

    try:
        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_text()
            logger.debug(f"Received: {data}")

            # Handle ping/pong
            if data == "ping":
                await websocket.send_json({"event": "pong"})

    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket disconnected. Total: {len(active_websockets) - 1}")
    finally:
        active_websockets.discard(websocket)

@app.post("/watch")
async def watch_project(project_path: str):
    """Start watching a project directory"""
    path = Path(project_path).resolve()

    if not path.exists():
        return {"error": "Path does not exist", "path": str(path)}

    if str(path) in watched_projects:
        return {
            "status": "already_watching",
            "path": str(path),
            "message": "Project already being watched"
        }

    # Start watching with SmartFileWatcher
    event_handler = SmartFileWatcher(str(path), event_queue)
    observer = Observer()
    observer.schedule(event_handler, str(path), recursive=True)
    observer.start()

    watched_projects[str(path)] = observer

    # Count files
    file_count = sum(1 for _ in path.rglob('*') if _.is_file() and not event_handler.should_ignore(str(_)))
    metrics["files_watched"] += file_count

    logger.info(f"👁️  Now watching: {path.name} ({file_count} files)")

    # Broadcast to connected clients
    await broadcast_event({
        "event": "project_added",
        "path": str(path),
        "files": file_count,
        "timestamp": datetime.now().isoformat()
    })

    return {
        "status": "watching",
        "path": str(path),
        "files": file_count
    }

@app.delete("/watch")
async def unwatch_project(project_path: str):
    """Stop watching a project"""
    path = str(Path(project_path).resolve())

    if path not in watched_projects:
        return {"error": "Project not being watched"}

    observer = watched_projects[path]
    observer.stop()
    observer.join()
    del watched_projects[path]

    logger.info(f"👁️  Stopped watching: {path}")

    return {"status": "unwatched", "path": path}

# ============================================================================
# PROJECT BRAIN ENDPOINTS
# ============================================================================

@app.get("/project/current")
async def get_current_project():
    """Get current project context (auto-switches based on cwd)"""
    try:
        # Auto-switch to current project
        current = project_scanner.auto_switch_context()

        if current:
            return {
                "status": "success",
                "project": current.to_dict(),
                "summary": project_scanner.get_project_summary(current)
            }
        else:
            return {
                "status": "no_project",
                "message": "Not in a recognized project directory"
            }
    except Exception as e:
        logger.error(f"Error getting current project: {e}")
        return {"status": "error", "error": str(e)}

@app.get("/project/all")
async def list_all_projects():
    """List all discovered projects"""
    try:
        projects_list = [
            {
                "name": p.name,
                "path": str(p.path),
                "type": p.type,
                "version": p.version,
                "language": p.language,
                "branch": p.git_branch,
                "problems": p.problems
            }
            for p in project_scanner.projects.values()
        ]

        return {
            "status": "success",
            "count": len(projects_list),
            "projects": projects_list
        }
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        return {"status": "error", "error": str(e)}

@app.post("/project/scan")
async def scan_projects():
    """Manually trigger project scan"""
    try:
        discovered = project_scanner.scan_all_projects(max_projects=20)
        return {
            "status": "success",
            "discovered": len(discovered),
            "projects": [p.name for p in discovered]
        }
    except Exception as e:
        logger.error(f"Error scanning projects: {e}")
        return {"status": "error", "error": str(e)}

@app.post("/error/capture")
async def capture_error(error: ErrorReport):
    """Manually report an error"""
    try:
        error_ctx = error_watcher.capture_error_context(
            error.error_text,
            error.command
        )

        # Save to memory
        memory_store.save_error(error_ctx)

        return {
            "status": "success",
            "error_type": error_ctx.error_type,
            "affected_files": error_ctx.affected_files
        }
    except Exception as e:
        logger.error(f"Error capturing error: {e}")
        return {"status": "error", "error": str(e)}

@app.get("/error/recent")
async def get_recent_errors(limit: int = 5):
    """Get recent errors"""
    try:
        recent = error_watcher.get_recent_errors(limit)

        return {
            "status": "success",
            "count": len(recent),
            "errors": [
                {
                    "type": e.error_type,
                    "command": e.command,
                    "timestamp": e.timestamp.isoformat(),
                    "affected_files": e.affected_files[:3]
                }
                for e in recent
            ]
        }
    except Exception as e:
        logger.error(f"Error getting recent errors: {e}")
        return {"status": "error", "error": str(e)}

@app.post("/context/smart")
async def get_smart_context(request: SmartContextRequest):
    """
    Get intelligent context for AI tools
    This is the main endpoint for browser extension
    """
    try:
        # Build context based on current state
        context = context_builder.build_context(
            trigger_type="manual",
            user_prompt=request.user_prompt
        )

        # Format for the requested platform
        formatted = context_builder.format_context(context, request.platform)

        metrics["contexts_served"] += 1

        return {
            "status": "success",
            "context": formatted,
            "raw_context": context,
            "intent": context.get("intent"),
            "length": len(formatted)
        }
    except Exception as e:
        logger.error(f"Error building smart context: {e}")
        return {"status": "error", "error": str(e)}

@app.get("/context/quick")
async def get_quick_context():
    """Get a quick one-liner context"""
    try:
        quick = context_builder.build_quick_context()
        return {
            "status": "success",
            "context": quick
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/brain/stats")
async def get_brain_stats():
    """Get Project Brain statistics"""
    try:
        storage_stats = memory_store.get_storage_stats()

        return {
            "status": "success",
            "projects_tracked": len(project_scanner.projects),
            "current_project": project_scanner.current_project.name if project_scanner.current_project else None,
            "errors_captured": len(error_watcher.recent_errors),
            "storage": storage_stats
        }
    except Exception as e:
        logger.error(f"Error getting brain stats: {e}")
        return {"status": "error", "error": str(e)}

@app.get("/", response_class=HTMLResponse)
def dashboard():
    """Local dashboard at localhost:7777"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Vidurai Ghost Daemon</title>
        <meta charset="UTF-8">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                background: linear-gradient(135deg, #0a0a0a 0%, #1a0a2e 100%);
                color: #10b981;
                font-family: 'Courier New', monospace;
                padding: 40px;
                min-height: 100vh;
            }
            .container { max-width: 1200px; margin: 0 auto; }
            h1 {
                font-size: 48px;
                background: linear-gradient(90deg, #10b981, #8b5cf6);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 30px;
                text-align: center;
            }
            .status {
                background: rgba(139, 92, 246, 0.1);
                border: 2px solid #8b5cf6;
                border-radius: 12px;
                padding: 30px;
                margin-bottom: 30px;
            }
            .status-row {
                display: flex;
                justify-content: space-between;
                margin: 15px 0;
                font-size: 18px;
            }
            .live {
                color: #22c55e;
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            .metric-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-top: 30px;
            }
            .metric-card {
                background: rgba(16, 185, 129, 0.1);
                border: 1px solid #10b981;
                border-radius: 8px;
                padding: 20px;
            }
            .metric-value {
                font-size: 36px;
                color: #8b5cf6;
                font-weight: bold;
                margin: 10px 0;
            }
            .metric-label {
                font-size: 14px;
                color: #10b981;
                text-transform: uppercase;
            }
            .projects-list {
                margin-top: 30px;
                background: rgba(139, 92, 246, 0.05);
                border: 1px solid #8b5cf6;
                border-radius: 8px;
                padding: 20px;
            }
            .project-item {
                padding: 10px;
                margin: 5px 0;
                background: rgba(16, 185, 129, 0.05);
                border-radius: 4px;
                display: flex;
                justify-content: space-between;
            }
            .footer {
                text-align: center;
                margin-top: 50px;
                color: #8b5cf6;
                font-size: 14px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🧠 VIDURAI GHOST DAEMON</h1>

            <div class="status">
                <div class="status-row">
                    <span>Status:</span>
                    <span class="live">● ALIVE</span>
                </div>
                <div class="status-row">
                    <span>Uptime:</span>
                    <span id="uptime">Loading...</span>
                </div>
                <div class="status-row">
                    <span>Active Connections:</span>
                    <span id="connections">0</span>
                </div>
            </div>

            <div class="metric-grid">
                <div class="metric-card">
                    <div class="metric-label">Watched Projects</div>
                    <div class="metric-value" id="projects">0</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Files Monitored</div>
                    <div class="metric-value" id="files">0</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Changes Detected</div>
                    <div class="metric-value" id="changes">0</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Tokens Saved</div>
                    <div class="metric-value" id="tokens">0</div>
                </div>
            </div>

            <div class="projects-list">
                <h3>📁 Watched Projects</h3>
                <div id="project-list"></div>
            </div>

            <div class="footer">
                <p>विस्मृति भी विद्या है — "Forgetting too is knowledge"</p>
                <p>Vidurai Ghost Daemon v2.5.0</p>
            </div>
        </div>

        <script>
            let ws = null;

            function connectWebSocket() {
                ws = new WebSocket('ws://localhost:7777/ws');

                ws.onopen = () => {
                    console.log('🔌 WebSocket connected');
                };

                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    console.log('📨 Received:', data);

                    if (data.event === 'file_changed') {
                        showNotification(`File changed: ${data.filename}`);
                    }
                };

                ws.onclose = () => {
                    console.log('🔌 WebSocket disconnected, reconnecting...');
                    setTimeout(connectWebSocket, 3000);
                };
            }

            function showNotification(message) {
                // Could add toast notification here
                console.log('🔔', message);
            }

            async function updateMetrics() {
                try {
                    const res = await fetch('/metrics');
                    const data = await res.json();

                    document.getElementById('files').textContent = data.files_watched.toLocaleString();
                    document.getElementById('changes').textContent = data.changes_detected.toLocaleString();
                    document.getElementById('tokens').textContent = data.tokens_saved.toLocaleString();

                    // Update project list
                    const projectList = document.getElementById('project-list');
                    projectList.innerHTML = data.projects_list.map(p =>
                        `<div class="project-item">
                            <span>📂 ${p.split('/').pop()}</span>
                            <span>${p}</span>
                        </div>`
                    ).join('') || '<p style="color: #8b5cf6; padding: 20px;">No projects being watched yet</p>';
                } catch (e) {
                    console.error('Failed to fetch metrics:', e);
                }
            }

            async function updateHealth() {
                try {
                    const res = await fetch('/health');
                    const data = await res.json();

                    document.getElementById('projects').textContent = data.watched_projects;
                    document.getElementById('connections').textContent = data.active_connections;
                    document.getElementById('uptime').textContent = data.uptime_human;
                } catch (e) {
                    console.error('Failed to fetch health:', e);
                }
            }

            // Initialize
            connectWebSocket();
            updateMetrics();
            updateHealth();

            // Update every second
            setInterval(() => {
                updateMetrics();
                updateHealth();
            }, 1000);
        </script>
    </body>
    </html>
    """

def main():
    logger.info("""
╔══════════════════════════════════════════╗
║   🧠 VIDURAI GHOST DAEMON v2.1           ║
║   The Invisible Infrastructure Layer     ║
║   Universal AI Context Protocol          ║
╚══════════════════════════════════════════╝
    """)
    logger.info("🌐 Dashboard: http://localhost:7777")
    logger.info("🔌 WebSocket: ws://localhost:7777/ws")
    logger.info("📡 IPC Pipe:  %s", get_pipe_path())
    logger.info("💓 Health:    http://localhost:7777/health")
    logger.info("")
    logger.info("विस्मृति भी विद्या है — 'Forgetting too is knowledge'")
    logger.info("")

    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=7777,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down gracefully...")

        # Note: shutdown_event will handle cleanup via FastAPI lifecycle
        logger.info("✅ Daemon stopped")


if __name__ == "__main__":
    main()
