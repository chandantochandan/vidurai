"""
Vidurai Jupyter Client - Live Mode
==================================

Lightweight client that connects to the Vidurai Daemon's HTTP API.
Avoids "Split Brain" by NOT loading a second VismritiMemory instance.

Instead, all operations go through the running daemon at localhost:7777.

Usage in Jupyter:
    from vidurai.clients import ViduraiLive

    client = ViduraiLive()

    # Get context (same as VS Code sees)
    print(client.get_context())

    # Remember something (sent to daemon)
    client.remember("Implemented feature X with approach Y")

    # Get brain statistics
    print(client.get_stats())
"""

import os
import json
import socket
import uuid
from typing import Optional, Dict, Any, Literal
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


# Default daemon endpoints
DEFAULT_HTTP_HOST = "http://localhost:7777"
DEFAULT_SOCKET_PATH = f"/tmp/vidurai-{os.environ.get('USER', 'user')}.sock"

# Audience types for context retrieval
AudienceType = Literal['developer', 'ai', 'manager', 'product', 'stakeholder']


class ViduraiLiveError(Exception):
    """Raised when ViduraiLive encounters an error"""
    pass


class DaemonNotFoundError(ViduraiLiveError):
    """Raised when the Vidurai daemon is not running or unreachable."""

    def __init__(self, message: str = None):
        self.message = message or (
            "Vidurai Daemon not found. Is it running?\n"
            "\n"
            "To start the daemon:\n"
            "  cd vidurai-daemon && python daemon.py\n"
            "\n"
            "Or run in background:\n"
            "  nohup python daemon.py > /tmp/vidurai.log 2>&1 &\n"
        )
        super().__init__(self.message)


