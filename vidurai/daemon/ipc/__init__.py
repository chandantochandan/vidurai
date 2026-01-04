"""
IPC Module - Named Pipe/Unix Socket Transport

Provides asyncio-based IPC server for communication with VS Code extension.
"""

from .server import (
    IPCServer,
    IPCClientConnection,
    IPCMessage,
    IPCResponse,
    IPC_PROTOCOL_VERSION,
    get_pipe_path,
    get_buffer_dir,
    scan_buffer_files,
    process_buffer_files,
)

__all__ = [
    'IPCServer',
    'IPCClientConnection',
    'IPCMessage',
    'IPCResponse',
    'IPC_PROTOCOL_VERSION',
    'get_pipe_path',
    'get_buffer_dir',
    'scan_buffer_files',
    'process_buffer_files',
]
