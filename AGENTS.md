# VIDURAI PROTOCOL (v2.0.0)

## 1. SYSTEM IDENTITY
Vidurai is a **Distributed Context Middleware**.
It functions as a local abstraction layer between IDE/Browser telemetry and LLM context windows.

**Core KPI:** Signal-to-Noise Ratio (SNR) Optimization.
**Core Constraint:** Zero-Trust / Local-First Data Governance.

## 2. OPERATIONAL RULES (STRICT)
1.  **Deterministic Imports:** Never hallucinate dependencies. Verify against `pyproject.toml`.
2.  **Schema Adherence:** All events MUST conform to `vidurai-events-v1` (Pydantic Strict Mode).
3.  **ACID Compliance:** All state changes MUST be written to SQLite via the Daemon's WAL-mode queue.
4.  **Immutability:** The `forgetting_ledger.jsonl` is append-only. Never modify existing lines.

## 3. ARCHITECTURE MAP
* **Ingestion:** `vidurai-daemon` (FastAPI/WebSockets)
* **Processing:** `vidurai.core` (SF-V2 Heuristic Engine)
* **Storage:** `~/.vidurai/vidurai.db` (SQLite)
* **Transport:** JSON-RPC over HTTP / WebSocket events

## 4. CODING STANDARDS
* **Logging:** Use structured logging (`loguru`) with correlation IDs.
* **Error Handling:** Fail gracefully. If the Daemon is unreachable, buffer events locally (Extensions).
