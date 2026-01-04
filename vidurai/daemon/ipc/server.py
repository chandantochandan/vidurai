"""
IPC Server - Named Pipe/Unix Socket Transport for Vidurai Daemon

Provides asyncio-based IPC server for communication with VS Code extension.
Uses NDJSON protocol for bidirectional communication.

Architecture:
- Unix: asyncio.start_unix_server() on /tmp/vidurai-{uid}.sock
- Windows: asyncio Named Pipe using proactor event loop

Features:
- Heartbeat every 5 seconds to all connected clients
- Request-response correlation via message IDs
- Graceful client disconnect handling

@version 2.1.0
"""

import os
import sys
import json
import asyncio
import logging
import getpass
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Set, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("vidurai.ipc")

# =============================================================================
# CONSTANTS
# =============================================================================

IPC_PROTOCOL_VERSION = 1
HEARTBEAT_INTERVAL = 5.0  # seconds
READ_BUFFER_SIZE = 8192


def get_pipe_path() -> str:
    """Get the platform-appropriate pipe path"""
    uid = getpass.getuser()

    if sys.platform == 'win32':
        return f"\\\\.\\pipe\\vidurai-{uid}"
    else:
        return os.path.join(tempfile.gettempdir(), f"vidurai-{uid}.sock")


def get_buffer_dir() -> Path:
    """Get the buffer directory path (~/.vidurai)"""
    return Path.home() / '.vidurai'


def scan_buffer_files() -> list:
    """
    Scan for offline buffer files from VS Code extension sessions.

    Buffer files are named: buffer-{sessionId}.jsonl or buffer-{sessionId}.jsonl.bak

    Returns:
        List of (path, line_count) tuples for each buffer file found
    """
    buffer_dir = get_buffer_dir()
    if not buffer_dir.exists():
        return []

    buffer_files = []
    for f in buffer_dir.iterdir():
        if f.name.startswith('buffer-') and (f.suffix == '.jsonl' or f.name.endswith('.jsonl.bak')):
            try:
                line_count = sum(1 for line in f.read_text().splitlines() if line.strip())
                buffer_files.append((f, line_count))
                logger.info(f"Found buffer file: {f.name} ({line_count} events)")
            except Exception as e:
                logger.warning(f"Error reading buffer file {f.name}: {e}")

    return buffer_files


async def process_buffer_files(handler: Callable[['IPCMessage'], Awaitable[Any]]) -> dict:
    """
    Process all buffer files through a message handler.

    Args:
        handler: Async function to process each IPCMessage

    Returns:
        Dict with 'files', 'events', 'errors' counts
    """
    buffer_files = scan_buffer_files()
    if not buffer_files:
        return {'files': 0, 'events': 0, 'errors': 0}

    stats = {'files': 0, 'events': 0, 'errors': 0}

    for file_path, _ in buffer_files:
        try:
            content = file_path.read_text()
            for line in content.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    message = IPCMessage.from_json(data)
                    await handler(message)
                    stats['events'] += 1
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON in buffer: {e}")
                    stats['errors'] += 1
                except Exception as e:
                    logger.warning(f"Error processing buffered message: {e}")
                    stats['errors'] += 1

            # Delete processed file
            file_path.unlink()
            stats['files'] += 1
            logger.info(f"Processed and deleted buffer: {file_path.name}")

        except Exception as e:
            logger.error(f"Error processing buffer file {file_path}: {e}")
            stats['errors'] += 1

    return stats


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class IPCMessage:
    """Incoming IPC message"""
    v: int
    type: str
    ts: int
    id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'IPCMessage':
        return cls(
            v=data.get('v', 1),
            type=data.get('type', ''),
            ts=data.get('ts', 0),
            id=data.get('id'),
            data=data.get('data')
        )


@dataclass
class IPCResponse:
    """Outgoing IPC response"""
    v: int = IPC_PROTOCOL_VERSION
    type: str = 'ack'
    ts: int = field(default_factory=lambda: int(datetime.now().timestamp() * 1000))
    id: Optional[str] = None
    ok: bool = True
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_json(self) -> str:
        result = {
            'v': self.v,
            'type': self.type,
            'ts': self.ts,
            'ok': self.ok,
        }
        if self.id:
            result['id'] = self.id
        if self.data is not None:
            result['data'] = self.data
        if self.error:
            result['error'] = self.error
        return json.dumps(result)


# =============================================================================
# CLIENT CONNECTION
# =============================================================================