class ViduraiLive:
    """
    Live Mode client for Vidurai - connects to daemon instead of loading SDK.

    This is the recommended way to use Vidurai from Jupyter notebooks,
    data analysis scripts, or any external tool that wants to share
    context with VS Code.

    Benefits:
    - No Split Brain: Same memory as VS Code and other tools
    - Lower overhead: No need to load VismritiMemory
    - Real-time sync: Changes are immediately visible everywhere

    Example:
        >>> from vidurai.clients import ViduraiLive
        >>> client = ViduraiLive()
        >>> client.is_connected()
        True
        >>> print(client.get_context(audience='ai'))
        <vidurai_context>...
    """

    def __init__(
        self,
        http_host: str = DEFAULT_HTTP_HOST,
        socket_path: Optional[str] = None,
        prefer_socket: bool = True,
        timeout: float = 5.0
    ):
        """
        Initialize ViduraiLive client.

        Args:
            http_host: HTTP endpoint of daemon (default: localhost:7777)
            socket_path: Unix socket path (default: /tmp/vidurai-{user}.sock)
            prefer_socket: Use Unix socket for IPC operations if available
            timeout: Request timeout in seconds
        """
        self.http_host = http_host.rstrip('/')
        self.socket_path = socket_path or DEFAULT_SOCKET_PATH
        self.prefer_socket = prefer_socket
        self.timeout = timeout
        self._connected: Optional[bool] = None

    # =========================================================================
    # Connection Management
    # =========================================================================

    def is_connected(self) -> bool:
        """Check if daemon is reachable."""
        try:
            health = self._http_get('/health')
            self._connected = health.get('status') == 'alive'
            return self._connected
        except Exception:
            self._connected = False
            return False

    def _has_socket(self) -> bool:
        """Check if Unix socket exists."""
        return os.path.exists(self.socket_path)

    # =========================================================================
    # Context Retrieval (Main Feature)
    # =========================================================================

    def get_context(
        self,
        audience: AudienceType = 'ai',
        include_memories: bool = True,
        query: Optional[str] = None,
        max_tokens: int = 4000
    ) -> str:
        """
        Get project context from daemon (same as VS Code sees).

        Args:
            audience: Target audience ('developer', 'ai', 'manager', etc.)
            include_memories: Include SDK memories in context
            query: Optional query to filter relevant memories
            max_tokens: Maximum tokens to return

        Returns:
            Formatted context string ready for AI consumption

        Example:
            >>> context = client.get_context(audience='ai')
            >>> print(context[:200])
            <vidurai_context audience="ai">...
        """
        if self.prefer_socket and self._has_socket():
            return self._get_context_via_socket(
                audience=audience,
                include_memories=include_memories,
                query=query,
                max_tokens=max_tokens
            )
        else:
            return self._get_context_via_http(query=query)

    def _get_context_via_socket(
        self,
        audience: AudienceType,
        include_memories: bool,
        query: Optional[str],
        max_tokens: int
    ) -> str:
        """Get context via Unix socket IPC (preferred for rich features)."""
        response = self._ipc_request(
            method='get_context',
            params={
                'audience': audience,
                'include_memories': include_memories,
                'query': query,
                'max_tokens': max_tokens
            }
        )

        if not response.get('ok'):
            raise ViduraiLiveError(f"get_context failed: {response.get('error')}")

        data = response.get('data', {})

        # Combine oracle context and memory context
        oracle_ctx = data.get('oracle_context', data.get('context', ''))
        memory_ctx = data.get('memory_context', '')

        if memory_ctx:
            return f"{oracle_ctx}\n\n{memory_ctx}"
        return oracle_ctx

    def _get_context_via_http(self, query: Optional[str] = None) -> str:
        """Get context via HTTP API (fallback)."""
        if query:
            data = self._http_post('/context/smart', {
                'user_prompt': query,
                'platform': 'jupyter'
            })
        else:
            data = self._http_get('/context/quick')

        if data.get('status') != 'success':
            raise ViduraiLiveError(f"get_context failed: {data.get('error')}")

        return data.get('context', '')

    def get_quick_context(self) -> str:
        """Get a quick one-liner context summary."""
        data = self._http_get('/context/quick')
        return data.get('context', '')

    # =========================================================================
    # Memory Operations
    # =========================================================================

    def remember(
        self,
        content: str,
        salience: str = 'medium',
        metadata: Optional[Dict[str, Any]] = None,
        source: str = 'jupyter'
    ) -> bool:
        """
        Remember content via daemon (becomes part of project context).

        This is the core feature for Jupyter integration - code and analysis
        written in notebooks becomes part of the shared project memory.

        Args:
            content: Content to remember (code, analysis, notes)
            salience: Importance level ('critical', 'high', 'medium', 'low')
            metadata: Optional metadata (file_path, language, etc.)
            source: Source identifier (default: 'jupyter')

        Returns:
            True if successful

        Example:
            >>> client.remember(
            ...     "Analysis: User retention is 78% in Q4",
            ...     salience='high',
            ...     metadata={'notebook': 'retention_analysis.ipynb'}
            ... )
            True
        """
        if not content or not content.strip():
            return False

        # Send via IPC socket for immediate processing
        if self.prefer_socket and self._has_socket():
            response = self._ipc_send(
                msg_type='file_edit',
                data={
                    'file': metadata.get('file_path', f'jupyter/{source}_cell.py') if metadata else f'jupyter/{source}_cell.py',
                    'gist': content[:500],  # Truncate for gist
                    'change': 'save',
                    'lang': metadata.get('language', 'python') if metadata else 'python',
                    'salience': salience
                }
            )
            return response.get('ok', False)
        else:
            # HTTP fallback - use context/prepare endpoint
            data = self._http_post('/context/prepare', {
                'user_prompt': content,
                'ai_platform': 'jupyter'
            })
            return data.get('status') == 'success'

    def recall(
        self,
        query: str,
        limit: int = 5,
        min_salience: str = 'low'
    ) -> str:
        """
        Recall memories matching a query.

        Args:
            query: Search query
            limit: Maximum memories to return
            min_salience: Minimum salience level

        Returns:
            Formatted memory context
        """
        if self.prefer_socket and self._has_socket():
            response = self._ipc_send(
                msg_type='recall',
                data={
                    'query': query,
                    'maxTokens': 2000,
                    'minSalience': min_salience
                }
            )
            if response.get('ok'):
                return response.get('data', {}).get('context', '')
            return ''
        else:
            return self.get_context(query=query, audience='ai')

    # =========================================================================
    # Statistics & Monitoring
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get brain statistics from daemon."""
        return self._http_get('/brain/stats')

    def get_health(self) -> Dict[str, Any]:
        """Get daemon health status."""
        return self._http_get('/health')

    def get_metrics(self) -> Dict[str, Any]:
        """Get detailed daemon metrics."""
        return self._http_get('/metrics')

    # =========================================================================
    # Profile Management (v2.3 Cognitive Control)
    # =========================================================================

    def set_profile(
        self,
        profile: Literal['cost_focused', 'balanced', 'quality_focused']
    ) -> bool:
        """
        Set memory profile via daemon.

        Args:
            profile: Profile to set
                - 'cost_focused': Minimize tokens, aggressive pruning
                - 'balanced': Default balance
                - 'quality_focused': Maximum context retention

        Returns:
            True if successful
        """
        if not self._has_socket():
            raise ViduraiLiveError("Profile switching requires socket connection")

        response = self._ipc_send(
            msg_type='set_config',
            data={'profile': profile}
        )
        return response.get('ok', False)

    # =========================================================================
    # Pin Operations (v2.2)
    # =========================================================================

    def pin(self, memory_id: str, reason: Optional[str] = None) -> bool:
        """Pin a memory to always include in context."""
        if not self._has_socket():
            raise ViduraiLiveError("Pin operations require socket connection")

        response = self._ipc_send(
            msg_type='pin',
            data={'memory_id': memory_id, 'reason': reason}
        )
        return response.get('ok', False)

    def unpin(self, memory_id: str) -> bool:
        """Unpin a memory."""
        if not self._has_socket():
            raise ViduraiLiveError("Unpin operations require socket connection")

        response = self._ipc_send(
            msg_type='unpin',
            data={'memory_id': memory_id}
        )
        return response.get('ok', False)

    def get_pinned(self) -> list:
        """Get list of pinned memories."""
        if not self._has_socket():
            raise ViduraiLiveError("Get pinned operations require socket connection")

        response = self._ipc_send(msg_type='get_pinned', data={})
        if response.get('ok'):
            return response.get('data', {}).get('pinned', [])
        return []

    # =========================================================================
    # Low-Level Transport
    # =========================================================================

    def _http_get(self, endpoint: str) -> Dict[str, Any]:
        """Make HTTP GET request to daemon."""
        url = f"{self.http_host}{endpoint}"
        try:
            req = Request(url)
            with urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode('utf-8'))
        except HTTPError as e:
            raise ViduraiLiveError(f"HTTP {e.code}: {e.reason}")
        except URLError as e:
            # Check for connection refused - daemon not running
            if 'Connection refused' in str(e.reason) or 'refused' in str(e.reason).lower():
                raise DaemonNotFoundError()
            raise DaemonNotFoundError(
                f"Cannot connect to Vidurai Daemon at {self.http_host}\n"
                f"Error: {e.reason}\n"
                f"\n"
                f"Is the daemon running? Start it with:\n"
                f"  cd vidurai-daemon && python daemon.py\n"
            )

    def _http_post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP POST request to daemon."""
        url = f"{self.http_host}{endpoint}"
        try:
            req = Request(
                url,
                data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode('utf-8'))
        except HTTPError as e:
            raise ViduraiLiveError(f"HTTP {e.code}: {e.reason}")
        except URLError as e:
            # Check for connection refused - daemon not running
            if 'Connection refused' in str(e.reason) or 'refused' in str(e.reason).lower():
                raise DaemonNotFoundError()
            raise DaemonNotFoundError(
                f"Cannot connect to Vidurai Daemon at {self.http_host}\n"
                f"Error: {e.reason}\n"
                f"\n"
                f"Is the daemon running? Start it with:\n"
                f"  cd vidurai-daemon && python daemon.py\n"
            )

    def _ipc_send(
        self,
        msg_type: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send IPC message via Unix socket."""
        message = {
            'v': 1,
            'type': msg_type,
            'ts': int(__import__('time').time() * 1000),
            'id': str(uuid.uuid4()),
            'data': data or {}
        }

        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect(self.socket_path)

            sock.send((json.dumps(message) + '\n').encode('utf-8'))

            response = b''
            while b'\n' not in response:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk

            sock.close()
            return json.loads(response.decode('utf-8').strip())

        except socket.error as e:
            # Check for common connection errors
            err_str = str(e).lower()
            if 'connection refused' in err_str or 'no such file' in err_str or 'errno 111' in err_str:
                raise DaemonNotFoundError(
                    f"Vidurai Daemon not found at {self.socket_path}\n"
                    f"\n"
                    f"The daemon socket does not exist or is not responding.\n"
                    f"\n"
                    f"To start the daemon:\n"
                    f"  cd vidurai-daemon && python daemon.py\n"
                )
            raise ViduraiLiveError(f"Socket error: {e}")
        except json.JSONDecodeError as e:
            raise ViduraiLiveError(f"Invalid response: {e}")

    def _ipc_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send IPC request (Oracle API pattern)."""
        message = {
            'v': 1,
            'type': 'request',
            'ts': int(__import__('time').time() * 1000),
            'id': str(uuid.uuid4()),
            'data': {
                'method': method,
                'params': params or {}
            }
        }

        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect(self.socket_path)

            sock.send((json.dumps(message) + '\n').encode('utf-8'))

            response = b''
            while b'\n' not in response:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk

            sock.close()
            return json.loads(response.decode('utf-8').strip())

        except socket.error as e:
            # Check for common connection errors
            err_str = str(e).lower()
            if 'connection refused' in err_str or 'no such file' in err_str or 'errno 111' in err_str:
                raise DaemonNotFoundError(
                    f"Vidurai Daemon not found at {self.socket_path}\n"
                    f"\n"
                    f"The daemon socket does not exist or is not responding.\n"
                    f"\n"
                    f"To start the daemon:\n"
                    f"  cd vidurai-daemon && python daemon.py\n"
                )
            raise ViduraiLiveError(f"Socket error: {e}")
        except json.JSONDecodeError as e:
            raise ViduraiLiveError(f"Invalid response: {e}")

    # =========================================================================
    # Context Manager Support
    # =========================================================================

    def __enter__(self):
        """Context manager entry."""
        if not self.is_connected():
            raise ViduraiLiveError("Cannot connect to Vidurai daemon")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass

    # =========================================================================
    # Repr
    # =========================================================================

    def __repr__(self) -> str:
        status = "connected" if self._connected else "disconnected"
        return f"<ViduraiLive({self.http_host}) {status}>"
