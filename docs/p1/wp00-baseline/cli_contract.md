# Baseline CLI Contract

## Commands Tree
- `vidurai start`
- `vidurai stop`
- `vidurai status`
- `vidurai server`
- `vidurai mcp-install`
- `vidurai get-context-json`
- `vidurai get-context`
- `vidurai init`
- `vidurai clean`
- `vidurai log`
- `vidurai recall`
- `vidurai active`
- `vidurai chat`
- `vidurai db`
- `vidurai reset`
- `vidurai db backup`
- `vidurai db restore`
- `vidurai db vacuum`
- `vidurai forgetting-log`
- `vidurai forgetting-stats`
- `vidurai trigger-decay`
- `vidurai hint`

## Main Options
- `vidurai server` options: `--host` (default: 127.0.0.1), `--port` (default: 8765), `--allow-all-origins` (default: False)

## Behavior
- `start`: Starts daemon via `subprocess.Popen` detaching from terminal, writes PID to `~/.vidurai/daemon.pid`.
- `stop`: Reads PID from `~/.vidurai/daemon.pid`, sends SIGTERM, waits 5 seconds, sends SIGKILL if still running, deletes PID file.
- `status`: Checks if PID exists via `psutil`.
- `server`: Starts MCP server directly via `fastapi` and `uvicorn.run`.
