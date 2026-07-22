# Baseline IPC Contract

## Transport
- Unix Socket (Mac/Linux): `tempfile.gettempdir()/vidurai-{uid}.sock` (e.g., `/tmp/vidurai-chandan.sock`)
- Named Pipe (Windows): `\\\\.\\pipe\\vidurai-{uid}`

## Connection Flow
- Server starts, listens on pipe/socket.
- Client connects, sends handshake.
- Server validates handshake, responds with `handshake_ack`.
- Server sends `heartbeat` every 5 seconds to connected clients.

## Message Envelope
```json
{
  "v": 1,
  "type": "<message_type>",
  "ts": 1784654718561,
  "id": "evt1",
  "data": { ... }
}
```

## Supported Message Types
- `handshake` (Client -> Server)
- `handshake_ack` (Server -> Client)
- `file_edit` (Client -> Server)
- `terminal_command` (Client -> Server)
- `diagnostics` (Client -> Server)
- `active_file` (Client -> Server)
- `heartbeat` (Server -> Client)
- `ping` / `pong`
- `error` (Server -> Client on validation failure)
- `ack` (Server -> Client on successful processing)

## `file_edit` Payload
```json
{
  "project_path": "/path/to/project",
  "file": "/path/to/project/src/example.py",
  "gist": "User modified the example.py file",
  "change": "modify"
}
```

## Validation Behavior
- Server verifies envelope contains `v`, `type`, `ts`, and `id`.
- Handshake validates `client_name` and `version`.
- If a message type is unknown (e.g., `bad_event_type`), server returns `{"type": "error", "error": "Unknown message type: ..."}`.
- Path validity for `project_path` is checked; if unresolved, a warning is logged, but it falls back to the daemon's CWD for context association.
