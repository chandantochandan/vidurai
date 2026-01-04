"""
Proxy Routes
Main HTTP route handlers for intercepting and forwarding AI API requests
Orchestrates: provider detection → session management → Vidurai processing → forwarding
"""

from fastapi import APIRouter, Request, HTTPException, Response
from fastapi.responses import StreamingResponse
import httpx
import json
import time
from typing import Optional
from loguru import logger

from vidurai.core.data_structures_v3 import SalienceLevel
from src.utils.provider_detection import ProviderDetector
from src.utils.session_manager import SessionManager
from src.utils.metrics_tracker import MetricsTracker
from src.utils.terminal_ui import TerminalUI

router = APIRouter()

# Global instances (will be set by main app)
_provider_detector: Optional[ProviderDetector] = None
_session_manager: Optional[SessionManager] = None
_metrics_tracker: Optional[MetricsTracker] = None
_terminal_ui: Optional[TerminalUI] = None


def init_routes(config, provider_detector, session_manager, metrics_tracker, terminal_ui):
    """
    Initialize routes with required dependencies

    Args:
        config: Config object
        provider_detector: ProviderDetector instance
        session_manager: SessionManager instance
        metrics_tracker: MetricsTracker instance
        terminal_ui: TerminalUI instance
    """
    global _provider_detector, _session_manager, _metrics_tracker, _terminal_ui

    _provider_detector = provider_detector
    _session_manager = session_manager
    _metrics_tracker = metrics_tracker
    _terminal_ui = terminal_ui

    logger.info("Proxy routes initialized")


@router.get("/health")
async def health_check():
    """
    Health check endpoint

    Returns:
        Health status and basic stats
    """
    return {
        "status": "healthy",
        "service": "vidurai-proxy",
        "version": "1.0.0",
        "sessions": _session_manager.get_session_count() if _session_manager else 0
    }


@router.get("/metrics")
async def get_metrics():
    """
    Get current metrics

    Returns:
        Global metrics including token savings
    """
    if not _metrics_tracker:
        return {"error": "Metrics tracker not initialized"}

    return _metrics_tracker.get_global_metrics()


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_request(request: Request, path: str):
    """
    Main proxy endpoint - handles all AI API requests

    Flow:
    1. Detect provider from request
    2. Get/create session
    3. Extract messages
    4. Process through Vidurai
    5. Forward to provider
    6. Track metrics
    7. Return response

    Args:
        request: FastAPI request object
        path: Request path

    Returns:
        Provider's response (transparent passthrough)
    """
    start_time = time.time()

    try:
        # 1. Detect provider and extract API key
        # Support both 'authorization' and 'x-api-key' headers
        auth_header = request.headers.get("authorization", "")
        if not auth_header:
            # Anthropic uses x-api-key header
            api_key = request.headers.get("x-api-key", "")
            if api_key:
                auth_header = f"Bearer {api_key}"  # Normalize format
        else:
            # Extract key from "Bearer <key>" format if needed
            api_key = auth_header.replace("Bearer ", "").strip()

        provider = _provider_detector.detect(path, auth_header or api_key)

        # Show request received
        _terminal_ui.show_request_received(
            method=request.method,
            path=f"/{path}",
            provider=provider
        )

        # 2. Get session (use the actual API key for session ID)
        session_id = _session_manager.generate_session_id(api_key if 'api_key' in locals() else auth_header)
        vidurai = _session_manager.get_session(session_id)

        # 3. Get request body
        body = await request.body()
        request_data = json.loads(body) if body else {}

        # 4. Process through Vidurai (if this is a messages endpoint)
        original_tokens = 0
        compressed_tokens = 0

        if _should_process_through_vidurai(path, request_data):
            request_data, original_tokens, compressed_tokens = await _process_with_vidurai(
                vidurai=vidurai,
                request_data=request_data,
                session_id=session_id
            )
        else:
            # Pass through without Vidurai processing
            logger.debug(f"Bypassing Vidurai for path: {path}")

        # 5. Forward to provider
        _terminal_ui.show_forwarding(provider, "")

        provider_config = _provider_detector.get_provider_config(provider)
        target_url = _provider_detector.get_target_url(provider, path)

        # Make request to actual provider
        async with httpx.AsyncClient(timeout=300.0) as client:
            # Prepare headers
            headers = dict(request.headers)
            headers.pop('host', None)  # Remove host header
            headers.pop('content-length', None)  # Remove content-length (httpx will recalculate)

            # Set correct content-type for JSON requests
            if request_data:
                headers['content-type'] = 'application/json'

            # Make request
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=json.dumps(request_data).encode() if request_data else body,
                timeout=300.0
            )

        # 6. Track metrics
        elapsed_ms = (time.time() - start_time) * 1000

        if original_tokens > 0:  # Only track if we processed through Vidurai
            session_metrics = _metrics_tracker.record_request(
                session_id=session_id,
                original_tokens=original_tokens,
                compressed_tokens=compressed_tokens,
                elapsed_ms=elapsed_ms
            )

            _terminal_ui.show_response(
                status=response.status_code,
                elapsed_ms=elapsed_ms,
                cost_saved=session_metrics.cost_saved
            )
        else:
            _terminal_ui.show_response(
                status=response.status_code,
                elapsed_ms=elapsed_ms
            )

        # 7. Return response (fix: remove compression headers)
        response_headers = dict(response.headers)
        # Remove headers that cause issues when response is already decompressed
        response_headers.pop('content-encoding', None)
        response_headers.pop('content-length', None)  # Length changes after decompression
        response_headers.pop('transfer-encoding', None)

        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=response_headers
        )

    except Exception as e:
        logger.error(f"Proxy error: {e}", exc_info=True)
        _terminal_ui.show_error(str(e))
        raise HTTPException(status_code=500, detail=str(e))


