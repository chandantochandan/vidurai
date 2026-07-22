# Legacy-Component Reference Audit

## 1. `vidurai-browser-extension/`
- **Runtime References:** None observed in core daemon flows.
- **Build References:** None.
- **Test References:** None.
- **Documentation References:** Mentioned in root `README.md` and architecture docs as an experimental frontend.
- **Package-Script References:** None.
- **Import References:** None in Python or VS Code extension.
- **Status:** Appears entirely unused by the P1 core runtime. Safe for eventual deletion.

## 2. `vidurai-proxy/`
- **Runtime References:** None. MCP and direct local API fulfill its former role.
- **Build References:** None.
- **Test References:** None.
- **Documentation References:** Mentioned in legacy architecture docs.
- **Package-Script References:** None.
- **Import References:** None.
- **Status:** Appears entirely unused. Safe for eventual deletion.

## 3. `vidurai-vscode-extension/python-bridge/`
- **Runtime References:** The VS Code extension now uses `src/ipc/Client.ts` to connect to the global daemon socket, rendering `python-bridge/bridge.py` obsolete.
- **Build References:** Included in extension package blindly, but not executed.
- **Test References:** `test-bridge.js` relies on it.
- **Documentation References:** Mentioned in `CONTRIBUTING.md`.
- **Package-Script References:** None in `package.json` for compilation.
- **Import References:** `src/utils.ts` has a fallback checking for `.venv` inside `python-bridge`, which is a dead code path.
- **Status:** Appears obsolete. Safe for eventual deletion.

## 4. `vidurai-vscode-extension/test-bridge.js`
- **Runtime References:** None.
- **Build References:** None.
- **Test References:** Script exists to test the legacy `python-bridge`.
- **Documentation References:** Mentioned in `TESTING.md`.
- **Package-Script References:** None.
- **Import References:** None.
- **Status:** Obsolete alongside `python-bridge`. Safe for eventual deletion.
