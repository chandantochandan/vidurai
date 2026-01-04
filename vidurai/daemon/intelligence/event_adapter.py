"""
EventAdapter - Converts IPC events to VismritiMemory-compatible format

Following Ironclad Rule I: The "Adapter" Commandment
All mapping logic lives here, NOT in daemon.py handlers.

Verified signatures from vidurai/vismriti_memory.py:
- remember(content: str, metadata: Optional[Dict], salience: Optional[SalienceLevel], extract_gist: bool)

Verified SalienceLevel enum from vidurai/core/data_structures_v3.py:
- CRITICAL = 100 (credentials, explicit commands)
- HIGH = 75 (bug fixes, breakthroughs)
- MEDIUM = 50 (normal work)
- LOW = 25 (casual interactions)
- NOISE = 5 (raw logs)
"""

from typing import Dict, Any, Optional
from datetime import datetime

# Import SalienceLevel from the verified location
# Commandment III: Use Enums, not magic strings
from vidurai.core.data_structures_v3 import SalienceLevel


class EventAdapter:
    """
    Converts raw IPC events to VismritiMemory-compatible dictionaries.

    This is a pure adapter with no side effects. All it does is transform
    data from IPC format to SDK format.

    Usage:
        memory_args = EventAdapter.adapt(ipc_event)
        if memory_args:
            sdk.remember(**memory_args)
    """

    @staticmethod
    def adapt(ipc_event: Dict[str, Any], event_type: str) -> Optional[Dict[str, Any]]:
        """
        Adapt an IPC event to VismritiMemory.remember() arguments.

        Args:
            ipc_event: Raw JSON data from IPC message
            event_type: Type of event ('file_edit', 'diagnostic', 'terminal')

        Returns:
            Dictionary with keys: content, metadata, salience
            Returns None if event should be skipped

        Verified signature match:
            VismritiMemory.remember(
                content: str,
                metadata: Optional[Dict[str, Any]] = None,
                salience: Optional[SalienceLevel] = None,
                extract_gist: bool = True
            )
        """
        if event_type == 'file_edit':
            return EventAdapter._adapt_file_edit(ipc_event)
        elif event_type == 'diagnostic':
            return EventAdapter._adapt_diagnostic(ipc_event)
        elif event_type == 'terminal':
            return EventAdapter._adapt_terminal(ipc_event)
        else:
            return None

    # Paranoid PII patterns - case insensitive, handles forward/back slashes
    SENSITIVE_FILE_PATTERNS = ['.env', '.pem', '.key', 'id_rsa', 'secret', 'credential', 'password', 'token']

    @staticmethod
    def _is_sensitive_file(path: str) -> bool:
        """
        Check if file path contains sensitive file patterns.

        Paranoid PII Rule: Case-insensitive, handles both slash types.
        """
        # Normalize path: lowercase and convert backslashes to forward slashes
        normalized = path.lower().replace('\\', '/')

        # Check against sensitive patterns
        for pattern in EventAdapter.SENSITIVE_FILE_PATTERNS:
            if pattern in normalized:
                return True
        return False

    @staticmethod
    def _adapt_file_edit(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert file_edit event to memory args.

        IPC format (from daemon.py line 135-158):
            file: str - File path
            gist: str - Description
            change: str - Change type (save, modify, etc.)
            lang: str - Language identifier (optional)
            lines: int - Line count (optional)
            is_fix: bool - Explicit signal that this is a fix (optional, v2.5)

        Salience mapping (priority order):
            1. Sensitive files (.env, .pem, .key, secrets) -> NOISE (security first)
            2. is_fix=True -> HIGH (explicit signal from client/test)
            3. Default -> MEDIUM (normal work activity)
        """
        file_path = data.get('file', '')
        gist = data.get('gist', '')
        change_type = data.get('change', 'modify')

        # v2.5 Signal Fidelity: Check for explicit flags from Client/Test
        is_fix = data.get('is_fix', False)
        is_sensitive = EventAdapter._is_sensitive_file(file_path)

        # SECURITY FIRST: Check for sensitive/PII files (always wins)
        if is_sensitive:
            # Redact content, mark as NOISE to prevent storage
            return {
                'content': f"[SECURITY] Edited sensitive file: {file_path}",
                'metadata': {
                    'type': 'file_edit',
                    'file': file_path,
                    'change': change_type,
                    'sensitive': True,
                    'timestamp': datetime.now().isoformat()
                },
                'salience': SalienceLevel.NOISE,  # NOISE = 5, minimal storage
                'extract_gist': False
            }

        # v2.5 Signal Fidelity: Explicit is_fix flag = HIGH priority
        if is_fix:
            content = f"[FIX] {file_path}: {gist or 'Applied fix'}"
            salience = SalienceLevel.HIGH
        else:
            # Default: Normal work activity
            content = f"[{change_type.upper()}] {file_path}"
            if gist:
                content += f": {gist}"
            salience = SalienceLevel.MEDIUM

        return {
            'content': content,
            'metadata': {
                'type': 'file_edit',
                'file': file_path,
                'change': change_type,
                'lang': data.get('lang'),
                'lines': data.get('lines'),
                'is_fix': is_fix,  # v2.5: Track fix flag in metadata
                'timestamp': datetime.now().isoformat()
            },
            'salience': salience,  # Commandment III: Use Enum
            'extract_gist': False  # Already have gist from VS Code
        }

    @staticmethod
    def _adapt_diagnostic(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Convert diagnostic event to memory args.

        IPC format (from daemon.py line 190-229):
            file: str - File path
            sev: int - Severity (0=error, 1=warning, 2=info, 3=hint)
            msg: str - Diagnostic message
            ln: int - Line number (optional)
            src: str - Source (typescript, eslint, etc.)

        Salience mapping:
            Error (0) -> HIGH (important, needs attention)
            Warning (1) -> MEDIUM (normal work context)
            Info/Hint (2,3) -> Skip (too noisy, handled by Zombie Killer)

        Note: Info/Hint events are used for "Zombie Killer" cleanup
        in active_state, not for memory storage.
        """
        severity = data.get('sev', 0)

        # Commandment V: Zombie Killer - Skip info/hint for memory
        # These trigger DELETE in active_state, not ADD to memory
        if severity >= 2:  # info or hint
            return None

        file_path = data.get('file', '')
        msg = data.get('msg', '')
        line = data.get('ln')
        source = data.get('src', 'unknown')

        # Build content
        severity_label = 'ERROR' if severity == 0 else 'WARNING'
        content = f"[{severity_label}] {file_path}"
        if line:
            content += f":{line}"
        content += f" - {msg}"

        # Map severity to salience
        salience = SalienceLevel.HIGH if severity == 0 else SalienceLevel.MEDIUM

        return {
            'content': content,
            'metadata': {
                'type': 'diagnostic',
                'file': file_path,
                'severity': severity,
                'severity_label': severity_label.lower(),
                'line': line,
                'source': source,
                'message': msg[:500],  # Truncate long messages
                'timestamp': datetime.now().isoformat()
            },
            'salience': salience,
            'extract_gist': False  # Diagnostic message IS the gist
        }

    @staticmethod
    def _adapt_terminal(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Convert terminal event to memory args.

        IPC format (from daemon.py line 161-187):
            cmd: str - Command executed
            code: int - Exit code (optional)
            out: str - Output excerpt
            err: str - Error output

        Salience mapping:
            Exit code 0 -> LOW (successful, routine)
            Exit code != 0 -> HIGH (error, needs attention)
        """
        cmd = data.get('cmd', '')
        exit_code = data.get('code')
        output = data.get('out', '')
        error_output = data.get('err', '')

        # Skip empty commands
        if not cmd:
            return None

        # Build content
        if exit_code == 0:
            content = f"[TERMINAL] {cmd} (success)"
            salience = SalienceLevel.LOW
        elif exit_code is None:
            content = f"[TERMINAL] {cmd}"
            salience = SalienceLevel.LOW
        else:
            content = f"[TERMINAL ERROR] {cmd} (exit code: {exit_code})"
            if error_output:
                content += f"\n{error_output[:300]}"  # Include error excerpt
            salience = SalienceLevel.HIGH

        return {
            'content': content,
            'metadata': {
                'type': 'terminal',
                'command': cmd,
                'exit_code': exit_code,
                'output': output[:500] if output else None,  # Truncate
                'error_output': error_output[:500] if error_output else None,
                'success': exit_code == 0 if exit_code is not None else None,
                'timestamp': datetime.now().isoformat()
            },
            'salience': salience,
            'extract_gist': False
        }


# Hallucination Check:
# 1. Did I invent a library? NO - vidurai.core.data_structures_v3.SalienceLevel exists (verified)
# 2. Did I break Offline Mode? NO - This is pure logic, no I/O
# 3. Did I block the pipe? NO - This is synchronous but fast (no I/O)
