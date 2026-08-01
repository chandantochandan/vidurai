import json
import uuid
from typing import Dict, Any, Tuple

def validate_class1_evidence(msg_v: int, msg_type: str, msg_ts: int, msg_id: str, msg_data: Dict[str, Any]) -> Tuple[bool, str, str]:
    """
    Validate Class 1 evidence.
    Returns: (is_valid, error_code, error_message)
    """
    if msg_v is None:
        return False, "missing_required_field", "Missing 'v'"
    if msg_v != 1:
        return False, "unsupported_version", f"Unsupported version: {msg_v}"
        
    if msg_ts is None:
        return False, "missing_required_field", "Missing 'ts'"
        
    if not msg_type:
        return False, "missing_required_field", "Missing 'type'"
        
    # Determine taxonomy (Class 1, 2, 3)
    class1_types = {'file_edit', 'terminal', 'diagnostic', 'terminal_command', 'diagnostics', 'mcp_evidence'}
    class2_types = {'recall', 'search'}
    class3_types = {'handshake', 'ping', 'echo'}
    
    valid_types = class1_types | class2_types | class3_types
    if msg_type not in valid_types:
        return False, "unknown_event_type", f"Unknown event type: {msg_type}"

    # We also require ts
    # Wait, the prompt says "validate required fields".
    # I'll check ts in _handle_class1_evidence or here?
    # Actually validation doesn't take ts as argument right now. Let me add it.

    # Apply UUIDv4 validation ONLY to Class 1 events
    if msg_type in class1_types:
        if msg_id is not None:
            try:
                val = uuid.UUID(msg_id, version=4)
                if str(val) != msg_id.lower():
                    return False, "malformed_uuid", "Malformed UUIDv4"
            except ValueError:
                return False, "malformed_uuid", "Malformed UUIDv4"
            
    if not msg_data:
        # Some Class 3 events might not require data, but if this is strict we can keep it
        # Actually handshake and recall have data. Ping might not. We can allow empty data for ping.
        if msg_type not in ('ping',):
            return False, "missing_required_field", "Missing 'data' payload"
        
    # Check specific fields
    # file_edit: project_path, file, change
    if msg_type in ('file_edit',):
        if 'project_path' not in msg_data or 'file' not in msg_data:
            return False, "missing_required_field", "Missing required fields in file_edit"
        if 'change' not in msg_data and 'change_type' not in msg_data:
            return False, "missing_required_field", "Missing required fields in file_edit"
            
    if msg_type in ('terminal', 'terminal_command'):
        if 'project_path' not in msg_data or 'command' not in msg_data or 'output' not in msg_data:
            if 'out' not in msg_data and 'output' not in msg_data:
                return False, "missing_required_field", "Missing required fields in terminal"
            
    return True, "", ""

def normalize_aliases(msg_type: str, msg_data: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """
    Normalise semantic legacy aliases into canonical WP-02 form.
    """
    if not msg_data:
        msg_data = {}
        
    norm_type = msg_type
    if msg_type == 'terminal_command':
        norm_type = 'terminal'
    elif msg_type == 'diagnostics':
        norm_type = 'diagnostic'
        
    norm_data = dict(msg_data)
    if norm_type == 'file_edit' and 'change_type' in norm_data:
        if 'change' not in norm_data:
            norm_data['change'] = norm_data['change_type']
        del norm_data['change_type']
        
    if norm_type == 'terminal':
        if 'cmd' in norm_data:
            if 'command' not in norm_data:
                norm_data['command'] = norm_data['cmd']
            del norm_data['cmd']
        if 'out' in norm_data:
            if 'output' not in norm_data:
                norm_data['output'] = norm_data['out']
            del norm_data['out']
        if 'err' in norm_data:
            if 'error' not in norm_data:
                norm_data['error'] = norm_data['err']
            del norm_data['err']
            
    return norm_type, norm_data

import hashlib
def generate_canonical_payload(msg_v, msg_type, ts, msg_data):
    """
    Generate deterministic JSON payload for hashing.
    Keys are sorted.
    """
    norm_type, norm_data = normalize_aliases(msg_type, msg_data)
    canon = {
        'v': msg_v,
        'type': norm_type,
        'ts': ts,
        'data': norm_data
    }
    return json.dumps(canon, sort_keys=True, separators=(',', ':'))

def generate_canonical_hash(payload_str: str) -> str:
    """
    Generate SHA-256 hash of the canonical payload.
    """
    return hashlib.sha256(payload_str.encode('utf-8')).hexdigest()
