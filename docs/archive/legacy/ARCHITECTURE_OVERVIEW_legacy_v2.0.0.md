# Vidurai Architecture Overview (v2.0.0)

> विस्मृति भी विद्या है — Forgetting too is knowledge.

Vidurai is a **local-first memory and context layer** that sits between humans and AI tools.
It watches what you do, watches what AI replies, and maintains a compressed, role-tagged, strategically-forgetting memory that any AI assistant can tap into.

This document describes the **high-level architecture**, core components, and data flows for Vidurai v2.0.0.

---

## 1. System Goals

Vidurai exists to:

- **Track** what the human is doing (code edits, commands, errors, project state)
- **Observe** what the AI is saying (requests + responses)
- **Compress & Forget** using SF-V2 (Smart Forgetting v2) while preserving critical entities
- **Mediate** between human ↔ AI by providing the right contextual gist at the right time
- **Support multiple audiences**: developer, AI model, manager, product, stakeholders
- **Stay local-first**: user data lives under `~/.vidurai/` with no mandatory cloud dependency

---

## 2. High-Level Architecture

At the highest level, Vidurai consists of:

1. **Core SDK (SF-V2 Engine)** — `vidurai/`
2. **Daemon (Ghost Daemon)** — `vidurai-daemon/`
3. **VS Code Extension (Developer Sensor)** — `vidurai-vscode-extension/`
4. **Browser Extension (AI UI Sensor)** — `vidurai-browser-extension/`
5. **Proxy (Optional API Wrapper)** — `vidurai-proxy/`
6. **Docs & Website** — `docs/`, `vidurai-docs/`, `vidurai-website/`
7. **Tests & Implementation History** — `tests/`, `docs/archive/implementation/`

### 2.1 Text Diagram

```text
               ┌─────────────────┐
               │   Human Tools    │
               │                  │
               │  - VS Code       │
               │  - Terminal      │
               │  - Browser (AI)  │
               └────────┬─────────┘
                        │ events (files, cmds, errors, chats)
                        ▼
               ┌─────────────────────┐
               │  Vidurai Daemon     │
               │   (Ghost Daemon)    │
               ├─────────────────────┤
               │ smart_file_watcher  │
               │ project_brain/*     │
               │ intelligence/*      │
               └────────┬────────────┘
                        │
                        │ enriched events / context requests
                        ▼
              ┌───────────────────────┐
              │   Vidurai SDK (SF-V2) │
              │       vidurai/        │
              ├───────────────────────┤
              │ VismritiMemory        │
              │ SF-V2 modules         │
              │ RL agent v2           │
              │ SQLite storage        │
              │ Forgetting ledger     │
              └────────┬──────────────┘
                       │
        ┌──────────────┴───────────────────┐
        │                                    │
        ▼                                    ▼
┌──────────────────────┐           ┌─────────────────────┐
│ Browser Extension    │           │  Proxy (optional)   │
│ AI UIs (DOM, chats)  │           │ LLM HTTP APIs       │
└──────────────────────┘           └─────────────────────┘

Both Browser Extension and Proxy read from & write to
the same SF-V2 memory, so context is shared across tools.
```

---

## 3. Core Component: Vidurai SDK (SF-V2 Engine)

**Repo:** `vidurai/`
**Version (target):** 2.0.0

The SDK is the cognitive engine. Everything else is a sensor or conduit.

### 3.1 Main Entry Points

- **VismritiMemory** — high-level memory interface (dual-trace: verbatim + gist).

- **CLI** — `vidurai.cli:cli`
  Commands like `context`, `recall`, `hints`, `pins`, `ledger`, `stats`.

- **MCP Server** — `vidurai.mcp_server:main`
  Provides Vidurai as a Model Context Protocol server.

### 3.2 SF-V2 Modules (Smart Forgetting v2)

Located under `vidurai/core/` (exact file names may vary slightly; this is conceptual):

- **semantic_consolidation.py**
  Consolidates windows of messages into compressed episodes.
  Preserves entities and roles while reducing token footprint.

- **entity_extractor.py**
  Extracts technical entities (files, functions, APIs, endpoints, errors, tools, etc.).
  Designed for 100% entity preservation under compression.

- **memory_role_classifier.py**
  Classifies memories into roles: CAUSE, CONTEXT, RESOLUTION, OUTCOME, etc.
  Ensures the "causal spine" of a project is not lost.

- **retention_score.py**
  Multi-factor retention score (0–200).
  Factors: salience, role, recency, access frequency, pin status, error impact.