class IPCClientConnection:
    """Represents a single client connection

    Phase 7.0 Handshake Protocol:
    - On connect: Log "New connection (ID: {id}). Waiting for handshake..."
    - On handshake: Store client metadata, log "Client {id} identified as: {name} (v{version})"
    - Until handshake: Client is considered "unknown"
    """

    _id_counter = 0

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        message_handler: Callable[['IPCClientConnection', IPCMessage], Awaitable[IPCResponse]]
    ):
        IPCClientConnection._id_counter += 1
        self.id = IPCClientConnection._id_counter
        self.reader = reader
        self.writer = writer
        self.message_handler = message_handler
        self.connected = True
        self.buffer = ""
        self.remote_addr = self._get_remote_addr()

        # Phase 7.0: Handshake Protocol metadata
        self.client_name: str = "unknown"
        self.client_version: str = "unknown"
        self.handshake_complete: bool = False
        self.connected_at = datetime.now()

        logger.info(f"[IPC] New connection (ID: {self.id}). Waiting for handshake...")

    def complete_handshake(self, client_name: str, client_version: str):
        """Complete the handshake and store client metadata"""
        self.client_name = client_name
        self.client_version = client_version
        self.handshake_complete = True
        logger.info(f"[IPC] Client {self.id} identified as: {client_name} (v{client_version})")

    def _get_remote_addr(self) -> str:
        try:
            peername = self.writer.get_extra_info('peername')
            return str(peername) if peername else 'unknown'
        except Exception:
            return 'unknown'

    async def send(self, response: IPCResponse) -> bool:
        """Send a response to this client"""
        if not self.connected:
            return False

        try:
            data = response.to_json() + '\n'
            self.writer.write(data.encode('utf-8'))
            await self.writer.drain()
            return True
        except Exception as e:
            logger.error(f"Client {self.id}: Send error: {e}")
            self.connected = False
            return False

    async def send_heartbeat(self) -> bool:
        """Send heartbeat to this client"""
        response = IPCResponse(
            type='heartbeat',
            ts=int(datetime.now().timestamp() * 1000)
        )
        return await self.send(response)

    async def handle(self):
        """Main handler loop for this client"""
        try:
            while self.connected:
                # Read data
                try:
                    data = await asyncio.wait_for(
                        self.reader.read(READ_BUFFER_SIZE),
                        timeout=HEARTBEAT_INTERVAL * 2  # Allow for some slack
                    )
                except asyncio.TimeoutError:
                    # No data received, but connection might still be alive
                    continue

                if not data:
                    # Client disconnected
                    logger.info(f"Client {self.id}: Connection closed by client")
                    break

                # Process data
                self.buffer += data.decode('utf-8')
                await self._process_buffer()

        except asyncio.CancelledError:
            logger.info(f"Client {self.id}: Handler cancelled")
        except Exception as e:
            logger.error(f"Client {self.id}: Handler error: {e}")
        finally:
            self.connected = False
            await self._cleanup()

    async def _process_buffer(self):
        """Process complete lines from buffer (NDJSON)"""
        while '\n' in self.buffer:
            line, self.buffer = self.buffer.split('\n', 1)
            line = line.strip()

            if not line:
                continue

            try:
                data = json.loads(line)
                message = IPCMessage.from_json(data)
                response = await self.message_handler(self, message)
                await self.send(response)
            except json.JSONDecodeError as e:
                logger.error(f"Client {self.id}: JSON parse error: {e}")
                error_response = IPCResponse(
                    type='error',
                    ok=False,
                    error=f"Invalid JSON: {str(e)}"
                )
                await self.send(error_response)
            except Exception as e:
                logger.error(f"Client {self.id}: Message handling error: {e}")
                error_response = IPCResponse(
                    type='error',
                    ok=False,
                    error=str(e)
                )
                await self.send(error_response)

    async def _cleanup(self):
        """Clean up connection resources"""
        try:
            self.writer.close()
            await self.writer.wait_closed()
        except Exception:
            pass
        logger.info(f"Client {self.id}: Disconnected")


# =============================================================================
# IPC SERVER
# =============================================================================

