# Changelog

All notable changes to this project will be documented in this file.

This project follows semantic versioning:
https://semver.org/

---

## [2.0.0] — 2025-01-XX
### **The Vidurai Architecture Rewrite (SF-V2 Release)**

Vidurai v2.0.0 is a **major system redesign**.
All major components — SDK, Daemon, Proxy, VS Code Extension, Browser Extension — have been aligned around the **Smart Forgetting V2 (SF-V2)** engine and the new **Shared Event Schema**.

This is the first *unified* Vidurai release where the entire ecosystem works as one coherent memory and context engine.

---

## ✨ **Highlights**

### **• Smart Forgetting Engine (SF-V2)**
A new, research-driven forgetting system that maintains a compact, meaningful memory over time.

Includes:
- Dual‐trace memory (verbatim + gist)
- Salience & retention scoring
- Forgetting ledger (auditable deletions)
- Pins & manual retention
- Entropy reduction instead of unbounded log growth

This shifts the primary focus away from the earlier RL-centric v1.x design and formalizes forgetting as a first-class concern.

---

### **• Shared Event Schema (Unified I/O Model)**
A structured, versioned event format used by:
- VS Code extension
- Browser extension
- Daemon
- Python SDK
- Proxy

Every event now follows the same schema:
- `schema_version`
- `source`, `channel`, `kind`
- `project_root`, `project_id`, `session_id`
- Kind-specific payloads

This eliminates fragmentation, reduces glue code, and enables consistent memory building.

---

### **• Multi-Audience Context Generation**
Vidurai can now produce summaries optimized for different consumers:

- `developer` — code, errors, functions, stack traces
- `ai` — token-efficient distilled context
- `manager` — high-level progress
- `stakeholder` — impact & reasoning

This replaces the old "single generic summary" style and makes the engine explicitly multi-audience.

---

### **• Local-First Project Brain**
Vidurai now stores all memory **locally** by default:

- Project brains
- Forgetting ledger
- Event history
- Session metadata

Stored under:
```
~/.vidurai/
```

No cloud requirement; remote/team features (when added) will be opt-in.

---

### **• Full Toolchain Integration (VS Code + Browser)**

#### VS Code Extension (2.0.0)
- File edit tracking
- Terminal command tracking
- Diagnostics/errors tracking
- Sends normalized events to Daemon
- Status bar + commands

#### Browser Extension (2.0.0)
- Captures ChatGPT / Claude / Gemini conversations
- Normalizes input/output messages
- Can inject Vidurai context into AI chats
- Uses the shared schema for all message types

---

### **• Vidurai Daemon (2.0.0)**
A unified background service responsible for:
- Event ingestion
- Project identification
- Memory write operations
- Forgetting logic execution
- IPC with VS Code / browser / proxy

Published as a Docker image:
- `chandantochandan/vidurai-daemon:2.0.0`

> **Note:**
> The daemon is the *recommended* way to use Vidurai with extensions,
> but the Python SDK itself can still be imported and used directly in Python code where appropriate.

---

### **• Vidurai Proxy (2.0.0)**
Optional LLM API proxy that:
- Wraps providers like OpenAI, Anthropic, etc.
- Injects Vidurai context into outgoing LLM calls
- Records AI prompts/responses into memory

Published as:
- `chandantochandan/vidurai-proxy:2.0.0`

---

## 🔧 **Developer Experience Improvements**

- Repository cleanup: tests moved to `/tests`, implementation docs archived under `docs/archive/implementation/`.
- All core components version-synchronized to `2.0.0`.
- Added `.github/workflows` CI for SDK, VS Code, Browser builds.
- Dockerfiles created for Daemon & Proxy.
- Migrated to `pyproject.toml` (PEP 621) as the canonical build config.
- Removed legacy `setup.py`.
- Introduced canonical `ARCHITECTURE_OVERVIEW.md`.
- Introduced shared `events.py` / `events.ts`.
- Removed the legacy ChatGPT-only extension (logic merged into main browser extension).

---

## 💥 **Breaking Changes**

### **1. Public API reshaping from v1.x**

Vidurai v2.0.0 introduces new abstractions and focuses on SF-V2 and the shared event schema.

As a result:

- Several v1.x classes and helpers have moved, been renamed, or are now considered internal.
- The primary integration path is now:
  - Tools → Daemon → SDK
  rather than direct ad-hoc usage inside application code.

The RL-based components and older kosha-era structures from v1.x may still exist in the codebase for compatibility where appropriate, but they are **no longer the main public surface** and should not be treated as stable APIs going forward.

Consult the updated docs at https://docs.vidurai.ai for the current recommended entrypoints.

---

### **2. New event models**

All new events are expected to follow:

- `vidurai-events-v1` schema
- Updated field names and enums
- Stable `project_id` / `session_id` conventions

Existing integrations using ad-hoc or older event shapes may require updates.

---

## 🚚 **Migration Guide (from v1.5.x – v1.6.x)**

1. Uninstall any old Vidurai install:

```bash
pip uninstall vidurai
```

2. Install Vidurai v2.0.0:

```bash
pip install vidurai
```

3. Existing local data under `~/.vidurai/` can remain;
   any migration or reuse of v1.x data should be done deliberately,
   not assumed, and guided by the updated docs.

4. Update integrations to:

   - Use the shared event schema, and
   - Prefer daemon-mediated flows for tool connections (VS Code, browser, proxies).

5. For direct SDK usage in Python, refer to the latest examples and API docs at:
   https://docs.vidurai.ai

---

## 📁 Repository Structure (v2.0.0)

```
vidurai/                     # Python SDK
vidurai-daemon/              # Daemon service
vidurai-proxy/               # Optional LLM proxy
vidurai-vscode-extension/    # VS Code extension
vidurai-browser-extension/   # Browser extension
tests/                       # All Python tests
docs/                        # Documentation
docs/archive/implementation/ # Historical specs
ARCHITECTURE_OVERVIEW.md     # Canonical architecture doc
```

---

## 🐳 Docker Images (v2.0.0)

**Daemon**

```bash
docker pull chandantochandan/vidurai-daemon:2.0.0
```

**Proxy**

```bash
docker pull chandantochandan/vidurai-proxy:2.0.0
```

---

## 🔜 Planned for 2.1.x / 2.2.x

- Memory inspection dashboard
- Expanded audience profiles
- JetBrains plugin
- CLI improvements
- Optional remote / team memory features

---

## [1.x.x] — Legacy Releases

v1.x.x introduced Vidurai's earlier RL-driven memory experiments and kosha-based designs.
Vidurai v2.0.0 re-centers the architecture around SF-V2, shared events, and multi-tool integration.

Legacy implementation notes and design phases have been preserved under:

```
docs/archive/implementation/
```

for historical reference.