- **memory_pinning.py**
  Pin/unpin memories, with a configurable global pin limit (e.g., 50).
  Pinned memories are protected from certain forgetting thresholds.

- **forgetting_ledger.py**
  JSONL audit trail at `~/.vidurai/forgetting_ledger.jsonl`.
  Records all forgetting operations for transparency and debugging.

- **proactive_hints.py**, **hint_delivery.py**
  Generates and filters hints that can be surfaced to humans or injected to AI.

- **episode_builder.py**, **event_bus.py**, **auto_memory_policy.py**, **multi_audience_gist.py**, **retention_policy.py**
  Organize memories into episodes.
  Publish/subscribe internal events.
  Apply automatic policies for retention.
  Generate different gists for different audiences (developer, AI, manager, etc.).

### 3.3 Storage

- **Primary DB:** SQLite at `~/.vidurai/vidurai.db`
- **Ledger:** `~/.vidurai/forgetting_ledger.jsonl`
- **Config:** `~/.vidurai/`

### 3.4 Multi-Audience Context

Vidurai can generate context for multiple audiences from the same underlying memory:

- **developer** — full technical context (files, functions, errors, stack traces).
- **ai** — optimized, compressed context suitable for prompt injection.
- **manager** — higher-level "what changed / what was fixed".
- **product / stakeholder** — roadmap impact, stability, risk summaries.

APIs like `get_context` and `get_hints` either accept an `audience` parameter or return a multi-audience structure for downstream tools.

---

## 4. Shared Event Schema

Vidurai uses a unified event schema across all components.

### 4.1 Event Envelope

Every event conforms to:

```json
{
  "schema_version": "vidurai-events-v1",
  "event_id": "uuid",
  "timestamp": "2025-11-26T18:30:00.123Z",
  "source": "vscode" | "browser" | "proxy" | "daemon" | "cli",
  "channel": "human" | "ai" | "system",
  "kind": "file_edit" | "terminal_command" | "diagnostic" | "ai_message" | "ai_response"
          | "error_report" | "memory_event" | "hint_event" | "metric_event" | "system_event",
  "subtype": "optional_subtype",
  "project_root": "/home/user/my-project",
  "project_id": "stable_hash_of_root",
  "session_id": "logical_session_id",
  "request_id": "llm_request_id_or_null",
  "payload": { "...kind-specific fields..." }
}
```

### 4.2 Example: Hint Event Payload (Multi-Audience)

```json
{
  "hint_id": "h_abc123",
  "hint_type": "relevant_context",
  "text": "You recently fixed a similar 500 error in /api/auth, see commit abc123.",
  "target": "human",                     // "human" | "ai"
  "audience": "developer",               // "developer" | "ai" | "manager" | "product" | "stakeholder"
  "surface": "vscode",                   // "vscode" | "browser" | "cli" | "dashboard"
  "accepted": true,
  "latency_ms": 120
}
```

The Python SDK exposes `ViduraiEvent`, `EventSource`, `EventChannel`, `EventKind` under `vidurai.shared.events`.
The VS Code and Browser extensions share matching TypeScript types under `src/shared/events.ts`.

---

## 5. Daemon (Ghost Daemon)

**Repo:** `vidurai-daemon/`
**Version (target):** 2.0.0

The Daemon is an always-on local service that:

- Watches project files and errors.
- Talks to the Vidurai SDK.
- Serves context and hints to other tools (VS Code, browser, custom clients).

### 5.1 Core Components

- **daemon.py**
  FastAPI + WebSocket server (default: `http://localhost:7777`)
  Endpoints like `/smart-context`, `/report-error`, `/watch/{project_root}`, `/metrics`.

- **smart_file_watcher.py**
  Watches file changes and publishes standardized `file_edit` events.

