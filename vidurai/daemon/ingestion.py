import uuid
import time
import asyncio
import logging
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger("vidurai.daemon.ingestion")

async def _process_receipt_async(memory_db, receipt_id: str, memory_args: Dict[str, Any], event_type: str, msg_data: Dict[str, Any] = None) -> None:
    """
    WP-02: Asynchronous dispatch after receipt commit.
    """
    if not memory_db:
        logger.warning(f"[WP-02] Dropping receipt {receipt_id} - no database")
        return
        
    try:
        if memory_args:
            metadata = memory_args.get('metadata', {})
            # Execute atomic transaction
            await asyncio.to_thread(
                memory_db.process_memory_from_receipt,
                receipt_id=receipt_id,
                project_path=metadata.get('project_path') or metadata.get('project') or (msg_data.get('project_path') if msg_data else '') or (msg_data.get('project') if msg_data else '') or '',
                verbatim=memory_args.get('content', ''),
                gist=metadata.get('message', '') or metadata.get('gist', '') or memory_args.get('content', ''),
                salience=memory_args.get('salience'),
                event_type=event_type,
                file_path=metadata.get('file'),
                line_number=metadata.get('line') or metadata.get('lines'),
                tags=[],
                retention_days=None,
                created_at=None,
                identity=msg_data.get('_identity') if msg_data else None
            )
            logger.info(f"[WP-02] Successfully processed receipt {receipt_id}")
        else:
            await asyncio.to_thread(
                memory_db.update_receipt_status,
                receipt_id=receipt_id,
                status='processed'
            )
            
    except Exception as e:
        logger.error(f"[WP-02] Failed to process receipt {receipt_id}: {e}")
        await asyncio.to_thread(memory_db.handle_processing_failure, receipt_id, str(e))


async def ingest_class1_evidence(
    memory_db, 
    msg_version: int, 
    msg_id: str, 
    msg_ts: int, 
    msg_type: str, 
    msg_data: Dict[str, Any]
) -> Tuple[bool, Dict[str, Any]]:
    """
    Shared boundary for Class 1 Evidence Ingestion.
    Returns (success, response_data).
    response_data contains 'error' if not success, else 'receipt_id' and 'status'.
    """
    from vidurai.daemon.ipc.validation import validate_class1_evidence, generate_canonical_payload, normalize_aliases
    from vidurai.daemon.server import generate_canonical_hash, EventAdapter
    from vidurai.daemon.identity import resolve_project_identity
    
    if not memory_db:
        return False, {"error": "Database not available", "retryable": True}
        
    # 1. Normalise Aliases
    import copy
    msg_data = copy.deepcopy(msg_data)
    norm_type, norm_data = normalize_aliases(msg_type, msg_data)
        
    # 2. Validation
    is_valid, err_code, err_msg = validate_class1_evidence(msg_version, norm_type, msg_ts, msg_id, norm_data)
    if not is_valid:
        return False, {"error": err_code, "retryable": False}
        
    # 2.5 WP-03: Project Identity Resolution
    project_path = norm_data.get('project_path') or norm_data.get('project') or ''
    identity = resolve_project_identity(project_path)
    
    if identity.get('ambiguous'):
        return False, {"error": "ambiguous_project_identity", "retryable": False, "reason": identity.get('error')}
        
    # Inject identity into norm_data so _process_receipt_async can use it for DB insertion
    norm_data['_identity'] = identity

    # 3. Canonical JSON and Hash
    ts = msg_ts or int(time.time() * 1000)
    canon_json = generate_canonical_payload(msg_version, norm_type, ts, norm_data)
    payload_hash = generate_canonical_hash(canon_json)
    
    # 4. Idempotency Check
    receipt_id = str(uuid.uuid4())
    event_id = msg_id
    
    if event_id:
        existing = await asyncio.to_thread(memory_db.get_receipt_by_event_id, event_id)
        if existing:
            if existing['payload_hash'] == payload_hash:
                return True, {'status': 'duplicate', 'receipt_id': existing['receipt_id']}
            else:
                return False, {"error": "event_id_payload_conflict", "retryable": False}
                
    # 5. Durable Commit
    success = await asyncio.to_thread(
        memory_db.insert_event_receipt,
        receipt_id=receipt_id,
        event_type=norm_type,
        payload_hash=payload_hash,
        payload_json=canon_json,
        status='recorded',
        received_at=int(time.time() * 1000),
        event_id=event_id,
        identity=identity
    )
    
    if not success:
        return False, {"error": "internal_durable_write_failure", "retryable": True}
        
    # 6. Background Dispatch
    memory_args = EventAdapter.adapt(norm_data, norm_type)
    asyncio.create_task(_process_receipt_async(memory_db, receipt_id, memory_args, norm_type, msg_data))
    
    status_msg = 'recorded' if event_id else 'legacy_unkeyed'
    return True, {'status': status_msg, 'receipt_id': receipt_id}
