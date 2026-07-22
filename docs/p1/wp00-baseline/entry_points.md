# Baseline Runtime Entry Points

## 1. CLI Entry Point
- Path: `vidurai/cli.py`
- Symbol: `cli()` (Click group)
- Invocation: `python -m vidurai.cli` or `vidurai`

## 2. Daemon Startup Entry Point
- Path: `vidurai/daemon/server.py`
- Symbol: `start_daemon(port, pipe_name)`
- Invoked via: `vidurai start`

## 3. MCP Startup Entry Point
- Path: `vidurai/mcp_server.py`
- Symbol: `main(host, port, allow_all_origins)`
- Invoked via: `vidurai server`

## 4. VS Code Extension Activation Entry Point
- Path: `vidurai-vscode-extension/src/extension.ts`
- Symbol: `activate(context: vscode.ExtensionContext)`

## 5. Website Build Entry Point
- Path: `website/package.json`
- Commands: `npm run dev`, `npm run build`

## 6. Proxy Entry Point
- Path: `vidurai-proxy/src/main.py`
- Symbol: `app` (FastAPI instance)
- Invoked via: `uvicorn src.main:app`

## 7. Browser-Extension Entry Points
- Background: `vidurai-browser-extension/background.js`
- Content Script: `vidurai-browser-extension/content.js`

## 8. Legacy Bridge Entry Points
- Python Bridge: `vidurai-vscode-extension/python-bridge/bridge.py` (`__main__` block)
- Test Bridge: `vidurai-vscode-extension/test-bridge.js`