- **project_brain/**
  - `scanner.py` — scans repositories/projects.
  - `context_builder.py` — builds a structured "project brain".
  - `error_watcher.py` — monitors error streams.
  - `memory_store.py` — maintains an in-memory cache for quick lookup.

- **intelligence/**
  - `context_mediator.py` — routes context requests between tools and SF-V2.
  - `human_ai_whisperer.py` — orchestrates multi-audience gists for human + AI.
  - `memory_bridge.py` — bridges daemon events ↔ VismritiMemory.

### 5.2 Role in the System

The Daemon:

- Ingests human-side signals: file edits, diagnostics, terminal patterns.
- Submits events to the SDK and requests context/hints.
- Serves AI-side tools (browser extension, proxy) via HTTP/WebSocket.
- Acts as the central nervous system of Vidurai.

---

## 6. VS Code Extension

**Repo:** `vidurai-vscode-extension/`
**Version (target):** 2.0.0

**Purpose:**

- Track developer activity in code.
- Provide a UI to inspect Vidurai memory and copy context.

**Key elements:**

- `src/extension.ts` — main entry.
- `src/fileWatcher.ts` — emits `file_edit` events using the shared schema.
- `src/terminalWatcher.ts` — emits `terminal_command` events.
- `src/diagnosticWatcher.ts` — emits `diagnostic` events.
- `src/shared/events.ts` — TypeScript `ViduraiEvent` types and helpers.
- `python-bridge/` — runs a Python process that communicates with the SDK / Daemon.
- `src/views/memoryTreeView.ts` — memory tree panel.
- `src/statusBar.ts` — "Vidurai: n memories" indicator.

---

## 7. Browser Extension

**Repo:** `vidurai-browser-extension/`
**Version (target):** 2.0.0

**Purpose:**

- Attach Vidurai context to web-based AI tools.
- Optionally log AI conversations back into memory.

**Key elements:**

- `manifest.json` — Chrome MV3 manifest.
- `src/content.ts` / `content.js` — runs in AI web UIs (ChatGPT, Claude, Gemini, etc.).
- `src/shared/events.ts` — shared event types.
- `src/strategies/` — site-specific or generic injection/formatting strategies.
- `src/injectors/` — DOM manipulation and React-aware injectors.
- `popup/` — basic UI to toggle features.

**Connections:**

- Talks to Daemon at `http://localhost:7777` for smart context.
- Emits `ai_message` and `ai_response` events following the shared schema.

---

## 8. Proxy (Optional API Layer)

**Repo:** `vidurai-proxy/`
**Version (target):** 2.0.0

**Purpose:**

- Act as a drop-in proxy for LLM APIs (OpenAI, Anthropic, etc.).
- Automatically attach Vidurai context to requests.
- Log all request/response pairs to SF-V2 for long-term learning.

**Key elements:**

- `src/main.py` — FastAPI application.
- `src/routes/proxy_routes.py` — proxy endpoints.
- `src/utils/session_manager.py` — per-user / per-key session handling.
- `src/utils/config_loader.py`, `metrics_tracker.py`, `provider_detection.py`, `terminal_ui.py`, `logger.py`.

---

## 9. Tests and Implementation History

- **Tests:** `tests/`
  All Python test files live here (e.g. `tests/test_*.py`).
  Includes SF-V2 tests, RL tests, daemon integration tests.

- **Implementation History:** `docs/archive/implementation/`
  Contains legacy `PHASE_*.md` documents.
  Kept for historical insight, not as canonical docs.

These two directories ensure the root of the repository is clean and signals a production-grade project.

---

## 10. Docs and Website

- `docs/` — project-level docs for the SDK and architecture.
- `vidurai-docs/` — Docusaurus-powered documentation site.
- `vidurai-website/` — marketing site (currently Astro; may be migrated to React in future).

For v2.0.0, docs will:

- Lead with SF-V2 and "forgetting as a feature".
- Present this architecture overview as the canonical system map.
- Provide quickstarts for:
  - SDK-only usage
  - Daemon + VS Code
  - Browser extension
  - Proxy integration.

---

## 11. Version Matrix (v2.0.0 Alignment)

For Vidurai v2.0.0, all components share a single version number:

| Component             | Version |
|-----------------------|---------|
| Vidurai SDK           | 2.0.0   |
| Vidurai Daemon        | 2.0.0   |
| VS Code Extension     | 2.0.0   |
| Browser Extension     | 2.0.0   |
| Vidurai Proxy         | 2.0.0   |
| Docs / Website Content| 2.0.0   |

---

## 12. Design Principles

1. **Local-first:** Everything runs on the user's machine by default.
2. **Bi-directional mediation:** Vidurai pays attention to both human activity and AI responses.
3. **Transparent forgetting:** A forgetting ledger is always available for inspection.
4. **Multi-audience context:** The right gist for the right consumer (developer, AI, manager, etc.).
5. **Minimal public surface:** A small, clear set of entry points instead of a sprawling API.
6. **Composable:** SDK is useful alone; daemon, proxy, and extensions add layers as needed.

---

*This document is the canonical overview for Vidurai v2.0.0 and should be kept in sync whenever architecture or component responsibilities change.*