def _should_process_through_vidurai(path: str, request_data: dict) -> bool:
    """
    Determine if request should be processed through Vidurai

    Args:
        path: Request path
        request_data: Request body

    Returns:
        True if should process through Vidurai
    """
    # Only process chat/message endpoints
    chat_paths = ['/messages', '/chat/completions', '/completions']

    if not any(p in path for p in chat_paths):
        return False

    # Must have messages
    if 'messages' not in request_data:
        return False

    # Must have at least one message to process
    messages = request_data.get('messages', [])
    if len(messages) < 1:  # Need at least 1 message to process
        return False

    return True


async def _process_with_vidurai(
    vidurai,
    request_data: dict,
    session_id: str
) -> tuple[dict, int, int]:
    """
    Process request through Vidurai memory management

    Args:
        vidurai: ViduraiMemory instance
        request_data: Request body with messages
        session_id: Session identifier

    Returns:
        Tuple of (modified_request_data, original_tokens, compressed_tokens)
    """
    messages = request_data.get('messages', [])

    # Estimate original token count
    original_tokens = sum(len(m.get('content', '').split()) for m in messages)

    _terminal_ui.show_processing(len(messages), original_tokens)
    _terminal_ui.show_vidurai_layers()

    # STEP 1: Recall existing memories FIRST (before storing current message)
    # Use empty query to get ALL recent conversation history (not semantic search)
    # This maintains full context instead of trying to match semantic similarity
    logger.info(f"🔍 Recalling all recent memories (min_salience=NOISE, top_k=50)")

    relevant_memories = vidurai.recall(
        query="",  # Empty query = get all memories, not semantic search
        min_salience=SalienceLevel.NOISE,  # Get everything
        top_k=50  # Increased limit for full context
    )

    # Debug: Log recalled memories
    logger.info(f"📝 Recalled {len(relevant_memories)} memories from session")
    for i, mem in enumerate(relevant_memories):
        content = mem.gist or mem.verbatim
        logger.info(f"  Memory {i+1} - gist: {mem.gist[:30] if mem.gist else 'None'}, verbatim: {mem.verbatim[:30] if mem.verbatim else 'None'}")
        logger.info(f"  Memory {i+1} - using: {content[:50] if content else 'EMPTY!'}...")

    # Reconstruct optimized messages from recalled memories
    # Use gist for compression (falls back to verbatim if gist extraction disabled)
    optimized_messages = [
        {
            'role': mem.metadata.get('role', 'user'),
            'content': mem.gist or mem.verbatim or ""  # Ensure we never have None
        }
        for mem in relevant_memories
        if (mem.gist or mem.verbatim)  # Only include memories with actual content
    ]

    # STEP 2: Store current messages for FUTURE recalls (after we've recalled existing ones)
    for msg in messages:
        vidurai.remember(
            content=msg.get('content', ''),
            metadata={
                'role': msg.get('role'),
                'session_id': session_id
            }
        )

    # Debug: Confirm storage
    logger.info(f"💾 Stored {len(messages)} messages in session {session_id}")

    # Debug: Check total memories in session after storage
    all_memories = vidurai.recall(query="", min_salience=SalienceLevel.NOISE, top_k=100)
    logger.info(f"🗄️ Total memories in session after storage: {len(all_memories)}")

    # Estimate compressed token count
    compressed_tokens = sum(len(m['content'].split()) for m in optimized_messages)

    # Show compression results
    session_metrics = _metrics_tracker.get_session_metrics(session_id)
    _terminal_ui.show_compression(
        before=original_tokens,
        after=compressed_tokens,
        session_total_saved=session_metrics.tokens_saved
    )

    # Update request with recalled context + current message
    if optimized_messages:
        # Prepend recalled context, keep current message at end
        request_data['messages'] = optimized_messages + [messages[-1]]
    else:
        # No recalled memories, just send current messages as-is
        request_data['messages'] = messages

    # Debug: Log messages being sent to Anthropic
    logger.info(f"📤 Sending {len(request_data['messages'])} messages to Anthropic")
    for i, msg in enumerate(request_data['messages']):
        logger.info(f"  Message {i+1} ({msg.get('role', 'unknown')}): {msg.get('content', '')[:50]}...")

    return request_data, original_tokens, compressed_tokens