class IPCServer:
    """
    Asyncio-based IPC server for Vidurai Daemon

    Handles multiple client connections over Named Pipe (Windows) or
    Unix Socket (Mac/Linux).

    Usage:
        server = IPCServer(message_handler=my_handler)
        await server.start()
        # ... run until shutdown
        await server.stop()
    """

    def __init__(
        self,
        message_handler: Optional[Callable[[IPCClientConnection, IPCMessage], Awaitable[IPCResponse]]] = None,
        pipe_path: Optional[str] = None
    ):
        self.pipe_path = pipe_path or get_pipe_path()
        self.message_handler = message_handler or self._default_handler
        self.server: Optional[asyncio.AbstractServer] = None
        self.clients: Set[IPCClientConnection] = set()
        self.running = False
        self.heartbeat_task: Optional[asyncio.Task] = None

    async def _default_handler(
        self,
        client: IPCClientConnection,
        message: IPCMessage
    ) -> IPCResponse:
        """Default message handler - just echoes or pongs"""
        if message.type == 'ping':
            return IPCResponse(
                type='pong',
                id=message.id,
                ok=True
            )
        else:
            return IPCResponse(
                type='ack',
                id=message.id,
                ok=True,
                data={'received': message.type}
            )

    async def start(self):
        """Start the IPC server"""
        if self.running:
            logger.warning("IPC server already running")
            return

        logger.info(f"Starting IPC server on {self.pipe_path}")

        # Clean up stale socket file on Unix
        if sys.platform != 'win32':
            socket_path = Path(self.pipe_path)
            if socket_path.exists():
                try:
                    socket_path.unlink()
                    logger.info(f"Removed stale socket: {self.pipe_path}")
                except OSError as e:
                    logger.warning(f"Could not remove stale socket: {e}")

        # Start server
        if sys.platform == 'win32':
            # Windows Named Pipe
            self.server = await asyncio.start_server(
                self._handle_client,
                path=self.pipe_path
            )
        else:
            # Unix Socket
            self.server = await asyncio.start_unix_server(
                self._handle_client,
                path=self.pipe_path
            )

        self.running = True

        # Start heartbeat task
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        logger.info(f"IPC server listening on {self.pipe_path}")

    async def stop(self):
        """Stop the IPC server"""
        if not self.running:
            return

        logger.info("Stopping IPC server...")
        self.running = False

        # Cancel heartbeat
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass

        # Disconnect all clients
        for client in list(self.clients):
            client.connected = False

        # Close server
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        # Clean up socket file on Unix
        if sys.platform != 'win32':
            socket_path = Path(self.pipe_path)
            if socket_path.exists():
                try:
                    socket_path.unlink()
                except OSError:
                    pass

        logger.info("IPC server stopped")

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ):
        """Handle a new client connection"""
        client = IPCClientConnection(reader, writer, self.message_handler)
        self.clients.add(client)

        try:
            await client.handle()
        finally:
            self.clients.discard(client)

    async def _heartbeat_loop(self):
        """Send heartbeats to all connected clients"""
        while self.running:
            await asyncio.sleep(HEARTBEAT_INTERVAL)

            if not self.running:
                break

            # Send heartbeat to all clients
            disconnected = []
            for client in self.clients:
                if not await client.send_heartbeat():
                    disconnected.append(client)

            # Remove disconnected clients
            for client in disconnected:
                self.clients.discard(client)

            if self.clients:
                logger.debug(f"Sent heartbeat to {len(self.clients)} clients")

    async def broadcast(self, response: IPCResponse):
        """Broadcast a message to all connected clients"""
        disconnected = []
        for client in self.clients:
            if not await client.send(response):
                disconnected.append(client)

        for client in disconnected:
            self.clients.discard(client)

    @property
    def client_count(self) -> int:
        """Number of connected clients"""
        return len(self.clients)


# =============================================================================
# STANDALONE TEST
# =============================================================================

async def _test_server():
    """Test the IPC server standalone"""
    logging.basicConfig(level=logging.DEBUG)

    async def handler(client: IPCClientConnection, msg: IPCMessage) -> IPCResponse:
        logger.info(f"Received from client {client.id}: {msg.type}")

        if msg.type == 'ping':
            return IPCResponse(type='pong', id=msg.id, ok=True)
        elif msg.type == 'echo':
            return IPCResponse(type='echo', id=msg.id, ok=True, data=msg.data)
        else:
            return IPCResponse(type='ack', id=msg.id, ok=True)

    server = IPCServer(message_handler=handler)
    await server.start()

    print(f"\nIPC Server running on: {server.pipe_path}")
    print("Press Ctrl+C to stop\n")

    try:
        while True:
            await asyncio.sleep(1)
            if server.client_count > 0:
                print(f"Connected clients: {server.client_count}")
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await server.stop()


if __name__ == '__main__':
    # Set Windows proactor event loop policy
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(_test_server())
